import asyncio
import time
from typing import List

from config import AppConfig
from logging_config import get_logger
from ws_manager import manager as ws_manager
from pipeline.source import DataSource, ZMQDataSource, LogFileDataSource
from pipeline.processor import Processor

logger = get_logger(__name__)

class DataPipeline:
    def __init__(self, processors: List[Processor] = None):
        self.processors_by_signal = {}
        if processors:
            for processor in processors:
                self.add_processor(processor)
        
    def add_processor(self, processor: Processor):
        if processor.target_signal not in self.processors_by_signal:
            self.processors_by_signal[processor.target_signal] = []
        self.processors_by_signal[processor.target_signal].append(processor)
        
    def process_signal(self, signal: dict) -> dict:
        signal_id = signal.get("id")
        if signal_id in self.processors_by_signal:
            for processor in self.processors_by_signal[signal_id]:
                signal = processor(signal)
        return signal

class PipelineManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.source: DataSource = None
        self.pipeline = DataPipeline()
        self._task = None
        
        self._setup_from_config()
        
    def _setup_from_config(self):
        # Default to ZMQ
        source_type = "zmq"
        
        if hasattr(self.config, 'pipeline') and hasattr(self.config.pipeline, 'source'):
            source_type = self.config.pipeline.source.lower()
            
        if source_type == 'logfile':
            log_file = "data.blf"
            if hasattr(self.config, 'pipeline') and hasattr(self.config.pipeline, 'log_file'):
                log_file = self.config.pipeline.log_file
            
            playback_speed = getattr(self.config.pipeline, 'playback_speed', 1.0)
            dbc_file = getattr(self.config.pipeline, 'dbc_file', None)
                
            self.source = LogFileDataSource(
                log_file_path=log_file,
                playback_speed=playback_speed,
                dbc_file=dbc_file
            )
        else:
            live_source = getattr(self.config, 'live_source', None)
            has_runtime_endpoint = bool(
                live_source
                and live_source.connected
                and live_source.zmq_host
                and live_source.zmq_port
            )

            if has_runtime_endpoint:
                self.source = ZMQDataSource(self.config)
            else:
                self.source = None
                logger.info("PipelineManager initialized without an active live source.")

    def has_source(self) -> bool:
        return self.source is not None

    async def _broadcast_status(self, status: str, detail: str | None = None):
        payload = {
            "type": "status",
            "status": status,
            "source": getattr(self.config.pipeline, "source", "unknown"),
            "detail": detail,
        }
        await ws_manager.broadcast_json(payload)

    async def start(self):
        if not self.source:
            logger.info("PipelineManager start skipped because no source is configured.")
            await self._broadcast_status("stopped", "No active live source configured.")
            return

        logger.info("PipelineManager starting...")
        await self.source.connect()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("PipelineManager started.")
        await self._broadcast_status("running")

    async def stop(self):
        logger.info("PipelineManager stopping...")
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.source:
            await self.source.disconnect()
        logger.info("PipelineManager stopped.")
        await self._broadcast_status("stopped")

    async def _run_loop(self):
        try:
            async for message in self.source.stream():
                if "decoded" in message and isinstance(message["decoded"], dict):
                    processed_signals = []
                    message_name = message.get("message_name", "Unknown")
                    for signal_name, signal_value in message["decoded"].items():
                        signal_id = f"{message_name}.{signal_name}"
                        signal_payload = {
                            "id": signal_id,
                            "name": signal_name,
                            "value": signal_value,
                            "arbitration_id": message.get("arbitration_id"),
                            "timestamp": message.get("timestamp", time.time())
                        }
                        processed_signal = self.pipeline.process_signal(signal_payload)
                        processed_signals.append(processed_signal)
                        
                    if processed_signals:
                        await ws_manager.broadcast_json(processed_signals)
                else:
                    pass
            
            # Broadcast stopped status when the stream finishes naturally
            await self._broadcast_status("stopped")
            logger.info("PipelineManager stream finished naturally.")
        except asyncio.CancelledError:
            logger.info("PipelineManager loop cancelled.")
        except Exception as e:
            logger.error(f"PipelineManager error: {e}", exc_info=True)
            await self._broadcast_status("error", str(e))
