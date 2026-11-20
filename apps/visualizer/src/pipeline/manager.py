import asyncio
import time

from config import AppConfig
from logging_config import get_logger
from ws_manager import manager as ws_manager
from pipeline.source import DataSource, ZMQDataSource, LogFileDataSource

logger = get_logger(__name__)

# Rate limit for engine/decode errors: log the 1st and every Nth failure.
_ERROR_LOG_EVERY = 100


class PipelineManager:
    def __init__(self, config: AppConfig, dbc_manager=None):
        self.config = config
        self.dbc_manager = dbc_manager
        self.source: DataSource = None
        self._task = None
        # Live virtual-signal runtime (Part 4). None => fast path, no WTS.
        self.wts_runtime = None
        # Optional test/inspection hook: called with each live_batch payload.
        self.on_batch = None

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
            
            playback_speed = getattr(self.config.pipeline, 'playback_speed', 0.0)
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
        # New session: no virtual-signal state leaks over (Part 4.4).
        self.wts_runtime = None
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

    def _build_wts_runtime(self):
        """Build a LiveWtsRuntime from the active setup, or None if no usable defs.

        Broken defs are skipped by the manager (they are not in
        ``get_virtual_signals()``). An engine construction failure (should
        not happen for valid defs) is isolated here so a bad edit can never
        kill the live loop; the old runtime keeps running until the next
        version bump.
        """
        if self.dbc_manager is None:
            return None
        try:
            definitions = self.dbc_manager.get_virtual_signals()
            version = self.dbc_manager.get_wts_version()
            if not definitions:
                return None
            from wts.live import LiveWtsRuntime

            runtime = LiveWtsRuntime(definitions, version=version)
            logger.info(
                "WTS live runtime built: %d virtual signal(s), %d raw input(s)",
                len(definitions), len(runtime.raw_inputs),
            )
            return runtime
        except Exception as e:  # failure isolation (4.8)
            logger.error("WTS runtime rebuild failed: %s", e, exc_info=True)
            return self.wts_runtime

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
            dbc_version = (
                self.dbc_manager.get_wts_version() if self.dbc_manager else None
            )

            runtime = self._build_wts_runtime()
            self.wts_runtime = runtime
            pending_clock_step = False
            missing_ts_logged = False
            decode_errors = 0
            wts_errors = 0

            async for message in self.source.stream():
                current_time = time.time()

                # Hot reload (D13): any definitions/DBC change bumps the
                # version. Refresh db + arb_id_cache (also fixes the old
                # DBC-switch-while-live limitation) and rebuild the runtime;
                # virtual state restarts empty.
                version = (
                    self.dbc_manager.get_wts_version() if self.dbc_manager else None
                )
                if version != dbc_version:
                    dbc_version = version
                    db = (
                        self.dbc_manager.get_active_dbc()
                        if self.dbc_manager else None
                    )
                    arb_id_cache = {}
                    runtime = self._build_wts_runtime()
                    self.wts_runtime = runtime
                    logger.info("Live pipeline reloaded (setup/wts v%s).", version)

                frames_to_process = []
                message_dropped = 0
                
                if message.get("type") == "can_batch":
                    frames_to_process = message.get("frames", [])
                    message_dropped = message.get("dropped_batches", 0)
                    dropped_batches += message_dropped
                else:
                    frames_to_process = [message] # LogFile fallback

                runtime_active = runtime is not None and runtime.raw_inputs
                if message_dropped and runtime is not None:
                    # Real gap even when timestamps look continuous.
                    for frame in frames_to_process:
                        runtime.note_dropped(frame.get("timestamp"))
                        break
                
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
                    
                    # Decode gating: subscribed raw ids OR WTS raw inputs.
                    # With no virtual signals this is identical to before (I9).
                    any_subscribed = False
                    for sig_name, sig_id in signal_map.items():
                        if sig_id in ws_manager.subscribed_signals or (
                            runtime_active and sig_id in runtime.raw_inputs
                        ):
                            any_subscribed = True
                            break
                    
                    if not any_subscribed:
                        continue

                    frame_ts = frame.get("timestamp")
                    try:
                        data_bytes = bytes(frame["data"])
                        decoded = db.decode_message(arb_id, data_bytes)
                        timestamp = frame_ts if frame_ts is not None else current_time
                        
                        for sig_name, sig_value in decoded.items():
                            sig_id = signal_map.get(sig_name)
                            if sig_id and sig_id in ws_manager.subscribed_signals:
                                if sig_id not in live_batch:
                                    live_batch[sig_id] = {"timestamps": [], "values": []}
                                live_batch[sig_id]["timestamps"].append(timestamp)
                                live_batch[sig_id]["values"].append(sig_value)
                    except Exception as e:
                        # Failure isolation (4.3): counted, rate-limited; the
                        # loop keeps running.
                        decode_errors += 1
                        if decode_errors % _ERROR_LOG_EVERY == 1:
                            logger.debug(
                                "Frame decode failed (%d so far): %s",
                                decode_errors, e, exc_info=True,
                            )
                        continue

                    # Virtual signals (D13: always-on; I8 handled by engine).
                    # Fast-path bypass: zero overhead when nothing is defined.
                    if not runtime_active:
                        continue
                    if frame_ts is None:
                        # Never substitute the backend wall clock (D11).
                        if not missing_ts_logged:
                            missing_ts_logged = True
                            logger.warning(
                                "Live frame without a timestamp; skipping such "
                                "frames for virtual signals this session."
                            )
                        runtime.process(None, {})  # count only
                        continue
                    try:
                        needed = {
                            sig_id: decoded[sig_name]
                            for sig_name, sig_id in signal_map.items()
                            if sig_id in runtime.raw_inputs and sig_name in decoded
                        }
                        if needed:
                            outputs, clock_step = runtime.process(frame_ts, needed)
                            if clock_step and live_batch:
                                # Close the old-time-base batch first so every
                                # per-signal array stays non-decreasing (I8);
                                # the flag rides on the next (new-base) batch.
                                payload = {
                                    "type": "live_batch",
                                    "signals": live_batch,
                                    "dropped_batches": dropped_batches,
                                }
                                if self.on_batch is not None:
                                    self.on_batch(payload)
                                await ws_manager.broadcast_json(payload)
                                live_batch = {}
                                dropped_batches = 0
                            if clock_step:
                                pending_clock_step = True
                            for wts_id, value in outputs.items():
                                if wts_id in ws_manager.subscribed_signals:
                                    entry = live_batch.get(wts_id)
                                    if entry is None:
                                        entry = live_batch[wts_id] = {
                                            "timestamps": [], "values": []
                                        }
                                    entry["timestamps"].append(frame_ts)
                                    entry["values"].append(value)
                    except Exception as e:
                        wts_errors += 1
                        if wts_errors % _ERROR_LOG_EVERY == 1:
                            logger.error(
                                "Virtual-signal update failed (%d so far): %s",
                                wts_errors, e, exc_info=True,
                            )
                        
                # Flush logic
                if current_time - last_flush_time >= flush_interval:
                    if live_batch or dropped_batches > 0:
                        payload = {
                            "type": "live_batch",
                            "signals": live_batch,
                            "dropped_batches": dropped_batches
                        }
                        if pending_clock_step:
                            payload["clock_step"] = True  # additive (I7)
                            pending_clock_step = False
                        if self.on_batch is not None:
                            self.on_batch(payload)
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
                if pending_clock_step:
                    payload["clock_step"] = True
                if self.on_batch is not None:
                    self.on_batch(payload)
                await ws_manager.broadcast_json(payload)
            
            # Broadcast stopped status when the stream finishes naturally
            await self._broadcast_status("stopped")
            logger.info("PipelineManager stream finished naturally.")
        except asyncio.CancelledError:
            logger.info("PipelineManager loop cancelled.")
        except Exception as e:
            logger.error(f"PipelineManager error: {e}", exc_info=True)
            await self._broadcast_status("error", str(e))
