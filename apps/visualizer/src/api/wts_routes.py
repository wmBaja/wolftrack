"""WolfTrack Signals API: catalog, definitions, and CRUD (docs/wts/api.md).

Registered from ``app.py`` alongside the main router. Errors use FastAPI's
``{"detail": ...}``; validation failures are
``detail: {"errors": [{signal, code, message}], "warnings": [...]}``.
"""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from dbc_manager import DbcConflictError, SignalDependentsError
from wts.errors import WtsValidationError
from wts.ops import describe_all
from wts.schema import VirtualSignalDef

wts_router = APIRouter()


class DefinitionPayload(BaseModel):
    definition: dict[str, Any]


def _manager(request: Request):
    dbc_manager = getattr(request.app.state, "dbc_manager", None)
    if dbc_manager is None:
        raise HTTPException(status_code=500, detail="DBC Manager not initialized")
    return dbc_manager


def _validation_detail(error: WtsValidationError) -> dict[str, Any]:
    return {
        "errors": [
            {
                "signal": item.get("signal", ""),
                "code": item.get("code", "invalid"),
                "message": item.get("message", ""),
            }
            for item in error.errors
        ],
        "warnings": [],
    }


@wts_router.get("/api/wts/operations")
async def get_operations():
    """Self-describing operation catalog (D15)."""
    return describe_all()


@wts_router.get("/api/wts/signals")
async def get_wts_signals(request: Request):
    """Definitions in the active setup, with broken flags and issues."""
    dbc_manager = _manager(request)
    wts = dbc_manager.active_wts
    if wts is None:
        return {"signals": [], "issues": [], "wts_version": dbc_manager.get_wts_version()}

    analysis = dbc_manager.active_analysis()
    hashes = dbc_manager.get_definition_hashes()
    broken = analysis.broken
    signals: list[dict[str, Any]] = []
    for definition in wts.signals:
        entry = definition.to_json()
        entry["broken"] = definition.name in broken
        entry["broken_reason"] = broken.get(definition.name)
        entry["def_hash"] = hashes.get(definition.name)
        signals.append(entry)
    for item in wts.raw_signals:
        if isinstance(item, dict):
            entry = dict(item)
            name = item.get("name") or ""
            entry["broken"] = True
            entry["broken_reason"] = broken.get(name, "invalid definition")
            entry["def_hash"] = None
            signals.append(entry)

    return {
        "signals": signals,
        # analysis.issues already includes the file's load warnings
        "issues": analysis.issues,
        "wts_version": dbc_manager.get_wts_version(),
    }


@wts_router.put("/api/wts/signals/{name}")
async def put_wts_signal(
    request: Request, name: str, payload: DefinitionPayload
):
    """Create or update one virtual signal (backend is the validator)."""
    dbc_manager = _manager(request)
    try:
        definition = VirtualSignalDef.from_json(payload.definition)
    except WtsValidationError as error:
        raise HTTPException(status_code=422, detail=_validation_detail(error))

    if definition.name != name:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": [{
                    "signal": name,
                    "code": "name_mismatch",
                    "message": f"path name '{name}' does not match definition "
                               f"name '{definition.name}'",
                }],
                "warnings": [],
            },
        )

    try:
        result = dbc_manager.upsert_virtual_signal(definition)
    except WtsValidationError as error:
        raise HTTPException(status_code=422, detail=_validation_detail(error))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return result


@wts_router.delete("/api/wts/signals/{name}")
async def delete_wts_signal(request: Request, name: str):
    """Delete a virtual signal; 409 with dependents when referenced."""
    dbc_manager = _manager(request)
    try:
        result = dbc_manager.delete_virtual_signal(name)
    except SignalDependentsError as error:
        raise HTTPException(
            status_code=409, detail={"dependents": error.dependents}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"WTS signal {name} not found")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return result
