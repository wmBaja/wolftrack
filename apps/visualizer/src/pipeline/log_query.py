import os
import sqlite3
import threading
import uuid
from typing import Any

from logging_config import get_logger

logger = get_logger(__name__)


class _IndexingCancelled(Exception):
    """Raised internally when an indexing job has been cancelled."""


class LogQueryService:
    BATCH_SIZE = 10_000
    PROGRESS_UPDATE_INTERVAL = 1_000

    def __init__(self, cache_dir: str | os.PathLike[str]) -> None:
        self.cache_dir = os.fspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.status = "idle"
        self.progress = 0
        self.log_file: str | None = None
        self.dbc: Any | None = None
        self.db_path: str | None = None
        self.conn: sqlite3.Connection | None = None
        self._task: threading.Thread | None = None
        self._state_lock = threading.RLock()
        self._active_job: object | None = None
        self._cancel_event: threading.Event | None = None
        self.start_ts = 0
        self.end_ts = 0

    def start_indexing(self, log_file: str | os.PathLike[str], dbc: Any) -> None:
        log_file_path = os.fspath(log_file)
        file_stat = os.stat(log_file_path)
        cache_key = (
            f"{os.path.basename(log_file_path)}_"
            f"{file_stat.st_size}_{file_stat.st_mtime}.sqlite"
        )
        db_path = os.path.join(self.cache_dir, cache_key)
        job = object()
        cancel_event = threading.Event()

        with self._state_lock:
            self._cancel_active_job_locked()
            self._close_connection_locked()
            self.log_file = log_file_path
            self.dbc = dbc
            self.db_path = db_path
            self.status = "loading"
            self.progress = 0
            self.start_ts = 0
            self.end_ts = 0
            self._active_job = job
            self._cancel_event = cancel_event
            self._task = threading.Thread(
                target=self._index_worker,
                args=(job, cancel_event, log_file_path, db_path, dbc),
                daemon=True,
            )
            task = self._task

        task.start()

    def _index_worker(
        self,
        job: object | None = None,
        cancel_event: threading.Event | None = None,
        log_file: str | None = None,
        db_path: str | None = None,
        dbc: Any | None = None,
    ) -> None:
        """Build an index in a temporary database and publish it on success."""
        # Defaults retain support for focused synchronous worker tests.
        if job is None:
            job = object()
            with self._state_lock:
                self._active_job = job
        if cancel_event is None:
            cancel_event = threading.Event()
            with self._state_lock:
                self._cancel_event = cancel_event
        if log_file is None:
            log_file = self.log_file
        if db_path is None:
            db_path = self.db_path
        if dbc is None:
            dbc = self.dbc

        if log_file is None or db_path is None:
            raise RuntimeError("Log indexing requires a log file and cache path.")

        temporary_db_path = f"{db_path}.{uuid.uuid4().hex}.partial"
        connection: sqlite3.Connection | None = None

        try:
            self._raise_if_cancelled(job, cancel_event)
            is_cached = os.path.exists(db_path)

            if is_cached:
                connection = sqlite3.connect(db_path, check_same_thread=False)
                logger.info("Using cached log index: %s", db_path)
                cursor = connection.cursor()
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals")
                row = cursor.fetchone()
                self._raise_if_cancelled(job, cancel_event)
                start_ts, end_ts = (row[0], row[1]) if row and row[0] is not None else (0, 0)
                self._publish_ready(job, cancel_event, connection, start_ts, end_ts)
                connection = None
                return

            if dbc is None:
                raise RuntimeError("Log indexing requires a loaded DBC.")

            logger.info("Indexing log file: %s", log_file)
            connection = sqlite3.connect(temporary_db_path, check_same_thread=False)
            cursor = connection.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS signals "
                "(timestamp REAL, signal_id TEXT, value REAL)"
            )

            import can

            file_size = os.path.getsize(log_file)
            batch = []
            min_ts = float("inf")
            max_ts = float("-inf")
            arb_id_cache = {}

            # Pass an open stream to BLFReader so its byte position is available
            # while messages are decoded.
            with open(log_file, "rb") as log_handle:
                reader = can.BLFReader(log_handle)
                try:
                    for message_index, msg in enumerate(reader, start=1):
                        self._raise_if_cancelled(job, cancel_event)
                        timestamp = getattr(msg, "timestamp", 0)
                        min_ts = min(min_ts, timestamp)
                        max_ts = max(max_ts, timestamp)

                        arb_id = msg.arbitration_id
                        if arb_id not in arb_id_cache:
                            try:
                                msg_obj = dbc.get_message_by_frame_id(arb_id)
                                arb_id_cache[arb_id] = {
                                    sig.name: f"{msg_obj.name}.{sig.name}"
                                    for sig in msg_obj.signals
                                }
                            except KeyError:
                                arb_id_cache[arb_id] = None

                        signal_map = arb_id_cache[arb_id]
                        if signal_map:
                            try:
                                decoded = dbc.decode_message(arb_id, msg.data)
                                for sig_name, sig_value in decoded.items():
                                    sig_id = signal_map.get(sig_name)
                                    if sig_id:
                                        batch.append((timestamp, sig_id, float(sig_value)))
                            except Exception:
                                logger.debug(
                                    "Unable to decode log message %s",
                                    arb_id,
                                    exc_info=True,
                                )

                        if len(batch) >= self.BATCH_SIZE:
                            self._raise_if_cancelled(job, cancel_event)
                            cursor.executemany("INSERT INTO signals VALUES (?, ?, ?)", batch)
                            connection.commit()
                            batch = []

                        if message_index % self.PROGRESS_UPDATE_INTERVAL == 0:
                            self._update_progress_for_job(
                                job, cancel_event, log_handle.tell(), file_size
                            )

                    self._raise_if_cancelled(job, cancel_event)
                    # BLFReader closes the supplied stream after EOF. At this
                    # point EOF is already known, so avoid calling tell() again.
                    self._update_progress_for_job(
                        job, cancel_event, file_size, file_size
                    )
                finally:
                    if not log_handle.closed:
                        reader.stop()

            self._raise_if_cancelled(job, cancel_event)
            if batch:
                cursor.executemany("INSERT INTO signals VALUES (?, ?, ?)", batch)
                connection.commit()

            self._raise_if_cancelled(job, cancel_event)
            logger.info("Creating indexes...")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sig_time "
                "ON signals(signal_id, timestamp)"
            )
            connection.commit()
            connection.close()
            connection = None

            self._publish_temporary_index(
                job,
                cancel_event,
                temporary_db_path,
                db_path,
                min_ts if min_ts != float("inf") else 0,
                max_ts if max_ts != float("-inf") else 0,
            )
            temporary_db_path = ""
            logger.info("Indexing complete.")

        except _IndexingCancelled:
            logger.info("Log indexing cancelled: %s", log_file)
        except Exception as error:
            logger.error("Error indexing log file: %s", error, exc_info=True)
            with self._state_lock:
                if self._active_job is job and not cancel_event.is_set():
                    self.status = "error"
        finally:
            if connection:
                connection.close()
            if temporary_db_path:
                try:
                    os.remove(temporary_db_path)
                except FileNotFoundError:
                    pass

    def _cancel_active_job_locked(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()

    def _close_connection_locked(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None

    def _raise_if_cancelled(self, job: object, cancel_event: threading.Event) -> None:
        with self._state_lock:
            if cancel_event.is_set() or self._active_job is not job:
                raise _IndexingCancelled()

    def _publish_ready(
        self,
        job: object,
        cancel_event: threading.Event,
        connection: sqlite3.Connection,
        start_ts: float,
        end_ts: float,
    ) -> None:
        with self._state_lock:
            if cancel_event.is_set() or self._active_job is not job:
                raise _IndexingCancelled()
            self._close_connection_locked()
            self.conn = connection
            self.start_ts = start_ts
            self.end_ts = end_ts
            self.progress = 100
            self.status = "ready"

    def _publish_temporary_index(
        self,
        job: object,
        cancel_event: threading.Event,
        temporary_db_path: str,
        db_path: str,
        start_ts: float,
        end_ts: float,
    ) -> None:
        with self._state_lock:
            if cancel_event.is_set() or self._active_job is not job:
                raise _IndexingCancelled()
            os.replace(temporary_db_path, db_path)
            connection = sqlite3.connect(db_path, check_same_thread=False)
            self._close_connection_locked()
            self.conn = connection
            self.start_ts = start_ts
            self.end_ts = end_ts
            self.progress = 100
            self.status = "ready"

    def _update_progress_for_job(
        self,
        job: object,
        cancel_event: threading.Event,
        bytes_read: int,
        file_size: int,
    ) -> None:
        self._raise_if_cancelled(job, cancel_event)
        self._update_progress(bytes_read, file_size)

    def _update_progress(self, bytes_read: int, file_size: int) -> None:
        if file_size <= 0:
            return

        bounded_bytes = max(0, min(bytes_read, file_size))
        with self._state_lock:
            self.progress = min(99, int((bounded_bytes / file_size) * 100))

    def get_status(self) -> dict[str, int | str | float]:
        with self._state_lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "start_ts": self.start_ts,
                "end_ts": self.end_ts,
            }

    def query(
        self,
        signals: list[str],
        start_ts: float,
        end_ts: float,
        max_points: int,
    ) -> dict[str, dict[str, list[float]]]:
        with self._state_lock:
            if self.status != "ready" or not self.conn:
                return {}

            cursor = self.conn.cursor()
            result = {}
            span = end_ts - start_ts
            if span <= 0:
                return {}
            bucket_size = span / max_points

            for sig in signals:
                query = """
                SELECT
                    MIN(timestamp) as ts,
                    value
                FROM signals
                WHERE signal_id = ? AND timestamp >= ? AND timestamp <= ?
                GROUP BY CAST((timestamp - ?) / ? AS INTEGER)
                ORDER BY ts ASC
                """
                cursor.execute(query, (sig, start_ts, end_ts, start_ts, bucket_size))
                rows = cursor.fetchall()
                result[sig] = {
                    "timestamps": [row[0] for row in rows],
                    "values": [row[1] for row in rows],
                }

            return result

    def stop(self) -> None:
        with self._state_lock:
            self._cancel_active_job_locked()
            self._active_job = None
            self._cancel_event = None
            self._close_connection_locked()
            self.status = "idle"
            self.progress = 0
            self.start_ts = 0
            self.end_ts = 0


log_query_service = LogQueryService(
    os.path.join(os.environ.get("WOLFTRACK_USER_DATA", os.getcwd()), "logs", "cache")
)
