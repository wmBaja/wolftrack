import os
import asyncio
import sqlite3
import threading
import time
from logging_config import get_logger

logger = get_logger(__name__)

class LogQueryService:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.status = "idle"
        self.progress = 0
        self.log_file = None
        self.dbc = None
        self.db_path = None
        self.conn = None
        self._task = None
        self.start_ts = 0
        self.end_ts = 0

    def start_indexing(self, log_file, dbc):
        self.log_file = log_file
        self.dbc = dbc
        
        # Simple cache key based on file name and size
        file_stat = os.stat(log_file)
        cache_key = f"{os.path.basename(log_file)}_{file_stat.st_size}_{file_stat.st_mtime}.sqlite"
        self.db_path = os.path.join(self.cache_dir, cache_key)
        
        self.status = "loading"
        self.progress = 0
        self._task = threading.Thread(target=self._index_worker, daemon=True)
        self._task.start()

    def _index_worker(self):
        try:
            is_cached = os.path.exists(self.db_path)
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            
            if is_cached:
                logger.info(f"Using cached log index: {self.db_path}")
                cursor = self.conn.cursor()
                cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM signals")
                row = cursor.fetchone()
                if row and row[0] is not None:
                    self.start_ts, self.end_ts = row[0], row[1]
                self.progress = 100
                self.status = "ready"
                return

            logger.info(f"Indexing log file: {self.log_file}")
            cursor = self.conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS signals (timestamp REAL, signal_id TEXT, value REAL)")
            
            import can
            reader = can.BLFReader(self.log_file)
            
            file_size = os.path.getsize(self.log_file)
            bytes_read = 0
            
            batch = []
            min_ts = float('inf')
            max_ts = float('-inf')
            
            # Fast signal map cache
            arb_id_cache = {}
            
            for msg in reader:
                # Approximate progress based on file position (BLFReader doesn't expose tell directly, 
                # but we can just use a generic progress or read the file size)
                # We'll just bump progress artificially or rely on time.
                # Actually, can't easily track BLF byte offset without wrapping the file.
                
                timestamp = getattr(msg, 'timestamp', 0)
                if timestamp < min_ts: min_ts = timestamp
                if timestamp > max_ts: max_ts = timestamp
                
                arb_id = msg.arbitration_id
                if arb_id not in arb_id_cache:
                    try:
                        msg_obj = self.dbc.get_message_by_frame_id(arb_id)
                        signal_map = {}
                        for sig in msg_obj.signals:
                            signal_map[sig.name] = f"{msg_obj.name}.{sig.name}"
                        arb_id_cache[arb_id] = signal_map
                    except KeyError:
                        arb_id_cache[arb_id] = None
                        
                signal_map = arb_id_cache[arb_id]
                if signal_map:
                    try:
                        decoded = self.dbc.decode_message(arb_id, msg.data)
                        for sig_name, sig_value in decoded.items():
                            sig_id = signal_map.get(sig_name)
                            if sig_id:
                                batch.append((timestamp, sig_id, float(sig_value)))
                    except Exception:
                        pass
                
                if len(batch) >= 10000:
                    cursor.executemany("INSERT INTO signals VALUES (?, ?, ?)", batch)
                    self.conn.commit()
                    batch = []
                    
                    # Update progress (fake it for now since we don't have byte offset)
                    self.progress = min(99, self.progress + 1)
            
            if batch:
                cursor.executemany("INSERT INTO signals VALUES (?, ?, ?)", batch)
                self.conn.commit()
                
            logger.info("Creating indexes...")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sig_time ON signals(signal_id, timestamp)")
            self.conn.commit()
            
            self.start_ts = min_ts if min_ts != float('inf') else 0
            self.end_ts = max_ts if max_ts != float('-inf') else 0
            
            self.progress = 100
            self.status = "ready"
            logger.info("Indexing complete.")
            
        except Exception as e:
            logger.error(f"Error indexing log file: {e}", exc_info=True)
            self.status = "error"

    def get_status(self):
        return {
            "status": self.status,
            "progress": self.progress,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts
        }

    def query(self, signals, start_ts, end_ts, max_points):
        if self.status != "ready" or not self.conn:
            return {}
            
        cursor = self.conn.cursor()
        result = {}
        
        # Calculate bucket size
        span = end_ts - start_ts
        if span <= 0: return {}
        bucket_size = span / max_points
        
        for sig in signals:
            # Downsample using min/max per bucket
            # SQLite doesn't have a direct bucketing function, but we can group by cast( (timestamp - start_ts) / bucket_size as integer )
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
            
            timestamps = [r[0] for r in rows]
            values = [r[1] for r in rows]
            result[sig] = {
                "timestamps": timestamps,
                "values": values
            }
            
        return result

    def stop(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        self.status = "idle"

log_query_service = LogQueryService(os.path.join(os.environ.get("WOLFTRACK_USER_DATA", os.getcwd()), "logs", "cache"))
