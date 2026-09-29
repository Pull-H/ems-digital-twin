from __future__ import annotations

from functools import lru_cache
from math import isnan
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.paths import DATA_DIR, PROJECT_ROOT, RESEARCH_DIR
from app.services.demo_data import empty_metrics


DATASET_ROOT = DATA_DIR / "nyc_ems"
DEFAULT_DATASET_ID = "20260909T040537085584Z-56d48fe7ce9b"
DEFAULT_MODEL_ID = "hist_gradient_boosting_v1"


def _read_json(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_dir(dataset_id: str) -> Path:
    if not dataset_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid dataset id")
    path = DATASET_ROOT / dataset_id
    if not path.is_dir():
        raise FileNotFoundError(f"Dataset {dataset_id} not found")
    return path


def _safe_float(value: Any, fallback: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return fallback
    return fallback if isnan(result) else result


def _safe_int(value: Any, fallback: int = 0) -> int:
    number = _safe_float(value)
    return fallback if number is None else int(number)


def _risk(value: float) -> str:
    if value >= 70:
        return "alto"
    if value >= 30:
        return "medio"
    return "bajo"


def _dataset_paths(dataset_id: str) -> dict[str, Path]:
    folder = _snapshot_dir(dataset_id)
    return {
        "folder": folder,
        "manifest": folder / "manifest.json",
        "cohort_summary": folder / "processed" / "cohort_summary.json",
        "geography_summary": folder / "processed" / "geography_summary.json",
        "phase6_manifest": folder / "simulation" / "phase6_manifest.json",
        "calibration": folder / "simulation" / "calibration_parameters.json",
        "scenario": folder / "simulation" / "nyc_scenario.json",
        "resources": folder / "simulation" / "resource_assumptions.json",
        "replay": folder / "simulation" / "historical_replay_inputs.parquet",
        "forecasts": folder / "processed" / "retrospective_forecasts.parquet",
        "metrics": RESEARCH_DIR / "artifacts" / "nyc_ems" / dataset_id / "phase5" / "reports" / "metrics.json",
    }


def list_datasets() -> list[dict[str, Any]]:
    if not DATASET_ROOT.exists():
        return []
    datasets: list[dict[str, Any]] = []
    for folder in sorted(DATASET_ROOT.iterdir()):
        if not folder.is_dir() or not (folder / "manifest.json").exists():
            continue
        manifest = _read_json(folder / "manifest.json")
        phase6 = folder / "simulation" / "phase6_manifest.json"
        datasets.append(
            {
                "id": folder.name,
                "study_id": manifest.get("study_id"),
                "mode": manifest.get("mode"),
                "status": manifest.get("status"),
                "window": manifest.get("window"),
                "expected_rows": manifest.get("expected_rows"),
                "historical_ready": phase6.exists(),
            }
        )
    return sorted(datasets, key=lambda item: (not item["historical_ready"], item["id"]))


def dataset_profile(dataset_id: str = DEFAULT_DATASET_ID) -> dict[str, Any]:
    paths = _dataset_paths(dataset_id)
    manifest = _read_json(paths["manifest"])
    phase6 = _read_json(paths["phase6_manifest"]) if paths["phase6_manifest"].exists() else {}
    calibration = _read_json(paths["calibration"]) if paths["calibration"].exists() else {}
    resources = _read_json(paths["resources"]) if paths["resources"].exists() else {}
    metrics = _read_json(paths["metrics"]) if paths["metrics"].exists() else {}
    return {
        "id": dataset_id,
        "study_id": manifest.get("study_id"),
        "status": manifest.get("status"),
        "window": manifest.get("window"),
        "expected_rows": manifest.get("expected_rows"),
        "historical_ready": bool(phase6),
        "phase6": phase6,
        "calibration_global": calibration.get("global", {}),
        "resource_assumptions": resources,
        "model_selection": metrics.get("selection", {}),
        "available_models": phase6.get("prediction_models_available", []),
    }


@lru_cache(maxsize=4)
def _scenario(dataset_id: str) -> dict[str, Any]:
    return _read_json(_dataset_paths(dataset_id)["scenario"])


@lru_cache(maxsize=4)
def _calibration(dataset_id: str) -> dict[str, Any]:
    return _read_json(_dataset_paths(dataset_id)["calibration"])


@lru_cache(maxsize=4)
def _replay(dataset_id: str) -> pd.DataFrame:
    return pd.read_parquet(_dataset_paths(dataset_id)["replay"])


@lru_cache(maxsize=4)
def _forecasts(dataset_id: str) -> pd.DataFrame:
    return pd.read_parquet(_dataset_paths(dataset_id)["forecasts"])


def _zone_to_frontend(zone: dict[str, Any]) -> dict[str, Any]:
    daily = _safe_float(zone.get("demanda_historica_diaria"), 0) or 0
    return {
        "id": int(zone["id"]),
        "nombre": zone["nombre"],
        "codigo": zone["codigo"],
        "centroide": zone["centroide"],
        "poligono": zone["poligono"],
        "poblacion": 0,
        "ingreso_promedio": 0,
        "quintil_socioeconomico": int(zone.get("quintil_socioeconomico_proxy", 3)),
        "nivel_vulnerabilidad": round(1 - int(zone.get("quintil_socioeconomico_proxy", 3)) * 0.15, 2),
        "demanda_historica_diaria": round(daily, 2),
        "area_km2": 0,
    }


def _base_to_frontend(base: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "id": int(base.get("id", idx)),
        "nombre": base.get("nombre", f"Base {idx}"),
        "codigo": base.get("codigo", f"BASE-{idx}"),
        "latitud": float(base["latitud"]),
        "longitud": float(base["longitud"]),
        "capacidad": 0,
        "zona_id": int(base["zona_id"]),
        "descripcion": "Proxy historico NYC; no observado en el dataset.",
    }


def _hospital_to_frontend(hospital: dict[str, Any], idx: int) -> dict[str, Any]:
    return {
        "id": int(hospital.get("id", idx)),
        "nombre": hospital.get("nombre", f"Hospital {idx}"),
        "codigo": hospital.get("codigo", f"HOSP-{idx}"),
        "latitud": float(hospital["latitud"]),
        "longitud": float(hospital["longitud"]),
        "capacidad": 0,
        "ocupacion": 0,
        "nivel_trauma": 2,
        "tiempo_espera_min": 0,
        "zona_id": int(hospital["zona_id"]),
    }


def _ambulances_from_bases(bases: list[dict[str, Any]], num_ambulances: int) -> list[dict[str, Any]]:
    ambulances = []
    for index in range(num_ambulances):
        base = bases[index % len(bases)]
        ambulances.append(
            {
                "id": index + 1,
                "codigo": f"NYC-AMB-{index + 1:03d}",
                "latitud": base["latitud"],
                "longitud": base["longitud"],
                "base_id": base["id"],
                "zona_actual_id": base["zona_id"],
                "estado": "disponible",
                "velocidad_kmh": 38,
                "incidente_asignado_id": None,
                "disponible_desde_min": 0,
                "kilometraje_total": 0,
                "incidentes_atendidos": 0,
            }
        )
    return ambulances


def _incident_to_frontend(row: dict[str, Any]) -> dict[str, Any]:
    response = _safe_float(row.get("observed_response_min"))
    sim_time = _safe_float(row.get("sim_time_min"), 0) or 0
    dispatch = _safe_float(row.get("observed_dispatch_min"))
    scene = None if response is None else sim_time + response
    return {
        "id": str(row["incident_id"]),
        "fecha_hora": str(row["incident_datetime_parsed"]),
        "sim_time_min": round(sim_time, 2),
        "latitud": float(row["latitud"]),
        "longitud": float(row["longitud"]),
        "zona_id": _safe_int(row.get("zone_id"), 99),
        "quintil_socioeconomico": _safe_int(row.get("quintile_proxy"), 3),
        "prioridad": row.get("prioridad") or "media",
        "tipo": row.get("tipo") or "otro",
        "estado": "completado" if response is not None else "pendiente",
        "ambulancia_id": None,
        "hospital_id": None,
        "tiempo_llamada": round(sim_time, 2),
        "tiempo_despacho": None if dispatch is None else round(sim_time + dispatch, 2),
        "tiempo_llegada_escena": None if scene is None else round(scene, 2),
        "tiempo_respuesta_min": None if response is None else round(response, 2),
        "duracion_atencion_escena_min": _safe_float(row.get("observed_scene_to_departure_min"), 0) or 0,
        "requiere_traslado": bool(row.get("requiere_traslado")),
        "tiempo_llegada_hospital": None,
        "tiempo_liberacion": None,
    }


def historical_predictions(dataset_id: str, sim_minute: int, model_id: str = DEFAULT_MODEL_ID) -> list[dict[str, Any]]:
    forecasts = _forecasts(dataset_id)
    scenario = _scenario(dataset_id)
    start = pd.Timestamp(dataset_profile(dataset_id)["window"]["start_inclusive"])
    target_hour = (start + pd.Timedelta(minutes=int(sim_minute))).floor("h")
    subset = forecasts[(forecasts["model_id"] == model_id) & (forecasts["target_start"] == target_hour)]
    if subset.empty:
        subset = forecasts[(forecasts["model_id"] == model_id)].head(0)
    zones = {zone["codigo"]: _zone_to_frontend(zone) for zone in scenario["zones"]}
    by_name = {zone["nombre"].upper(): _zone_to_frontend(zone) for zone in scenario["zones"]}
    predictions = []
    for _, row in subset.iterrows():
        zone_key = str(row["zone_id"])
        zone = zones.get(zone_key) or by_name.get(zone_key.upper())
        if zone is None and zone_key.upper().startswith("RICHMOND"):
            zone = zones.get("STATEN_ISLAND")
        if zone is None:
            continue
        prediction = float(row["prediction"])
        baseline_match = forecasts[
            (forecasts["model_id"] == "baseline_temporal_v1")
            & (forecasts["target_start"] == row["target_start"])
            & (forecasts["zone_id"] == row["zone_id"])
        ]
        baseline = prediction if baseline_match.empty else float(baseline_match.iloc[0]["prediction"])
        predictions.append(
            {
                "zona_id": zone["id"],
                "zona_nombre": zone["nombre"],
                "horizonte_min": 60,
                "demanda_predicha_base": round(baseline, 2),
                "demanda_predicha_ml": round(prediction, 2),
                "nivel_riesgo": _risk(prediction),
                "probabilidad_incidente": min(round(prediction / 100, 3), 0.95),
                "factores_principales": ["Rezagos historicos", "Hora/dia", "Borough"],
                "fecha_generacion": str(row["issued_at"]),
            }
        )
    return predictions


def _metrics_from_incidents(incidents: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = empty_metrics()
    responses = [incident["tiempo_respuesta_min"] for incident in incidents if incident.get("tiempo_respuesta_min") is not None]
    metrics["incidentes_totales"] = len(incidents)
    metrics["incidentes_atendidos"] = len(responses)
    metrics["incidentes_pendientes"] = len(incidents) - len(responses)
    if not responses:
        return metrics
    values = pd.Series(responses)
    metrics["tiempo_promedio_respuesta"] = round(float(values.mean()), 2)
    metrics["mediana_respuesta"] = round(float(values.median()), 2)
    metrics["p90_respuesta"] = round(float(values.quantile(0.90)), 2)
    metrics["tiempo_maximo_respuesta"] = round(float(values.max()), 2)
    metrics["porcentaje_menor_8min"] = round(float((values <= 8).mean() * 100), 2)
    for q in range(1, 6):
        subset = [i["tiempo_respuesta_min"] for i in incidents if i.get("quintil_socioeconomico") == q and i.get("tiempo_respuesta_min") is not None]
        if subset:
            q_values = pd.Series(subset)
            metrics["por_quintil"][str(q)]["total_incidentes"] = len(subset)
            metrics["por_quintil"][str(q)]["tiempo_promedio_respuesta"] = round(float(q_values.mean()), 2)
            metrics["por_quintil"][str(q)]["mediana_respuesta"] = round(float(q_values.median()), 2)
            metrics["por_quintil"][str(q)]["p90_respuesta"] = round(float(q_values.quantile(0.90)), 2)
            metrics["por_quintil"][str(q)]["porcentaje_menor_8min"] = round(float((q_values <= 8).mean() * 100), 2)
    return metrics


def build_historical_state(payload: dict[str, Any], sim_minute: int | None = None) -> dict[str, Any]:
    dataset_id = payload.get("dataset_id") or DEFAULT_DATASET_ID
    model_id = payload.get("model_id") or DEFAULT_MODEL_ID
    calibration = _calibration(dataset_id)
    scenario = _scenario(dataset_id)
    start_minute = int(payload.get("start_minute", 64800))
    current_minute = int(sim_minute if sim_minute is not None else start_minute)
    duration_min = int(payload.get("duration_min", 43200))
    window_start = max(0, current_minute - int(payload.get("visible_window_min", 180)))
    replay = _replay(dataset_id)
    visible = replay[(replay["sim_time_min"] >= window_start) & (replay["sim_time_min"] <= current_minute)].tail(300)
    zones = [_zone_to_frontend(zone) for zone in scenario["zones"]]
    bases = [_base_to_frontend(base, index) for index, base in enumerate(scenario["bases"], start=1)]
    hospitals = [_hospital_to_frontend(hospital, index) for index, hospital in enumerate(scenario["hospitals"], start=1)]
    fleet_size = int(payload.get("num_ambulances") or calibration["resource_estimates"]["ambulances_by_target_utilization"]["target_utilization_0.50"])
    incidents = [_incident_to_frontend(row) for row in visible.to_dict("records")]
    return {
        "sim_minute": current_minute,
        "is_running": False,
        "scenario": payload.get("scenario", "dia_normal"),
        "policy": payload.get("policy", "predictivo"),
        "seed": int(payload.get("seed", 12345)),
        "speed_multiplier": 1,
        "total_duration_min": start_minute + duration_min,
        "traffic_factor": 1.0,
        "weather_factor": 1.0,
        "zones": zones,
        "bases": bases,
        "hospitals": hospitals,
        "ambulances": _ambulances_from_bases(bases, fleet_size),
        "incidents": incidents,
        "predictions": historical_predictions(dataset_id, current_minute, model_id),
        "relocation_recommendations": [],
        "event_logs": [
            {
                "id": f"HIST-{current_minute}",
                "sim_time_min": current_minute,
                "tipo_evento": "incidente_creado",
                "descripcion": f"Modo historico NYC activo: {len(incidents)} incidentes visibles en la ventana reciente.",
            }
        ],
        "metrics": _metrics_from_incidents(incidents),
        "weights": payload.get("weights")
        or {"peso_tiempo": 0.45, "peso_demanda": 0.25, "peso_cobertura": 0.15, "peso_equidad": 0.15},
        "data_mode": "historical",
        "dataset_id": dataset_id,
        "model_id": model_id,
    }
