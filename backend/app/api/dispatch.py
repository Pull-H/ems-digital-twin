from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.demo_data import generate_predictions
from app.services.simulation_service import runtime

router = APIRouter(tags=["dispatch"])


@router.post("/dispatch/evaluate")
def evaluate_dispatch(payload: dict[str, Any] | None = None):
    data = payload or {}
    incident = data.get("incident")
    if not incident:
        raise HTTPException(status_code=400, detail="Parametro incidente requerido.")

    available = [ambulance for ambulance in runtime.state["ambulances"] if ambulance["estado"] == "disponible"]
    selected = available[0] if available else runtime.state["ambulances"][0]
    return {
        "ambulancia": selected,
        "tiempo_estimado_min": 6.5,
        "demanda_futura_origen": 0.2,
        "perdida_cobertura": 0.1,
        "penalizacion_equidad": 0.0,
        "puntaje_total": 6.8,
        "explicacion": "Seleccion demo del backend FastAPI; se reemplazara por el motor historico calibrado.",
    }


@router.post("/relocation/recommend")
def recommend_relocation():
    predictions = generate_predictions(runtime.state["sim_minute"], runtime.state["scenario"])
    high_risk = [item for item in predictions if item["horizonte_min"] == 60 and item["nivel_riesgo"] in {"alto", "medio"}]
    recommendations = []
    if high_risk:
        target = high_risk[0]
        ambulance = runtime.state["ambulances"][0]
        recommendations.append(
            {
                "id": f"REC-{runtime.state['sim_minute']}",
                "ambulancia_id": ambulance["id"],
                "ambulancia_codigo": ambulance["codigo"],
                "zona_origen_id": ambulance["zona_actual_id"],
                "zona_origen_nombre": "Zona actual",
                "zona_destino_id": target["zona_id"],
                "zona_destino_nombre": target["zona_nombre"],
                "lat_destino": -8.111,
                "lng_destino": -79.028,
                "motivo": "Demanda prevista elevada en horizonte de 60 minutos.",
                "riesgo_demanda_destino": target["nivel_riesgo"],
                "prioridad": "media",
                "timestamp_sim_min": runtime.state["sim_minute"],
            }
        )

    return {
        "timestamp_min": runtime.state["sim_minute"],
        "recommendations_count": len(recommendations),
        "recommendations": recommendations,
    }
