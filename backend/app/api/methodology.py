from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.historical_data_service import DEFAULT_DATASET_ID
from app.services.methodology_service import crisp_dm_report

router = APIRouter(tags=["methodology"])


@router.get("/methodology/crisp-dm")
def get_crisp_dm_methodology(dataset_id: str = DEFAULT_DATASET_ID):
    try:
        return crisp_dm_report(dataset_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
