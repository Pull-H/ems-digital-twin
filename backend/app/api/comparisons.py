from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.comparison_service import run_demo_comparison, run_historical_paired_experiment
from app.services.simulation_service import runtime

router = APIRouter(tags=["comparisons"])


class HistoricalComparisonRequest(BaseModel):
    dataset_id: str | None = None
    model_id: str | None = None
    start_minute: int = Field(default=87840, ge=0)
    duration_min: int = Field(default=720, ge=60, le=1440)
    num_ambulances: int = Field(default=691, ge=1, le=1500)
    seed: int = Field(default=12345, ge=0, le=2147483647)
    repetitions: int = Field(default=10, ge=1, le=50)
    demand_source: str = "historical"


@router.get("/comparisons")
def get_comparison(
    scenario: str = "dia_normal",
    ambulances: int = 12,
    seed: int = 12345,
    duration: int = 720,
    dataset_id: str | None = None,
    model_id: str | None = None,
    start_minute: int | None = None,
    repetitions: int = 10,
    demand_source: str = "historical",
):
    if dataset_id or runtime.state.get("data_mode") == "historical":
        try:
            return run_historical_paired_experiment(
                dataset_id=dataset_id or runtime.state.get("dataset_id"),
                model_id=model_id or runtime.state.get("model_id"),
                start_minute=start_minute if start_minute is not None else int(runtime.state.get("start_minute") or 87840),
                duration_min=duration,
                num_ambulances=ambulances,
                seed=seed,
                repetitions=repetitions,
                demand_source=demand_source,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    return run_demo_comparison(scenario, ambulances, seed, duration)


@router.post("/comparisons/historical")
def post_historical_comparison(payload: HistoricalComparisonRequest):
    if payload.demand_source not in {"historical", "forecast"}:
        raise HTTPException(status_code=422, detail="demand_source debe ser historical o forecast.")
    try:
        return run_historical_paired_experiment(**payload.model_dump())
    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
