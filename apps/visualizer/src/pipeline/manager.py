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
        signal_name = signal.get("name")
        if signal_name in self.processors_by_signal:
            for processor in self.processors_by_signal[signal_name]:
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
            self.source = ZMQDataSource(self.config)
            
        pass

    async def start(self):
        if not self.source:
            logger.error("No DataSource configured for PipelineManager.")
            return

        logger.info("PipelineManager starting...")
        await self.source.connect()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("PipelineManager started.")

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

    async def _run_loop(self):
        try:
            async for message in self.source.stream():
                if "decoded" in message and isinstance(message["decoded"], dict):
                    processed_signals = []
                    for signal_name, signal_value in message["decoded"].items():
                        signal_payload = {
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
        except asyncio.CancelledError:
            logger.info("PipelineManager loop cancelled.")
        except Exception as e:
            logger.error(f"PipelineManager error: {e}", exc_info=True)
