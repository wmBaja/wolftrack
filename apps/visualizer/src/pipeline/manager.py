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
    def __init__(self, config: AppConfig, dbc_manager=None):
        self.config = config
        self.dbc_manager = dbc_manager
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
            db = self.dbc_manager.get_active_dbc() if self.dbc_manager else None
            self.source = LogFileDataSource(
                log_file_path=log_file,
                playback_speed=playback_speed,
                db=db
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
            # 50 ms batching interval
            flush_interval = 0.050
            last_flush_time = time.time()
            
            # buffer structure: { signal_id: { "timestamps": [], "values": [] } }
            live_batch = {}
            dropped_batches = 0
            
            db = self.dbc_manager.get_active_dbc() if self.dbc_manager else None
            arb_id_cache = {}

            async for message in self.source.stream():
                current_time = time.time()
                frames_to_process = []
                
                if message.get("type") == "can_batch":
                    frames_to_process = message.get("frames", [])
                    dropped_batches += message.get("dropped_batches", 0)
                else:
                    frames_to_process = [message] # LogFile fallback
                
                for frame in frames_to_process:
                    arb_id = frame.get("arbitration_id")
                    
                    if not db or arb_id is None:
                        continue
                        
                    if arb_id not in arb_id_cache:
                        try:
                            msg_obj = db.get_message_by_frame_id(arb_id)
                            signal_map = {}
                            for sig in msg_obj.signals:
                                signal_map[sig.name] = f"{msg_obj.name}.{sig.name}"
                            arb_id_cache[arb_id] = (msg_obj.name, signal_map)
                        except KeyError:
                            arb_id_cache[arb_id] = None
                            
                    cache_entry = arb_id_cache[arb_id]
                    if not cache_entry:
                        continue
                        
                    msg_name, signal_map = cache_entry
                    
                    any_subscribed = False
                    for sig_name, sig_id in signal_map.items():
                        if sig_id in ws_manager.subscribed_signals:
                            any_subscribed = True
                            break
                    
                    if not any_subscribed:
                        continue
                        
                    try:
                        data_bytes = bytes(frame["data"])
                        decoded = db.decode_message(arb_id, data_bytes)
                        timestamp = frame.get("timestamp", current_time)
                        
                        for sig_name, sig_value in decoded.items():
                            sig_id = signal_map.get(sig_name)
                            if sig_id and sig_id in ws_manager.subscribed_signals:
                                if sig_id not in live_batch:
                                    live_batch[sig_id] = {"timestamps": [], "values": []}
                                live_batch[sig_id]["timestamps"].append(timestamp)
                                live_batch[sig_id]["values"].append(sig_value)
                    except Exception:
                        pass
                        
                # Flush logic
                if current_time - last_flush_time >= flush_interval:
                    if live_batch or dropped_batches > 0:
                        payload = {
                            "type": "live_batch",
                            "signals": live_batch,
                            "dropped_batches": dropped_batches
                        }
                        await ws_manager.broadcast_json(payload)
                        live_batch = {}
                        dropped_batches = 0
                    last_flush_time = current_time
                    
            if live_batch or dropped_batches > 0:
                payload = {
                    "type": "live_batch",
                    "signals": live_batch,
                    "dropped_batches": dropped_batches
                }
                await ws_manager.broadcast_json(payload)
            
            # Broadcast stopped status when the stream finishes naturally
            await self._broadcast_status("stopped")
            logger.info("PipelineManager stream finished naturally.")
        except asyncio.CancelledError:
            logger.info("PipelineManager loop cancelled.")
        except Exception as e:
            logger.error(f"PipelineManager error: {e}", exc_info=True)
            await self._broadcast_status("error", str(e))
