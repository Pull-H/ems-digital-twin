from typing import Any

from fastapi import APIRouter, HTTPException, Response

from app.services.demo_data import ZONES
from app.services.simulation_service import runtime

router = APIRouter(tags=["data"])


@router.post("/incidents/generate")
def generate_incidents(payload: dict[str, Any] | None = None):
    data = payload or {}
    duration_min = int(data.get("duration_min", 1440))
    scenario = data.get("scenario", "dia_normal")
    seed = int(data.get("seed", 12345))
    sample = []
    for idx, zone in enumerate(ZONES[:5], start=1):
        sample.append(
            {
                "id": f"GEN-{idx:03d}",
                "fecha_hora": "2026-04-01T00:00:00.000Z",
                "sim_time_min": idx * 15,
                "latitud": zone["centroide"][0],
                "longitud": zone["centroide"][1],
                "zona_id": zone["id"],
                "quintil_socioeconomico": zone["quintil_socioeconomico"],
                "prioridad": "media",
                "tipo": "otro",
                "estado": "pendiente",
                "ambulancia_id": None,
                "hospital_id": None,
                "tiempo_llamada": idx * 15,
                "tiempo_despacho": None,
                "tiempo_llegada_escena": None,
                "tiempo_respuesta_min": None,
                "duracion_atencion_escena_min": 12,
                "requiere_traslado": True,
                "tiempo_llegada_hospital": None,
                "tiempo_liberacion": None,
            }
        )
    return {
        "total": len(sample),
        "scenario": scenario,
        "seed": seed,
        "duration_min": duration_min,
        "incidents": sample,
    }


@router.post("/data/import")
def import_data(payload: dict[str, Any] | None = None):
    csv_content = (payload or {}).get("csv_content")
    if not csv_content or not isinstance(csv_content, str):
        raise HTTPException(status_code=400, detail="Contenido CSV invalido.")
    lines = [line for line in csv_content.strip().splitlines() if line.strip()]
    if len(lines) < 2:
        raise HTTPException(status_code=400, detail="El archivo CSV debe tener encabezados y al menos una fila.")
    return {
        "status": "success",
        "imported_count": len(lines) - 1,
        "sample": [],
    }


@router.get("/data/export")
def export_data(type: str = "incidents"):
    if type == "metrics":
        metrics = runtime.state["metrics"]
        body = "metric,value\n" + "\n".join(
            [
                f"tiempo_promedio_respuesta,{metrics['tiempo_promedio_respuesta']}",
                f"mediana_respuesta,{metrics['mediana_respuesta']}",
                f"p90_respuesta,{metrics['p90_respuesta']}",
                f"porcentaje_menor_8min,{metrics['porcentaje_menor_8min']}",
            ]
        )
        return Response(content=body, media_type="text/csv")

    if type == "incidents":
        body = "incident_id,datetime,sim_time_min,latitude,longitude,zone_id,priority,incident_type,status,ambulance_id,response_time_min\n"
        return Response(content=body, media_type="text/csv")

    raise HTTPException(status_code=400, detail="Tipo de exportacion no soportado.")
