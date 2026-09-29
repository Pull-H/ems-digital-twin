from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.core.paths import RUNTIME_DIR


REGISTRY_PATH = RUNTIME_DIR / "simulation_runs_index.json"
ACTIVE_PATH = RUNTIME_DIR / "active_simulation_run.json"
RUNS_DIR = RUNTIME_DIR / "runs"
MAX_INDEX_RUNS = 50


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent), suffix=".tmp") as tmp:
        json.dump(payload, tmp, ensure_ascii=True, indent=2, default=_json_default)
        tmp.write("\n")
        temp_name = tmp.name
    Path(temp_name).replace(path)


def _run_path(run_id: str) -> Path:
    safe_id = "".join(char for char in run_id if char.isalnum() or char in {"-", "_"})
    return RUNS_DIR / f"{safe_id}.json"


def _state_summary(state: dict[str, Any]) -> dict[str, Any]:
    metrics = state.get("metrics", {})
    simulation = state.get("simulation", {})
    return {
        "sim_minute": state.get("sim_minute"),
        "start_minute": state.get("start_minute"),
        "total_duration_min": state.get("total_duration_min"),
        "data_mode": state.get("data_mode", "demo"),
        "dataset_id": state.get("dataset_id"),
        "model_id": state.get("model_id"),
        "policy": state.get("policy"),
        "seed": state.get("seed"),
        "demand_source": simulation.get("demand_source"),
        "status": simulation.get("status"),
        "clock": simulation.get("clock"),
        "incidentes_totales": metrics.get("incidentes_totales"),
        "incidentes_atendidos": metrics.get("incidentes_atendidos"),
        "incidentes_pendientes": metrics.get("incidentes_pendientes"),
        "tiempo_promedio_respuesta": metrics.get("tiempo_promedio_respuesta"),
        "p90_respuesta": metrics.get("p90_respuesta"),
        "observed_response_mean": simulation.get("observed_response_mean"),
        "observed_response_count": simulation.get("observed_response_count"),
        "completed": simulation.get("completed"),
        "unfinished": simulation.get("unfinished"),
    }


def save_run(run_id: str, payload: dict[str, Any], state: dict[str, Any], event: str) -> None:
    saved_at = datetime.now(timezone.utc).isoformat()
    record = {
        "run_id": run_id,
        "payload": payload,
        "state": state,
        "summary": _state_summary(state),
        "last_event": event,
        "saved_at": saved_at,
        "schema_version": "1.0",
    }
    _atomic_write_json(_run_path(run_id), record)
    _atomic_write_json(ACTIVE_PATH, record)

    index = _read_json(REGISTRY_PATH, {"runs": []})
    runs = [item for item in index.get("runs", []) if item.get("run_id") != run_id]
    runs.insert(
        0,
        {
            "run_id": run_id,
            "saved_at": saved_at,
            "last_event": event,
            **record["summary"],
        },
    )
    _atomic_write_json(REGISTRY_PATH, {"runs": runs[:MAX_INDEX_RUNS], "updated_at": saved_at})


def load_active_run() -> dict[str, Any] | None:
    record = _read_json(ACTIVE_PATH, None)
    return record if isinstance(record, dict) and record.get("run_id") else None


def list_runs(limit: int = 20) -> list[dict[str, Any]]:
    index = _read_json(REGISTRY_PATH, {"runs": []})
    return list(index.get("runs", []))[: max(1, min(limit, MAX_INDEX_RUNS))]


def storage_summary() -> dict[str, Any]:
    active = load_active_run()
    runs = list_runs(5)
    return {
        "active_run_id": active.get("run_id") if active else None,
        "active_summary": active.get("summary") if active else None,
        "recent_runs": runs,
        "storage_path": str(RUNTIME_DIR),
    }
