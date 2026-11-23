from fastapi import APIRouter
from .common import *

router = APIRouter()

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
        raise HTTPException(status_code=400, detail=str(error)) from error

    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

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

    return {"status": "success", "message": f"DBC {filename} selected"}

@router.delete("/api/dbc/{filename}")
async def delete_dbc_route(
    request: Request,
    filename: str
):
    dbc_manager = getattr(request.app.state, 'dbc_manager', None)
    if not dbc_manager:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")

    try:
        success = dbc_manager.delete_dbc(filename)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not success:
        raise HTTPException(status_code=404, detail=f"DBC {filename} not found")

    pipeline_manager = getattr(request.app.state, 'pipeline_manager', None)
    if pipeline_manager and pipeline_manager.source:
        pipeline_manager.source.db = dbc_manager.get_active_dbc()

    return {"status": "success", "message": f"DBC {filename} deleted"}

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
        request.app.state.config.pipeline.dbc_file = str(dbc_manager.dbc_dir / payload.new_name)

    return {
        "status": "success",
        "old_name": filename,
        "new_name": payload.new_name,
    }
