from datetime import datetime, timezone

from fastapi import APIRouter

from app.services.simulation_service import runtime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "EMS Digital Twin API",
        "backend": "fastapi",
        "sim_minute": runtime.state["sim_minute"],
        "active_policy": runtime.state["policy"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
