import csv

import io

import os

import shutil

import json

from collections import defaultdict

from datetime import datetime, timezone

from typing import Optional

from zoneinfo import ZoneInfo

from pydantic import BaseModel

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, UploadFile, File, Form

from fastapi.responses import StreamingResponse

from openpyxl import Workbook

from openpyxl.styles import Font

from core.ws_manager import manager

from core.pipeline.manager import PipelineManager

from core.pipeline.source import LogFileDataSource

from core.pipeline.log_query import log_query_service

class LogQueryRequest(BaseModel):
    signals: list[str]
    start_ts: float
    end_ts: float
    max_points: int

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
    rows: list[dict[str, object]] = []

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
                rows.append({
                    "timestamp": formatted_timestamp,
                    "signal_name": signal_name,
                    "value": signal_value,
                    "unit": signal_units.get(signal_name, ""),
                })
    finally:
        await source.disconnect()

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
