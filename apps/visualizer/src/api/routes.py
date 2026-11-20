import csv
import contextlib
import io
import os
import shutil
import sqlite3
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from ws_manager import manager
from dbc_manager import DbcConflictError
from pipeline.manager import PipelineManager
from pipeline.source import LogFileDataSource
from pipeline.log_query import log_query_service

class LogQueryRequest(BaseModel):
    signals: list[str]
    start_ts: float
    end_ts: float
    max_points: int

router = APIRouter()

US_EXPORT_TIMEZONES = {
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Anchorage",
    "Pacific/Honolulu",
    "America/Phoenix",
}

class ConfigUpdate(BaseModel):
    source: str
    log_file: Optional[str] = None
    dbc_file: Optional[str] = None
    playback_speed: Optional[float] = None


class LiveSourceConnectRequest(BaseModel):
    flask_host: str
    flask_port: int
    zmq_host: str
    zmq_port: int


class RenameRequest(BaseModel):
    new_name: str


def serialize_live_source(config):
    live_source = config.live_source
    return {
        "connected": live_source.connected,
        "flask_host": live_source.flask_host,
        "flask_port": live_source.flask_port,
        "zmq_host": live_source.zmq_host,
        "zmq_port": live_source.zmq_port,
    }


def serialize_live_source_event(config):
    return {
        "type": "live_source",
        **serialize_live_source(config),
    }


def _build_export_filename() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"wolftrack-export-{timestamp}.csv"


def _reindex_active_log(request: Request) -> None:
    """Re-index the configured log for the current active setup (D8 cache key).

    Called whenever the active setup changes (select/upload auto-select/
    delete/rename). The DBC hash is part of the cache key, so switching
    setups on the same log is a cache hit for a pair indexed before and
    never serves stale or missing signals.
    """
    config = getattr(request.app.state, "config", None)
    pipeline = getattr(config, "pipeline", None) if config else None
    if not pipeline or (pipeline.source or "").lower() != "logfile":
        return
    log_file = getattr(pipeline, "log_file", None)
    if not log_file or not os.path.exists(log_file):
        return
    dbc_manager = getattr(request.app.state, "dbc_manager", None)
    active_dbc = dbc_manager.get_active_dbc() if dbc_manager else None
    if not active_dbc:
        log_query_service.stop()
        return
    log_query_service.start_indexing(
        log_file, active_dbc, dbc_manager.get_active_dbc_hash()
    )


def _format_export_timestamp(raw_timestamp: float, timezone_name: str) -> str:
    localized = datetime.fromtimestamp(raw_timestamp, tz=timezone.utc).astimezone(ZoneInfo(timezone_name))
    return localized.isoformat()


def _validate_export_request(request: Request, timezone_name: str):
    log_file = getattr(request.app.state.config.pipeline, "log_file", None)
    if not log_file or not os.path.exists(log_file):
        raise HTTPException(status_code=400, detail="No configured log file was found.")

    if timezone_name not in US_EXPORT_TIMEZONES:
        raise HTTPException(status_code=400, detail="Timezone must be one of the supported United States options.")

    dbc_manager = getattr(request.app.state, "dbc_manager", None)
    active_dbc = dbc_manager.get_active_dbc() if dbc_manager else None
    if not active_dbc:
        raise HTTPException(status_code=400, detail="No active DBC is loaded.")

    return log_file, active_dbc


async def _collect_export_rows(request: Request, timezone_name: str) -> list[dict[str, object]]:
    log_file, active_dbc = _validate_export_request(request, timezone_name)
    source = LogFileDataSource(log_file_path=log_file, playback_speed=0, db=active_dbc)
    sortable: list[tuple[float, int, dict[str, object]]] = []

    try:
        await source.connect()
        async for message in source.stream():
            decoded = message.get("decoded")
            if not isinstance(decoded, dict):
                continue

            message_name = message.get("message_name")
            if not message_name:
                continue

            dbc_message = active_dbc.get_message_by_name(message_name)
            signal_units = {
                signal.name: signal.unit or ""
                for signal in dbc_message.signals
            }

            timestamp = float(message.get("timestamp", 0))
            formatted_timestamp = _format_export_timestamp(timestamp, timezone_name)
            for signal_name, signal_value in decoded.items():
                sortable.append((timestamp, len(sortable), {
                    "timestamp": formatted_timestamp,
                    "signal_name": signal_name,
                    "value": signal_value,
                    "unit": signal_units.get(signal_name, ""),
                }))
    finally:
        await source.disconnect()

    # Virtual-signal rows interleaved by raw timestamp; a stable sort keeps
    # the BLF order of raw rows that share a timestamp.
    for timestamp, row in _collect_derived_export_rows(request, timezone_name):
        sortable.append((timestamp, len(sortable), row))
    sortable.sort(key=lambda item: (item[0], item[1]))
    return [row for _, _, row in sortable]


