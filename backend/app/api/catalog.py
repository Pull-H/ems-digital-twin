from fastapi import APIRouter

from app.services.demo_data import BASES, ZONES
from app.services.simulation_service import runtime

router = APIRouter(tags=["catalog"])


@router.get("/zones")
def get_zones():
    return ZONES


@router.get("/bases")
def get_bases():
    return BASES


@router.get("/ambulances")
def get_ambulances():
    return runtime.state["ambulances"]


@router.get("/hospitals")
def get_hospitals():
    return runtime.state["hospitals"]


@router.get("/incidents")
def get_incidents():
    return runtime.state["incidents"]
