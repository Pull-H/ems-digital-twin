from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.demo_data import generate_predictions
from app.services.historical_data_service import DEFAULT_DATASET_ID, DEFAULT_MODEL_ID, historical_predictions
from app.services.simulation_service import runtime

router = APIRouter(tags=["predictions"])


@router.post("/predictions/train")
def train_predictions(payload: dict[str, Any] | None = None):
    if runtime.engine is not None:
        raise HTTPException(status_code=409, detail="Los modelos NYC se entrenan mediante el pipeline de fase 5.")
    data = payload or {}
    scenario = data.get("scenario", runtime.state["scenario"])
    sim_minute = int(data.get("sim_minute", runtime.state["sim_minute"]))
    predictions = generate_predictions(sim_minute, scenario)
    return {
        "status": "success",
        "model": "Baseline historico FastAPI demo",
        "training_samples": 0,
        "mae": 0.0,
        "rmse": 0.0,
        "r2": 0.0,
        "predictions": predictions,
    }


@router.get("/predictions")
def get_predictions(
    horizon: int | None = None,
    dataset_id: str | None = None,
    model_id: str | None = None,
    sim_minute: int | None = None,
):
    if runtime.engine is not None and dataset_id is None and model_id is None and sim_minute is None:
        predictions = runtime.state['predictions']
        return [p for p in predictions if not horizon or p['horizonte_min'] == horizon]
    if dataset_id or runtime.state.get("data_mode") == "historical":
        predictions = historical_predictions(
            dataset_id or runtime.state.get("dataset_id") or DEFAULT_DATASET_ID,
            sim_minute if sim_minute is not None else int(runtime.state.get("sim_minute", 64800)),
            model_id or runtime.state.get("model_id") or DEFAULT_MODEL_ID,
        )
        if horizon:
            return [prediction for prediction in predictions if prediction["horizonte_min"] == horizon]
        return predictions

    predictions = generate_predictions(runtime.state["sim_minute"], runtime.state["scenario"])
    if horizon:
        return [prediction for prediction in predictions if prediction["horizonte_min"] == horizon]
    return predictions
