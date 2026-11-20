import contextlib
import heapq
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Callable

from logging_config import get_logger
from wts.batch import run_batch
from wts.engine import VirtualSignalEngine
from wts.graph import subgraph_defs
from wts.schema import WTS_PREFIX

logger = get_logger(__name__)


class _IndexingCancelled(Exception):
    """Raised internally when an indexing or derived-compute job is cancelled."""


#: definitions provider: returns (valid definitions, {name: def_hash}).
DefinitionsProvider = Callable[[], tuple[list[Any], dict[str, str]]]


class LogQueryService:
    BATCH_SIZE = 10_000
    PROGRESS_UPDATE_INTERVAL = 1_000
    DERIVED_SWAP_BATCH = 10_000
    RECOMPUTE_DEBOUNCE_SECONDS = 0.3

    def __init__(self, cache_dir: str | os.PathLike[str]) -> None:
        self.cache_dir = os.fspath(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.status = "idle"
        self.progress = 0
        self.log_file: str | None = None
        self.dbc: Any | None = None
        self.dbc_hash: str | None = None
        self.db_path: str | None = None
        self.conn: sqlite3.Connection | None = None
        self._task: threading.Thread | None = None
        self._state_lock = threading.RLock()
        self._active_job: object | None = None
        self._cancel_event: threading.Event | None = None
        self.start_ts = 0
        self.end_ts = 0

        # Virtual signals (Part 3): computed in a worker thread with its own
        # connection; the raw `signals` table stays immutable after publish.
        self._definitions_provider: DefinitionsProvider | None = None
        self._compute_job: object | None = None
        self._compute_cancel: threading.Event | None = None
        self._compute_thread: threading.Thread | None = None
        self._compute_targets: set[str] = set()
        self._debounce_timer: threading.Timer | None = None
        self.derived_status = "idle"
        self.derived_progress = 0
        self.derived_pending: list[str] = []

    # ------------------------------------------------------------- setup

    def set_cache_dir(self, cache_dir: str | os.PathLike[str]) -> None:
        """Re-point the cache directory (the module singleton is created at
        import time from the environment; the app knows better later)."""
        cache_dir = os.fspath(cache_dir)
        if cache_dir == self.cache_dir:
            return
        self.stop()
        with self._state_lock:
            self.cache_dir = cache_dir
            os.makedirs(self.cache_dir, exist_ok=True)

    def set_definitions_provider(
        self, provider: DefinitionsProvider | None
    ) -> None:
        """Attach the virtual-signal source (DBCManager-backed callable)."""
        self._definitions_provider = provider

    # ---------------------------------------------------------- indexing

    def start_indexing(
        self,
        log_file: str | os.PathLike[str],
        dbc: Any,
        dbc_hash: str | None = None,
    ) -> None:
        log_file_path = os.fspath(log_file)
        file_stat = os.stat(log_file_path)
        # The DBC is part of the cache key: switching DBCs on the same log
        # must not serve stale or missing signals (and switching back is a
        # cache hit, D8).
        hash8 = dbc_hash[:8] if dbc_hash else "nodbc"
        cache_key = (
            f"{os.path.basename(log_file_path)}_"
            f"{file_stat.st_size}_{file_stat.st_mtime}_{hash8}.sqlite"
        )
        db_path = os.path.join(self.cache_dir, cache_key)
        job = object()
        cancel_event = threading.Event()

        with self._state_lock:
            self._cancel_active_job_locked()
            self._cancel_compute_locked()
            self._close_connection_locked()
            self.log_file = log_file_path
            self.dbc = dbc
            self.dbc_hash = dbc_hash
            self.db_path = db_path
            self.status = "loading"
            self.progress = 0
            self.start_ts = 0
            self.end_ts = 0
            self._active_job = job
            self._cancel_event = cancel_event
            self.derived_status = "idle"
            self.derived_progress = 0
            self.derived_pending = []
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
                connection.execute("PRAGMA journal_mode=WAL")
                logger.info("Using cached log index: %s", db_path)
                cursor = connection.cursor()
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals")
                row = cursor.fetchone()
                self._raise_if_cancelled(job, cancel_event)
                start_ts, end_ts = (row[0], row[1]) if row and row[0] is not None else (0, 0)
                self._ensure_derived_tables(connection)
                self._publish_ready(job, cancel_event, connection, start_ts, end_ts)
                connection = None
                self._kick_derived_compute()
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
            self._kick_derived_compute()

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

    # ---------------------------------------------------- derived compute

    @staticmethod
    def _ensure_derived_tables(connection: sqlite3.Connection) -> None:
        """Lazily create derived tables (cached files predate them)."""
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS derived_signals (
                timestamp REAL, signal_id TEXT, value REAL
            );
            CREATE INDEX IF NOT EXISTS idx_derived_sig_time
                ON derived_signals(signal_id, timestamp);
            CREATE TABLE IF NOT EXISTS derived_meta (
                signal_id   TEXT PRIMARY KEY,
                def_hash    TEXT NOT NULL,
                row_count   INTEGER NOT NULL,
                computed_at REAL NOT NULL
            );
            """
        )
        connection.commit()

    def _derived_meta_map(self, connection: sqlite3.Connection) -> dict[str, str]:
        rows = connection.execute(
            "SELECT signal_id, def_hash FROM derived_meta"
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def _kick_derived_compute(self) -> None:
        """Start a derived compute if a provider is attached and raw is ready."""
        if self._definitions_provider is None:
            return
        with self._state_lock:
            if self.status != "ready" or not self.db_path:
                return
            if self._compute_thread is not None and self._compute_thread.is_alive():
                return  # the running job re-checks definitions when it finishes
            self._start_compute_locked()

    def _start_compute_locked(self) -> None:
        job = object()
        cancel = threading.Event()
        self._compute_job = job
        self._compute_cancel = cancel
        self.derived_status = "computing"
        self.derived_progress = 0
        thread = threading.Thread(
            target=self._compute_worker,
            args=(job, cancel, self.db_path),
            daemon=True,
        )
        self._compute_thread = thread
        thread.start()

    def request_wts_recompute(self, changed_ids: set[str] | None = None) -> None:
        """Debounced recompute trigger after a WTS mutation (on_wts_changed).

        Debouncing coalesces rapid edits; a running compute is cancelled and
        restarted with the latest definitions.
        """
        with self._state_lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(
                self.RECOMPUTE_DEBOUNCE_SECONDS, self._kick_derived_compute
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def _cancel_compute_locked(self) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.cancel()
            self._debounce_timer = None
        if self._compute_cancel is not None:
            self._compute_cancel.set()

    def _raise_if_compute_cancelled(
        self, job: object, cancel_event: threading.Event
    ) -> None:
        with self._state_lock:
            if cancel_event.is_set() or self._compute_job is not job:
                raise _IndexingCancelled()

    def _compute_worker(
        self, job: object, cancel_event: threading.Event, db_path: str
    ) -> None:
        """Recompute stale virtual signals from the immutable raw table (D9).

        Runs on full-resolution data (the raw table, never downsampled
        query output) with its own SQLite connection; the shared read
        connection is never touched here.
        """
        provider = self._definitions_provider
        if provider is None:
            return
        try:
            definitions, hashes = provider()
        except Exception as error:  # a broken provider must not corrupt state
            logger.error("Virtual-signal provider failed: %s", error, exc_info=True)
            with self._state_lock:
                if self._compute_job is job:
                    self.derived_status = "error"
            return

        connection: sqlite3.Connection | None = None
        try:
            self._raise_if_compute_cancelled(job, cancel_event)
            connection = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
            connection.execute("PRAGMA journal_mode=WAL")
            self._ensure_derived_tables(connection)

            meta = self._derived_meta_map(connection)
            stale = {
                name
                for name, definition_hash in hashes.items()
                if meta.get(f"{WTS_PREFIX}{name}") != definition_hash
            }
            removed = [
                signal_id
                for signal_id in meta
                if signal_id.startswith(WTS_PREFIX)
                and signal_id[len(WTS_PREFIX):] not in hashes
            ]
            with self._state_lock:
                self._compute_targets = {
                    f"{WTS_PREFIX}{name}" for name in stale
                }
                self.derived_pending = sorted(self._compute_targets)

            if not stale and not removed:
                with self._state_lock:
                    self.derived_status = "ready"
                    self.derived_progress = 100
                    self.derived_pending = []
                    self._compute_targets = set()
                return

            # Minimal subgraph: targets + their transitive WTS ancestors, so
            # fresh unrelated signals sharing raw inputs are not re-evaluated.
            active_defs = subgraph_defs(list(definitions), sorted(self._compute_targets))
            engine = VirtualSignalEngine(active_defs)
            inputs = sorted(engine.required_inputs())

            self._raise_if_compute_cancelled(job, cancel_event)
            totals = [
                connection.execute(
                    "SELECT COUNT(*) FROM signals WHERE signal_id = ?", (signal_id,)
                ).fetchone()[0]
                for signal_id in inputs
            ]
            total_rows = sum(totals) or 1

            # One cursor per raw input, merged on timestamp; never fetchall.
            # Explicit generator construction: a generator-expression nested
            # in a comprehension would share the loop-variable cell and make
            # every stream read the last cursor (late binding).
            streams = []
            for signal_id in inputs:
                cursor = connection.execute(
                    "SELECT timestamp, value FROM signals WHERE signal_id = ? "
                    "ORDER BY timestamp",
                    (signal_id,),
                )

                def rows_for(cursor=cursor, signal_id=signal_id):
                    for ts, value in cursor:
                        yield ts, signal_id, value

                streams.append(rows_for())
            merged = heapq.merge(*streams, key=lambda row: row[0])

            connection.execute(
                "CREATE TEMP TABLE IF NOT EXISTS derived_staging "
                "(timestamp REAL, signal_id TEXT, value REAL)"
            )
            connection.execute("DELETE FROM temp.derived_staging")

            targets = self._compute_targets

            batch: list[tuple[float, str, float]] = []
            processed = 0
            for ts, signal_id, value in run_batch(engine, merged):
                batch.append((ts, signal_id, value))
                if len(batch) >= self.DERIVED_SWAP_BATCH:
                    self._raise_if_compute_cancelled(job, cancel_event)
                    connection.executemany(
                        "INSERT INTO temp.derived_staging VALUES (?, ?, ?)", batch
                    )
                    processed += len(batch)
                    batch = []
                    self._raise_if_compute_cancelled(job, cancel_event)
                    with self._state_lock:
                        self.derived_progress = min(
                            99, int(processed / total_rows * 100)
                        )
            if batch:
                connection.executemany(
                    "INSERT INTO temp.derived_staging VALUES (?, ?, ?)", batch
                )
            self._raise_if_compute_cancelled(job, cancel_event)

            now = time.time()
            definition_hash_by_id = {
                f"{WTS_PREFIX}{name}": definition_hash
                for name, definition_hash in hashes.items()
            }
            # One transaction per target: readers never see a half-computed
            # signal; the old values stay visible until the swap.
            for signal_id in sorted(targets):
                self._raise_if_compute_cancelled(job, cancel_event)
                cursor = connection.execute(
                    "SELECT COUNT(*) FROM temp.derived_staging WHERE signal_id = ?",
                    (signal_id,),
                )
                row_count = cursor.fetchone()[0]
                connection.execute(
                    "DELETE FROM derived_signals WHERE signal_id = ?", (signal_id,)
                )
                connection.execute(
                    "INSERT INTO derived_signals "
                    "SELECT timestamp, signal_id, value FROM temp.derived_staging "
                    "WHERE signal_id = ?",
                    (signal_id,),
                )
                connection.execute(
                    "INSERT OR REPLACE INTO derived_meta "
                    "(signal_id, def_hash, row_count, computed_at) VALUES (?, ?, ?, ?)",
                    (
                        signal_id,
                        definition_hash_by_id.get(signal_id, ""),
                        row_count,
                        now,
                    ),
                )
                connection.commit()

            # Definitions deleted from the file leave no rows behind.
            for signal_id in removed:
                connection.execute(
                    "DELETE FROM derived_signals WHERE signal_id = ?", (signal_id,)
                )
                connection.execute(
                    "DELETE FROM derived_meta WHERE signal_id = ?", (signal_id,)
                )
            if removed:
                connection.commit()

            connection.execute("DELETE FROM temp.derived_staging")
            connection.commit()

            # Definitions changed while computing? Re-run with the latest.
            try:
                _latest_defs, latest_hashes = provider()
            except Exception:
                latest_hashes = hashes
            if latest_hashes != hashes:
                logger.info("Virtual signals changed during compute; recomputing")
                with self._state_lock:
                    if self._compute_job is job and not cancel_event.is_set():
                        self._start_compute_locked()
                return

            with self._state_lock:
                if self._compute_job is not job or cancel_event.is_set():
                    raise _IndexingCancelled()
                self.derived_status = "ready"
                self.derived_progress = 100
                self.derived_pending = []
                self._compute_targets = set()
            logger.info("Virtual-signal compute complete.")

        except _IndexingCancelled:
            logger.info("Virtual-signal compute cancelled; keeping previous rows")
            with self._state_lock:
                if self._compute_job is job:
                    self.derived_status = "idle"
                    self.derived_pending = []
        except Exception as error:
            logger.error("Error computing virtual signals: %s", error, exc_info=True)
            with self._state_lock:
                if self._compute_job is job and not cancel_event.is_set():
                    self.derived_status = "error"
        finally:
            if connection is not None:
                connection.close()

    # --------------------------------------------------------- lifecycle

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
            connection.execute("PRAGMA journal_mode=WAL")
            self._ensure_derived_tables(connection)
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

    def get_status(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "status": self.status,
                "progress": self.progress,
                "start_ts": self.start_ts,
                "end_ts": self.end_ts,
                "derived": {
                    "status": self.derived_status,
                    "progress": self.derived_progress,
                    "pending": list(self.derived_pending),
                },
            }

    # ------------------------------------------------------------- query

    def query(
        self,
        signals: list[str],
        start_ts: float,
        end_ts: float,
        max_points: int,
    ) -> dict[str, dict[str, list[float]]]:
        data, _pending = self.get_results(signals, start_ts, end_ts, max_points)
        return data

    def get_results(
        self,
        signals: list[str],
        start_ts: float,
        end_ts: float,
        max_points: int,
    ) -> tuple[dict[str, dict[str, list[float]]], list[str]]:
        """Bucketed series per signal id plus ``pending`` virtual ids.

        ``WTS.*`` ids read from ``derived_signals``; anything else from the
        immutable raw ``signals`` table. Ids still computing return empty
        arrays and appear in ``pending`` (the frontend polls and retries).
        """
        with self._state_lock:
            connection = self.conn
            ready = self.status == "ready" and connection is not None
            pending_state = set(self._compute_targets)

        if not ready:
            return {}, [
                signal for signal in signals if signal.startswith(WTS_PREFIX)
            ]

        span = end_ts - start_ts
        if span <= 0:
            return {}, []

        bucket_size = span / max_points
        result: dict[str, dict[str, list[float]]] = {}
        pending: list[str] = []
        try:
            for signal in signals:
                if signal.startswith(WTS_PREFIX):
                    # No rows yet (never computed or being recomputed) while
                    # compute is pending → empty + pending, never a mix.
                    is_pending = signal in pending_state
                    if is_pending and not self._derived_has_rows(connection, signal):
                        result[signal] = {"timestamps": [], "values": []}
                        pending.append(signal)
                        continue
                    table = "derived_signals"
                else:
                    table = "signals"
                rows = connection.execute(
                    """
                    SELECT
                        MIN(timestamp) as ts,
                        value
                    FROM {table}
                    WHERE signal_id = ? AND timestamp >= ? AND timestamp <= ?
                    GROUP BY CAST((timestamp - ?) / ? AS INTEGER)
                    ORDER BY ts ASC
                    """.format(table=table),
                    (signal, start_ts, end_ts, start_ts, bucket_size),
                ).fetchall()
                result[signal] = {
                    "timestamps": [row[0] for row in rows],
                    "values": [row[1] for row in rows],
                }
        except sqlite3.ProgrammingError:
            # The connection was closed concurrently (stop/re-index).
            logger.debug("Log query interrupted by connection close")
        return result, pending

    @staticmethod
    def _derived_has_rows(connection: sqlite3.Connection, signal_id: str) -> bool:
        row = connection.execute(
            "SELECT 1 FROM derived_signals WHERE signal_id = ? LIMIT 1",
            (signal_id,),
        ).fetchone()
        return row is not None

    def stop(self) -> None:
        with self._state_lock:
            self._cancel_active_job_locked()
            self._cancel_compute_locked()
            self._active_job = None
            self._cancel_event = None
            self._compute_job = None
            self._compute_cancel = None
            self._close_connection_locked()
            self.status = "idle"
            self.progress = 0
            self.start_ts = 0
            self.end_ts = 0
            self.derived_status = "idle"
            self.derived_progress = 0
            self.derived_pending = []
            self._compute_targets = set()


log_query_service = LogQueryService(
    os.path.join(os.environ.get("WOLFTRACK_USER_DATA", os.getcwd()), "logs", "cache")
)
