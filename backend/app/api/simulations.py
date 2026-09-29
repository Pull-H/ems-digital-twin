from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services import run_storage
from app.services.simulation_service import runtime

router = APIRouter(tags=["simulations"])


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_mode: Literal["demo", "historical"] = "demo"
    demand_source: Literal["historical", "forecast"] = "historical"
    dataset_id: str | None = None
    model_id: str | None = None
    start_minute: int = Field(default=64800, ge=0)
    duration_min: int = Field(default=720, ge=1, le=1440)
    num_ambulances: int = Field(default=691, ge=1, le=1500)
    seed: int = Field(default=12345, ge=0, le=2147483647)
    policy: Literal["tradicional", "predictivo"] = "tradicional"
    scenario: Literal["dia_normal", "evento_masivo", "tormenta", "brote_respiratorio"] = "dia_normal"
    weights: dict[str, float] = Field(default_factory=dict)


class StepRequest(BaseModel):
    delta_minutes: int = Field(default=5, ge=1, le=1440)


def check_run(run_id):
    if run_id != runtime.run_id:
        raise HTTPException(status_code=404, detail="Corrida no activa. Las corridas se conservan en memoria.")


@router.post("/simulations")
def create_simulation(payload: SimulationRequest):
    with runtime.lock:
        try:
            if payload.data_mode == "historical" and payload.scenario != "dia_normal":
                raise ValueError("Los multiplicadores de escenarios demo no se aplican a NYC.")
            return runtime.reset(payload.model_dump())
        except (ValueError, FileNotFoundError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/simulations")
def list_simulation_runs(limit: int = 20):
    return {
        "active_run_id": runtime.run_id,
        "runs": run_storage.list_runs(limit),
    }


@router.get("/simulations/current")
def get_current_simulation():
    if not runtime.run_id:
        raise HTTPException(status_code=404, detail="No hay corrida activa.")
    return {"run_id": runtime.run_id, "state": runtime.state}


@router.post("/simulations/restore/latest")
def restore_latest_simulation():
    with runtime.lock:
        try:
            return runtime.restore_latest()
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/simulations/step")
def step_simulation(payload: StepRequest):
    with runtime.lock:
        try:
            return runtime.step(payload.delta_minutes)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error


@router.patch("/simulations/config")
def update_simulation_config(payload: dict[str, Any] | None = None):
    data = payload or {}
    policy = data.get("policy")
    if policy and policy not in {"tradicional", "predictivo"}:
        raise HTTPException(status_code=400, detail="Politica de despacho no soportada.")
    with runtime.lock:
        try:
            return runtime.update_config(data)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/simulations/{run_id}/run")
def run_simulation(run_id: str):
    with runtime.lock:
        check_run(run_id)
        state = runtime.run_complete()
    return {
        "id": run_id,
        "status": "completada",
        "state": state,
        "metrics": state["metrics"],
    }


@router.get("/simulations/{run_id}")
def get_simulation(run_id: str):
    check_run(run_id)
    return runtime.state


@router.get("/simulations/{run_id}/events")
def get_simulation_events(run_id: str):
    check_run(run_id)
    return runtime.state["event_logs"]


@router.get("/simulations/{run_id}/metrics")
def get_simulation_metrics(run_id: str):
    check_run(run_id)
    return runtime.state["metrics"]
