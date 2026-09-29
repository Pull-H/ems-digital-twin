from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.historical_data_service import DEFAULT_DATASET_ID
from app.services.model_performance_service import model_performance_report

router = APIRouter(tags=["model-performance"])


@router.get("/model-performance")
def get_model_performance(dataset_id: str = DEFAULT_DATASET_ID):
    try:
        return model_performance_report(dataset_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
