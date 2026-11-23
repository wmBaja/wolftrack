from fastapi import APIRouter
from .common import *

router = APIRouter()

@router.get("/api/logfile/status")
async def get_logfile_status():
    return log_query_service.get_status()

@router.post("/api/logfile/query")
async def query_logfile(payload: LogQueryRequest):
    data = log_query_service.query(payload.signals, payload.start_ts, payload.end_ts, payload.max_points)
    return {"data": data}
