import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pipeline.log_query import LogQueryService


def test_progress_uses_file_position_and_stops_before_ready(tmp_path):
    service = LogQueryService(tmp_path)

    service._update_progress(625, 1_000)
    assert service.progress == 62

    service._update_progress(1_000, 1_000)
    assert service.progress == 99


def test_cached_index_is_ready_with_complete_progress(tmp_path):
    log_file = tmp_path / "session.blf"
    log_file.write_bytes(b"cached log")
    service = LogQueryService(tmp_path)
    cache_key = (
        f"{log_file.name}_{log_file.stat().st_size}_"
        f"{log_file.stat().st_mtime}.sqlite"
    )
    connection = sqlite3.connect(tmp_path / cache_key)
    connection.execute(
        "CREATE TABLE signals (timestamp REAL, signal_id TEXT, value REAL)"
    )
    connection.execute("INSERT INTO signals VALUES (1.0, 'Vehicle.speed', 10.0)")
    connection.commit()
    connection.close()

    service.start_indexing(str(log_file), dbc=None)
    service._task.join(timeout=2)

    assert service.get_status() == {
        "status": "ready",
        "progress": 100,
        "start_ts": 1.0,
        "end_ts": 1.0,
    }


def test_indexing_handles_reader_closing_the_stream_at_eof(tmp_path, monkeypatch):
    log_file = tmp_path / "session.blf"
    log_file.write_bytes(b"log data")

    class ClosingReader:
        def __init__(self, handle):
            self.handle = handle

        def __iter__(self):
            yield SimpleNamespace(timestamp=1.0, arbitration_id=1, data=b"\x01")
            self.handle.close()

        def stop(self):
            self.handle.close()

    class Dbc:
        def get_message_by_frame_id(self, arbitration_id):
            return SimpleNamespace(
                name="Vehicle",
                signals=[SimpleNamespace(name="speed")],
            )

        def decode_message(self, arbitration_id, data):
            return {"speed": 12.0}

    monkeypatch.setitem(sys.modules, "can", SimpleNamespace(BLFReader=ClosingReader))
    service = LogQueryService(tmp_path)
    service.log_file = str(log_file)
    service.db_path = str(tmp_path / "index.sqlite")
    service.dbc = Dbc()
    service.status = "loading"

    service._index_worker()

    assert service.get_status()["status"] == "ready"
    assert service.get_status()["progress"] == 100
    assert Path(service.db_path).exists()
    assert not list(tmp_path.glob("*.partial"))


def test_stop_cancels_indexing_and_discards_temporary_cache(tmp_path, monkeypatch):
    log_file = tmp_path / "session.blf"
    log_file.write_bytes(b"log data")
    waiting_for_next_message = threading.Event()
    release_reader = threading.Event()

    class BlockingReader:
        def __init__(self, handle):
            self.handle = handle

        def __iter__(self):
            yield SimpleNamespace(timestamp=1.0, arbitration_id=1, data=b"\x01")
            waiting_for_next_message.set()
            release_reader.wait(timeout=2)
            yield SimpleNamespace(timestamp=2.0, arbitration_id=1, data=b"\x02")

        def stop(self):
            self.handle.close()

    class Dbc:
        def __init__(self):
            self.decoded_messages = []

        def get_message_by_frame_id(self, arbitration_id):
            return SimpleNamespace(
                name="Vehicle",
                signals=[SimpleNamespace(name="speed")],
            )

        def decode_message(self, arbitration_id, data):
            self.decoded_messages.append(data)
            return {"speed": 12.0}

    monkeypatch.setitem(sys.modules, "can", SimpleNamespace(BLFReader=BlockingReader))
    dbc = Dbc()
    service = LogQueryService(tmp_path)
    service.start_indexing(str(log_file), dbc)

    assert waiting_for_next_message.wait(timeout=2)
    service.stop()
    assert service.get_status() == {
        "status": "idle",
        "progress": 0,
        "start_ts": 0,
        "end_ts": 0,
    }

    release_reader.set()
    service._task.join(timeout=2)

    assert not service._task.is_alive()
    assert dbc.decoded_messages == [b"\x01"]
    assert list(tmp_path.iterdir()) == [log_file]
