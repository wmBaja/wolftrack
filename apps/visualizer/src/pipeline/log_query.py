import os
import sqlite3
import threading
from typing import Any

from logging_config import get_logger

logger = get_logger(__name__)


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
        self.start_ts = 0
        self.end_ts = 0

    def start_indexing(self, log_file: str | os.PathLike[str], dbc: Any) -> None:
        self.log_file = os.fspath(log_file)
        self.dbc = dbc

        file_stat = os.stat(self.log_file)
        cache_key = (
            f"{os.path.basename(self.log_file)}_"
            f"{file_stat.st_size}_{file_stat.st_mtime}.sqlite"
        )
        self.db_path = os.path.join(self.cache_dir, cache_key)

        self.status = "loading"
        self.progress = 0
        self.start_ts = 0
        self.end_ts = 0
        self._task = threading.Thread(target=self._index_worker, daemon=True)
        self._task.start()

    def _index_worker(self) -> None:
        if self.log_file is None or self.db_path is None:
            raise RuntimeError("Log indexing requires a log file and cache path.")

        log_file = self.log_file
        db_path = self.db_path
        dbc = self.dbc

        try:
            is_cached = os.path.exists(db_path)
            self.conn = sqlite3.connect(db_path, check_same_thread=False)

            if is_cached:
                logger.info("Using cached log index: %s", db_path)
                cursor = self.conn.cursor()
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals")
                row = cursor.fetchone()
                if row and row[0] is not None:
                    self.start_ts, self.end_ts = row[0], row[1]
                self.progress = 100
                self.status = "ready"
                return

            if dbc is None:
                raise RuntimeError("Log indexing requires a loaded DBC.")

            logger.info("Indexing log file: %s", log_file)
            cursor = self.conn.cursor()
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
                        timestamp = getattr(msg, "timestamp", 0)
                        if timestamp < min_ts:
                            min_ts = timestamp
                        if timestamp > max_ts:
                            max_ts = timestamp

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
                                        batch.append(
                                            (timestamp, sig_id, float(sig_value))
                                        )
                            except Exception:
                                logger.debug(
                                    "Unable to decode log message %s",
                                    arb_id,
                                    exc_info=True,
                                )

                        if len(batch) >= self.BATCH_SIZE:
                            cursor.executemany(
                                "INSERT INTO signals VALUES (?, ?, ?)",
                                batch,
                            )
                            self.conn.commit()
                            batch = []

                        if message_index % self.PROGRESS_UPDATE_INTERVAL == 0:
                            self._update_progress(log_handle.tell(), file_size)

                    # BLFReader closes the supplied stream after EOF. At this
                    # point EOF is already known, so avoid calling tell() again.
                    self._update_progress(file_size, file_size)
                finally:
                    if not log_handle.closed:
                        reader.stop()

            if batch:
                cursor.executemany("INSERT INTO signals VALUES (?, ?, ?)", batch)
                self.conn.commit()

            logger.info("Creating indexes...")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sig_time "
                "ON signals(signal_id, timestamp)"
            )
            self.conn.commit()

            self.start_ts = min_ts if min_ts != float("inf") else 0
            self.end_ts = max_ts if max_ts != float("-inf") else 0
            self.progress = 100
            self.status = "ready"
            logger.info("Indexing complete.")

        except Exception as error:
            logger.error("Error indexing log file: %s", error, exc_info=True)
            self.status = "error"

    def _update_progress(self, bytes_read: int, file_size: int) -> None:
        if file_size <= 0:
            return

        bounded_bytes = max(0, min(bytes_read, file_size))
        self.progress = min(99, int((bounded_bytes / file_size) * 100))

    def get_status(self) -> dict[str, int | str | float]:
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
        if self.conn:
            self.conn.close()
            self.conn = None
        self.status = "idle"


log_query_service = LogQueryService(
    os.path.join(os.environ.get("WOLFTRACK_USER_DATA", os.getcwd()), "logs", "cache")
)
