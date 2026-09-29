from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.historical_data_service import dataset_profile, list_datasets

router = APIRouter(tags=["datasets"])


@router.get("/datasets")
def get_datasets():
    return {"datasets": list_datasets()}


@router.get("/datasets/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str):
    try:
        return dataset_profile(dataset_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
