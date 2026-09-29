from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.assistant_service import run_assistant_query

router = APIRouter(tags=["assistant"])


@router.post("/assistant/query")
def query_assistant(payload: dict[str, Any] | None = None):
    data = payload or {}
    if not data.get("message") or not isinstance(data.get("message"), str):
        raise HTTPException(status_code=400, detail="Mensaje requerido para consultar el asistente.")
    return run_assistant_query(data)
