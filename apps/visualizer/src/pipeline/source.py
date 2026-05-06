import abc
import asyncio
import typing
import zmq
import zmq.asyncio

from config import AppConfig
from logging_config import get_logger

logger = get_logger(__name__)

class DataSource(abc.ABC):
    @abc.abstractmethod
    async def connect(self):
        pass

    @abc.abstractmethod
    async def disconnect(self):
        pass

    @abc.abstractmethod
    async def stream(self) -> typing.AsyncGenerator[dict, None]:
        pass

class ZMQDataSource(DataSource):
    def __init__(self, config: AppConfig, db=None):
        self.config = config
        self.zmq_context = zmq.asyncio.Context()
        self.sock = None
        self.db = db

    async def connect(self):
        self.sock = self.zmq_context.socket(zmq.SUB)
        zmq_url = f"tcp://{self.config.zmq.host}:{self.config.zmq.port}"
        self.sock.connect(zmq_url)
        self.sock.setsockopt_string(zmq.SUBSCRIBE, "")
        logger.info(f"ZMQDataSource connected to {zmq_url}")

    async def disconnect(self):
        if self.sock:
            self.sock.close(linger=0)
        self.zmq_context.destroy(linger=0)
        logger.info("ZMQDataSource disconnected")

    async def stream(self) -> typing.AsyncGenerator[dict, None]:
        if not self.sock:
            raise RuntimeError("ZMQ socket not connected. Call connect() first.")
        
        while True:
            try:
                message = await self.sock.recv_json()
                
                if self.db and "arbitration_id" in message and "data" in message:
                    try:
                        data_bytes = bytes(message["data"])
                        decoded = self.db.decode_message(message['arbitration_id'], data_bytes)
                        message['decoded'] = decoded
                        msg_obj = self.db.get_message_by_frame_id(message['arbitration_id'])
                        message['message_name'] = msg_obj.name
                    except KeyError:
                        pass
                
                yield message
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ZMQ Stream Error: {e}", exc_info=True)
                break

class LogFileDataSource(DataSource):
    def __init__(self, log_file_path: str, playback_speed: float = 1.0, db=None):
        self.log_file_path = log_file_path
        self.playback_speed = playback_speed
        self.db = db
        self._reader = None

    async def connect(self):
        logger.info(f"LogFileDataSource loading log file: {self.log_file_path}")
        # can.BLFReader reads the file sync, but yields messages sequentially
        import can
        self._reader = can.BLFReader(self.log_file_path)
        logger.info(f"Loaded BLF LogFile: {self.log_file_path}")

    async def disconnect(self):
        if self._reader:
            self._reader.stop()
        logger.info("LogFileDataSource disconnected")

    async def stream(self) -> typing.AsyncGenerator[dict, None]:
        if not self._reader:
            raise RuntimeError("Log file not loaded. Call connect() first.")
        
        logger.info("Log playback stream loop started.")
        last_timestamp = None
        for msg in self._reader:
            if self.playback_speed > 0:
                current_timestamp = getattr(msg, 'timestamp', 0)
                if last_timestamp is not None and current_timestamp >= last_timestamp:
                    time_diff = current_timestamp - last_timestamp
                    sleep_time = time_diff / self.playback_speed
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                last_timestamp = current_timestamp
            else:
                await asyncio.sleep(0)
            
            payload = {
                "timestamp": getattr(msg, 'timestamp', 0),
                "arbitration_id": msg.arbitration_id,
                "data": list(msg.data)
            }
            
            if self.db:
                try:
                    payload['decoded'] = self.db.decode_message(msg.arbitration_id, msg.data)
                    msg_obj = self.db.get_message_by_frame_id(msg.arbitration_id)
                    payload['message_name'] = msg_obj.name
                except KeyError:
                    pass
            
            yield payload