def _collect_derived_export_rows(
    request: Request, timezone_name: str
) -> list[tuple[float, dict[str, object]]]:
    """Virtual-signal rows from the derived index (Part 3, Q6).

    Raises 409 while derived compute is still running so a partial export is
    never produced. With no virtual signals or no index this is a no-op, so
    the raw-only export behavior is unchanged. Returns (raw_ts, row) pairs.
    """
    status = log_query_service.get_status()
    if status.get("status") != "ready":
        return []
    derived = status.get("derived") or {}
    if derived.get("status") == "computing":
        raise HTTPException(
            status_code=409,
            detail="Virtual signals are still being computed; try the export "
                   "again in a moment.",
        )
    if derived.get("status") != "ready":
        return []

    dbc_manager = getattr(request.app.state, "dbc_manager", None)
    if dbc_manager is None:
        return []
    units = {
        signal["id"]: (signal.get("unit") or "")
        for signal in dbc_manager.get_signals()
        if signal.get("is_virtual")
    }
    if not units:
        return []

    db_path = getattr(log_query_service, "db_path", None)
    if not db_path or not os.path.exists(db_path):
        return []

    rows: list[tuple[float, dict[str, object]]] = []
    with contextlib.closing(
        sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30)
    ) as connection:
        try:
            cursor = connection.execute(
                "SELECT timestamp, signal_id, value FROM derived_signals "
                "ORDER BY timestamp"
            )
        except sqlite3.OperationalError:
            return []  # index predates derived tables
        for raw_timestamp, signal_id, value in cursor:
            raw_timestamp = float(raw_timestamp)
            formatted = _format_export_timestamp(raw_timestamp, timezone_name)
            rows.append((raw_timestamp, {
                "timestamp": formatted,
                "signal_name": signal_id,
                "value": value,
                "unit": units.get(signal_id, ""),
            }))
    return rows


def _build_sheet_name(signal_name: str, used_names: set[str]) -> str:
    base_name = signal_name[:31] or "Signal"
    candidate = base_name
    suffix_index = 1

    while candidate in used_names:
        suffix = f"_{suffix_index}"
        candidate = f"{base_name[:31 - len(suffix)]}{suffix}"
        suffix_index += 1

    used_names.add(candidate)
    return candidate

@router.get("/api/config")
async def get_config(request: Request):
    pipeline_config = request.app.state.config.pipeline
    return {
        "source": pipeline_config.source,
        "log_file": pipeline_config.log_file,
        "dbc_file": pipeline_config.dbc_file,
        "playback_speed": getattr(pipeline_config, "playback_speed", 0.0)
    }


@router.get("/api/live_source")
async def get_live_source(request: Request):
    return serialize_live_source(request.app.state.config)

@router.get("/api/signals")
async def get_signals(request: Request):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        return {"signals": []}
    
    return {"signals": dbc_manager.get_signals()}

@router.get("/api/dbc")
async def get_dbc_info(request: Request):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        return {"available": [], "active": None}
    
    return {
        "available": dbc_manager.get_available_dbcs(),
        "active": dbc_manager.active_dbc_filename
    }

@router.post("/api/dbc/upload")
async def upload_dbc_route(
    request: Request,
    file: UploadFile = File(...)
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
        
    try:
        content = await file.read()
        dbc_manager.upload_dbc(file.filename or '', content)
    except ValueError as error:
        status_code = 409 if isinstance(error, DbcConflictError) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

    # Uploading the first setup auto-selects it; re-point the log index too.
    _reindex_active_log(request)

    return {"status": "success", "message": f"DBC {file.filename} uploaded successfully"}

@router.post("/api/dbc/select")
async def select_dbc_route(
    request: Request,
    filename: str = Form(...)
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
        
    try:
        success = dbc_manager.select_dbc(filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to select DBC {filename}")
        
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

    _reindex_active_log(request)

    return {"status": "success", "message": f"DBC {filename} selected"}

@router.get("/api/dbc/{filename}/download")
async def download_dbc_route(request: Request, filename: str):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")

    try:
        file_path = dbc_manager._get_dbc_path(filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Setup {filename} not found")

    content = file_path.read_bytes()
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/api/dbc/{filename}")
async def delete_dbc_route(
    request: Request,
    filename: str
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")

    was_active = dbc_manager.active_dbc_filename == filename
    try:
        success = dbc_manager.delete_dbc(filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not success:
        raise HTTPException(status_code=404, detail=f"DBC {filename} not found")
        
    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

    if was_active:
        _reindex_active_log(request)

    return {
        "status": "success",
        "message": f"DBC {filename} deleted",
    }


@router.patch("/api/dbc/{filename}")
async def rename_dbc_route(
    request: Request,
    filename: str,
    payload: RenameRequest,
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")

    was_active = dbc_manager.active_dbc_filename == filename
    try:
        success = dbc_manager.rename_dbc(filename, payload.new_name)
    except ValueError as error:
        status_code = 409 if 'already exists' in str(error) else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    if not success:
        raise HTTPException(status_code=404, detail=f"DBC {filename} not found")

    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

    if was_active and getattr(request.app.state.config, 'pipeline', None):
        request.app.state.config.pipeline.dbc_file = dbc_manager.get_active_setup_path()
        # Promotion on first save rewrites dbc_file, but the index cache key
        # is unchanged (same DBC hash) — no log re-index needed for a rename.

    return {
        "status": "success",
        "old_name": filename,
        "new_name": payload.new_name,
    }

@router.post("/api/upload_config")
async def upload_config(
    request: Request,
    source: str = Form(...),
    playback_speed: float = Form(0.0),
    log_file_upload: Optional[UploadFile] = File(None),
    dbc_file_upload: Optional[UploadFile] = File(None),
    existing_log: Optional[str] = Form(None),
    existing_dbc: Optional[str] = Form(None)
):
    if source not in ["zmq", "logfile"]:
        raise HTTPException(status_code=400, detail="Source must be 'zmq' or 'logfile'.")
        
    # Use a writable directory provided by the environment (e.g. Electron's userData path)
    base_dir = os.environ.get("WOLFTRACK_USER_DATA", os.getcwd())
    upload_dir = os.path.join(base_dir, "logs", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    config = request.app.state.config
    config.pipeline.source = source
    config.pipeline.playback_speed = playback_speed
    
    if source == "logfile":
        if log_file_upload and log_file_upload.filename:
            # Clear old logs
            for f in os.listdir(upload_dir):
                try:
                    os.remove(os.path.join(upload_dir, f))
                except Exception:
                    pass
            
            file_path = os.path.join(upload_dir, log_file_upload.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(log_file_upload.file, buffer)
            config.pipeline.log_file = file_path
        elif existing_log:
            if os.path.isabs(existing_log) and os.path.exists(existing_log):
                config.pipeline.log_file = existing_log
            else:
                config.pipeline.log_file = os.path.join(upload_dir, os.path.basename(existing_log))
        else:
            raise HTTPException(status_code=400, detail="Log file is required for logfile source.")
            
    # Setups are managed by DBCManager: point the config at the real path of
    # the active setup file (.dbc or .wts), or None when none is selected.
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if dbc_manager and dbc_manager.active_dbc_filename:
        # The pipeline manager pulls the DBC from the DBCManager; this is
        # informational, but the dashboard checks it is truthy before
        # fetching signals.
        config.pipeline.dbc_file = dbc_manager.get_active_setup_path()
    else:
        config.pipeline.dbc_file = None

    # Reinitialize pipeline manager. A logfile index is owned separately from
    # the playback pipeline, so it must be cancelled explicitly before a new
    # source configuration can replace it.
    log_query_service.stop()
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        
    request.app.state.pipeline_manager = PipelineManager(config, dbc_manager)
    if source == "zmq" and request.app.state.pipeline_manager.has_source():
        await request.app.state.pipeline_manager.start()
    elif source == "logfile":
        dbc_manager = getattr(request.app.state, 'dbc_manager', None)
        active_dbc = dbc_manager.get_active_dbc() if dbc_manager else None
        if active_dbc and config.pipeline.log_file:
            log_query_service.start_indexing(
                config.pipeline.log_file,
                active_dbc,
                dbc_manager.get_active_dbc_hash(),
            )
            
    return {"status": "success", "message": "Pipeline configuration uploaded and restarted successfully"}

@router.get("/api/logfile/status")
async def get_logfile_status():
    return log_query_service.get_status()

@router.post("/api/logfile/query")
async def query_logfile(payload: LogQueryRequest):
    data, pending = log_query_service.get_results(
        payload.signals, payload.start_ts, payload.end_ts, payload.max_points
    )
    return {"data": data, "pending": pending}


@router.get("/api/export_csv")
async def export_csv(request: Request, timezone_name: str = "America/New_York"):
    rows = await _collect_export_rows(request, timezone_name)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["timestamp", "signal_name", "value", "unit"])
    for row in rows:
        writer.writerow([
            row["timestamp"],
            row["signal_name"],
            row["value"],
            row["unit"],
        ])

    csv_content = "\ufeff" + buffer.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="{_build_export_filename()}"',
    }
    return StreamingResponse(
        iter([csv_content.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@router.get("/api/export_xlsx")
async def export_xlsx(request: Request, timezone_name: str = "America/New_York"):
    rows = await _collect_export_rows(request, timezone_name)
    grouped_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped_rows[str(row["signal_name"])].append(row)

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)
    header_font = Font(bold=True)
    used_sheet_names: set[str] = set()

    for signal_name, signal_rows in grouped_rows.items():
        sheet = workbook.create_sheet(title=_build_sheet_name(signal_name, used_sheet_names))
        sheet.append(["timestamp", "value", "unit"])
        for cell in sheet[1]:
            cell.font = header_font

        for row in signal_rows:
            sheet.append([
                row["timestamp"],
                row["value"],
                row["unit"],
            ])

        for column_cells in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            sheet.column_dimensions[column_cells[0].column_letter].width = max_length + 2

    if not workbook.sheetnames:
        sheet = workbook.create_sheet(title="Signals")
        sheet.append(["timestamp", "value", "unit"])
        for cell in sheet[1]:
            cell.font = header_font

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="{_build_export_filename().replace(".csv", ".xlsx")}"',
    }
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/api/live_source/connect")
async def connect_live_source(request: Request, payload: LiveSourceConnectRequest):
    config = request.app.state.config
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    config.pipeline.source = "zmq"
    config.live_source.flask_host = payload.flask_host
    config.live_source.flask_port = payload.flask_port
    config.live_source.zmq_host = payload.zmq_host
    config.live_source.zmq_port = payload.zmq_port
    config.live_source.connected = True

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()

    request.app.state.pipeline_manager = PipelineManager(config, dbc_manager)
    await request.app.state.pipeline_manager.start()
    await manager.broadcast_json(serialize_live_source_event(config))
    return {"status": "success", "message": "Live source connected successfully"}


@router.post("/api/live_source/stop")
async def stop_live_source(request: Request):
    config = request.app.state.config

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        request.app.state.pipeline_manager = None

    config.live_source.connected = False
    await manager.broadcast_json(serialize_live_source_event(config))
    return {"status": "success", "message": "Live source stopped successfully"}


@router.post("/api/live_source/disconnect")
async def disconnect_live_source(request: Request):
    config = request.app.state.config

    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        request.app.state.pipeline_manager = None

    config.live_source.connected = False
    config.live_source.flask_host = None
    config.live_source.flask_port = None
    config.live_source.zmq_host = None
    config.live_source.zmq_port = None
    await manager.broadcast_json(serialize_live_source_event(config))
    return {"status": "success", "message": "Live source disconnected successfully"}

@router.post("/api/stop")
async def stop_pipeline(request: Request):
    # Log-file indexing runs in its own worker thread and is not controlled by
    # PipelineManager. Signal it even when no pipeline manager is active.
    log_query_service.stop()
    if getattr(request.app.state, 'pipeline_manager', None):
        await request.app.state.pipeline_manager.stop()
        # Nullify the active pipeline manager
        request.app.state.pipeline_manager = None
        request.app.state.config.live_source.connected = False
        return {"status": "success", "message": "Pipeline stopped successfully"}
    return {"status": "success", "message": "Pipeline is already stopped"}

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if data.get("type") == "subscribe":
                    manager.subscribed_signals = set(data.get("signals", []))
                    manager.live_window_seconds = data.get("live_window_seconds", 15.0)
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
