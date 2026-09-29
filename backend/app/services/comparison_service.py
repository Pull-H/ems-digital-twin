from __future__ import annotations

import json
from datetime import datetime, timezone
from copy import deepcopy
from math import erf, sqrt
from pathlib import Path
from typing import Any

import numpy as np

from app.core.paths import REPORTS_DIR
from app.services.demo_data import empty_metrics
from app.services.ems_simulator import EMSSimulator
from app.services import historical_data_service as historical


def _metrics(mean_response: float, compliance: float, disparity: float) -> dict[str, Any]:
    metrics = empty_metrics()
    metrics.update(
        {
            "tiempo_promedio_respuesta": mean_response,
            "mediana_respuesta": round(mean_response - 0.7, 2),
            "p90_respuesta": round(mean_response + 4.1, 2),
            "tiempo_maximo_respuesta": round(mean_response + 8.4, 2),
            "porcentaje_menor_8min": compliance,
            "distancia_total_km": round(165 + mean_response * 8, 2),
            "utilizacion_ambulancias": 0.64,
            "incidentes_totales": 24,
            "incidentes_atendidos": 22,
            "incidentes_pendientes": 2,
            "razon_disparidad": disparity,
            "diferencia_max_min_quintiles": 3.2,
        }
    )
    for q in range(1, 6):
        metrics["por_quintil"][str(q)]["total_incidentes"] = 4 + q
        metrics["por_quintil"][str(q)]["tiempo_promedio_respuesta"] = round(mean_response + (3 - q) * 0.55, 2)
        metrics["por_quintil"][str(q)]["mediana_respuesta"] = round(mean_response + (3 - q) * 0.4, 2)
        metrics["por_quintil"][str(q)]["p90_respuesta"] = round(mean_response + 3 + (3 - q) * 0.5, 2)
        metrics["por_quintil"][str(q)]["porcentaje_menor_8min"] = max(0, min(100, compliance - (3 - q) * 2.2))
    return metrics


def _incidents(prefix: str, response_base: float) -> list[dict[str, Any]]:
    result = []
    for idx in range(24):
        response = round(response_base + (idx % 6) * 0.8, 2)
        result.append(
            {
                "id": f"{prefix}-{idx + 1:03d}",
                "fecha_hora": "2026-04-01T00:00:00.000Z",
                "sim_time_min": idx * 20,
                "latitud": -8.11,
                "longitud": -79.03,
                "zona_id": (idx % 5) + 1,
                "quintil_socioeconomico": (idx % 5) + 1,
                "prioridad": "media",
                "tipo": "otro",
                "estado": "completado",
                "ambulancia_id": (idx % 12) + 1,
                "hospital_id": None,
                "tiempo_llamada": idx * 20,
                "tiempo_despacho": idx * 20 + 1,
                "tiempo_llegada_escena": idx * 20 + response,
                "tiempo_respuesta_min": response,
                "duracion_atencion_escena_min": 12,
                "requiere_traslado": True,
                "tiempo_llegada_hospital": None,
                "tiempo_liberacion": None,
            }
        )
    return result


def run_demo_comparison(scenario: str, num_ambulances: int, seed: int, duration_min: int) -> dict[str, Any]:
    traditional_metrics = _metrics(9.4, 58.0, 1.32)
    predictive_metrics = _metrics(8.1, 66.5, 1.18)
    return {
        "scenario": scenario,
        "semilla": seed,
        "duracion_min": duration_min,
        "num_ambulancias": num_ambulances,
        "traditional_run": {
            "metrics": traditional_metrics,
            "incidents": _incidents("TRAD", 6.0),
        },
        "predictive_run": {
            "metrics": predictive_metrics,
            "incidents": _incidents("PRED", 5.2),
        },
        "statistical_tests": {
            "t_test": {
                "t_stat": -2.1,
                "p_value": 0.04,
                "significant_p05": True,
                "interpretacion": "Resultado demo; no usar como evidencia del articulo.",
            },
            "wilcoxon": {
                "w_stat": 42,
                "z_score": -1.9,
                "p_value": 0.06,
                "significant_p05": False,
                "interpretacion": "Resultado demo; sera reemplazado por experimentos reales.",
            },
            "bootstrap_ci": {
                "delta_tiempo_promedio": {"mean": 1.3, "ci_lower": 0.4, "ci_upper": 2.1},
                "delta_cumplimiento_8min": {"mean": 8.5, "ci_lower": 2.0, "ci_upper": 14.0},
                "delta_razon_disparidad": {"mean": 0.14, "ci_lower": 0.02, "ci_upper": 0.25},
            },
            "ml_evaluacion": {
                "mae": 0,
                "rmse": 0,
                "r2": 0,
                "mae_baseline": 0,
                "rmse_baseline": 0,
            },
        },
        "resumen_ejecutivo": {
            "reduccion_tiempo_promedio_min": round(
                traditional_metrics["tiempo_promedio_respuesta"] - predictive_metrics["tiempo_promedio_respuesta"],
                2,
            ),
            "aumento_cumplimiento_8min_pct": round(
                predictive_metrics["porcentaje_menor_8min"] - traditional_metrics["porcentaje_menor_8min"],
                1,
            ),
            "mejora_razon_disparidad": round(
                traditional_metrics["razon_disparidad"] - predictive_metrics["razon_disparidad"],
                3,
            ),
            "tiempo_promedio_q1_trad": deepcopy(traditional_metrics["por_quintil"]["1"]["tiempo_promedio_respuesta"]),
            "tiempo_promedio_q1_pred": deepcopy(predictive_metrics["por_quintil"]["1"]["tiempo_promedio_respuesta"]),
        },
    }


def _round(value: Any, digits: int = 3) -> float:
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return 0.0


def _normal_p_two_sided(z_value: float) -> float:
    return float(2 * (1 - (0.5 * (1 + erf(abs(z_value) / sqrt(2))))))


def _paired_t_test(deltas: list[float]) -> dict[str, Any]:
    n = len(deltas)
    if n < 2:
        return {
            "t_stat": 0,
            "p_value": 1,
            "significant_p05": False,
            "interpretacion": "Se requieren al menos dos replicas pareadas para estimar variabilidad.",
        }
    values = np.array(deltas, dtype=float)
    std = float(values.std(ddof=1))
    if std == 0:
        t_stat = 0.0 if float(values.mean()) == 0 else float("inf")
    else:
        t_stat = float(values.mean() / (std / sqrt(n)))
    p_value = 0.0 if t_stat == float("inf") else _normal_p_two_sided(t_stat)
    return {
        "t_stat": _round(t_stat),
        "p_value": _round(p_value, 5),
        "significant_p05": p_value < 0.05,
        "interpretacion": (
            "Prueba pareada sobre replicas; delta positivo favorece la politica predictiva en tiempo medio."
            if p_value < 0.05
            else "No hay evidencia suficiente en estas replicas para afirmar una diferencia estadistica."
        ),
    }


def _average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[position][1]:
            end += 1
        rank = (position + 1 + end + 1) / 2
        for idx in range(position, end + 1):
            ranks[indexed[idx][0]] = rank
        position = end + 1
    return ranks


def _wilcoxon_signed_rank(deltas: list[float]) -> dict[str, Any]:
    non_zero = [delta for delta in deltas if abs(delta) > 1e-12]
    n = len(non_zero)
    if n < 2:
        return {
            "w_stat": 0,
            "z_score": 0,
            "p_value": 1,
            "significant_p05": False,
            "interpretacion": "No hay suficientes diferencias no nulas para Wilcoxon.",
        }
    abs_values = [abs(delta) for delta in non_zero]
    ranks = _average_ranks(abs_values)
    w_plus = sum(rank for rank, delta in zip(ranks, non_zero) if delta > 0)
    expected = n * (n + 1) / 4
    variance = n * (n + 1) * (2 * n + 1) / 24
    z_score = 0.0 if variance == 0 else (w_plus - expected) / sqrt(variance)
    p_value = _normal_p_two_sided(z_score)
    return {
        "w_stat": _round(w_plus),
        "z_score": _round(z_score),
        "p_value": _round(p_value, 5),
        "significant_p05": p_value < 0.05,
        "interpretacion": (
            "Prueba no parametrica sobre replicas; delta positivo favorece la politica predictiva."
            if p_value < 0.05
            else "Wilcoxon no detecta una diferencia robusta con este presupuesto de replicas."
        ),
    }


def _bootstrap_ci(values: list[float], seed: int, samples: int = 2000) -> dict[str, float]:
    if not values:
        return {"mean": 0, "ci_lower": 0, "ci_upper": 0}
    rng = np.random.default_rng(seed)
    data = np.array(values, dtype=float)
    means = [float(rng.choice(data, size=len(data), replace=True).mean()) for _ in range(samples)]
    return {
        "mean": _round(float(data.mean())),
        "ci_lower": _round(float(np.quantile(means, 0.025))),
        "ci_upper": _round(float(np.quantile(means, 0.975))),
    }


def _run_policy(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    engine = EMSSimulator(payload)
    state = engine.step(int(payload["duration_min"]))
    incidents = []
    for incident in engine.incidents:
        incidents.append(
            {
                "id": incident["id"],
                "zona_id": incident["zona_id"],
                "tiempo_llamada": _round(incident.get("tiempo_llamada"), 4),
                "tiempo_respuesta_min": None
                if incident.get("tiempo_respuesta_min") is None
                else _round(incident["tiempo_respuesta_min"], 4),
                "estado": incident.get("estado"),
            }
        )
    return state, incidents


def _matched_response_pairs(traditional: list[dict[str, Any]], predictive: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trad_lookup = {
        item["id"]: item
        for item in traditional
        if item.get("tiempo_respuesta_min") is not None
    }
    pairs = []
    for pred in predictive:
        response_pred = pred.get("tiempo_respuesta_min")
        trad = trad_lookup.get(pred["id"])
        if trad is None or response_pred is None:
            continue
        response_trad = float(trad["tiempo_respuesta_min"])
        response_pred_f = float(response_pred)
        pairs.append(
            {
                "incident_id": pred["id"],
                "zone_id": pred["zona_id"],
                "traditional_response_min": _round(response_trad),
                "predictive_response_min": _round(response_pred_f),
                "delta_response_min": _round(response_trad - response_pred_f),
            }
        )
    return pairs


def _metric_delta(trad: dict[str, Any], pred: dict[str, Any], key: str) -> float:
    return _round(float(trad.get(key) or 0) - float(pred.get(key) or 0))


def _summarize_run(
    index: int,
    seed: int,
    traditional_state: dict[str, Any],
    predictive_state: dict[str, Any],
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    trad_metrics = traditional_state["metrics"]
    pred_metrics = predictive_state["metrics"]
    return {
        "replica": index,
        "seed": seed,
        "paired_incidents": len(pairs),
        "traditional": {
            "metrics": trad_metrics,
            "completed": traditional_state["simulation"].get("completed"),
            "unfinished": traditional_state["simulation"].get("unfinished"),
        },
        "predictive": {
            "metrics": pred_metrics,
            "completed": predictive_state["simulation"].get("completed"),
            "unfinished": predictive_state["simulation"].get("unfinished"),
        },
        "delta": {
            "mean_response_min": _metric_delta(trad_metrics, pred_metrics, "tiempo_promedio_respuesta"),
            "median_response_min": _metric_delta(trad_metrics, pred_metrics, "mediana_respuesta"),
            "p90_response_min": _metric_delta(trad_metrics, pred_metrics, "p90_respuesta"),
            "under_8min_pct": _round(
                float(pred_metrics.get("porcentaje_menor_8min") or 0)
                - float(trad_metrics.get("porcentaje_menor_8min") or 0)
            ),
            "completed": int(predictive_state["simulation"].get("completed") or 0)
            - int(traditional_state["simulation"].get("completed") or 0),
            "unfinished": int(traditional_state["simulation"].get("unfinished") or 0)
            - int(predictive_state["simulation"].get("unfinished") or 0),
        },
    }


def _average_metrics(replications: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    metrics = empty_metrics()
    source = [rep[policy]["metrics"] for rep in replications]
    for key in [
        "tiempo_promedio_respuesta",
        "mediana_respuesta",
        "p90_respuesta",
        "tiempo_maximo_respuesta",
        "porcentaje_menor_8min",
        "distancia_total_km",
        "utilizacion_ambulancias",
        "incidentes_totales",
        "incidentes_atendidos",
        "incidentes_pendientes",
    ]:
        metrics[key] = _round(float(np.mean([item.get(key) or 0 for item in source])), 3)
    metrics.update(por_quintil={}, razon_disparidad=None, diferencia_max_min_quintiles=None)
    return metrics


def _write_phase8_report(dataset_id: str, result: dict[str, Any]) -> dict[str, str]:
    report_dir = REPORTS_DIR / "nyc_ems" / dataset_id / "phase8"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "paired_experiment_results.json"
    md_path = report_dir / "NYC_EMS_PHASE8_EXPERIMENT_REPORT.md"
    json_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    summary = result["resumen_ejecutivo"]
    tests = result["statistical_tests"]
    md_path.write_text(
        "\n".join(
            [
                "# NYC EMS - Fase 8: experimentos pareados",
                "",
                f"Generado: {result['generated_at']}",
                f"Snapshot: `{result['dataset_id']}`",
                f"Modelo: `{result['model_id']}`",
                f"Replicas pareadas: {result['experiment']['repetitions']}",
                f"Ventana inicial: minuto {result['experiment']['start_minute']} por {result['duracion_min']} min",
                "",
                "## Resultado principal",
                "",
                f"- Delta medio de respuesta (tradicional - predictivo): {summary['reduccion_tiempo_promedio_min']} min.",
                f"- IC bootstrap 95%: [{tests['bootstrap_ci']['delta_tiempo_promedio']['ci_lower']}, {tests['bootstrap_ci']['delta_tiempo_promedio']['ci_upper']}] min.",
                f"- Delta P90: {summary['reduccion_p90_min']} min.",
                f"- Delta cumplimiento <8 min: {summary['aumento_cumplimiento_8min_pct']} puntos porcentuales.",
                "",
                "## Interpretacion",
                "",
                result["resumen_ejecutivo"]["interpretacion"],
                "",
                "## Limites",
                "",
                "- Resultados de simulacion, no de operacion real.",
                "- Recursos, bases, hospitales y liberacion son supuestos calibrados.",
                "- No se incluyen GPS reales ni camas observadas.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {"json": str(json_path), "markdown": str(md_path)}


def run_historical_paired_experiment(
    dataset_id: str | None = None,
    model_id: str | None = None,
    start_minute: int = 87840,
    duration_min: int = 720,
    num_ambulances: int = 691,
    seed: int = 12345,
    repetitions: int = 10,
    demand_source: str = "historical",
) -> dict[str, Any]:
    dataset = dataset_id or historical.DEFAULT_DATASET_ID
    model = model_id or historical.DEFAULT_MODEL_ID
    repetitions = max(1, min(int(repetitions), 50))
    duration_min = max(60, min(int(duration_min), 1440))
    base_payload = {
        "data_mode": "historical",
        "dataset_id": dataset,
        "model_id": model,
        "start_minute": int(start_minute),
        "duration_min": duration_min,
        "num_ambulances": int(num_ambulances),
        "demand_source": demand_source,
        "scenario": "dia_normal",
    }

    replications = []
    sampled_pairs: list[dict[str, Any]] = []
    for index in range(repetitions):
        run_seed = int(seed) + index
        traditional_state, traditional_incidents = _run_policy({**base_payload, "seed": run_seed, "policy": "tradicional"})
        predictive_state, predictive_incidents = _run_policy({**base_payload, "seed": run_seed, "policy": "predictivo"})
        pairs = _matched_response_pairs(traditional_incidents, predictive_incidents)
        if len(sampled_pairs) < 300:
            sampled_pairs.extend([{**pair, "replica": index + 1} for pair in pairs[: 300 - len(sampled_pairs)]])
        replications.append(_summarize_run(index + 1, run_seed, traditional_state, predictive_state, pairs))

    deltas_mean = [rep["delta"]["mean_response_min"] for rep in replications]
    deltas_under8 = [rep["delta"]["under_8min_pct"] for rep in replications]
    deltas_p90 = [rep["delta"]["p90_response_min"] for rep in replications]
    deltas_unfinished = [rep["delta"]["unfinished"] for rep in replications]

    traditional_metrics = _average_metrics(replications, "traditional")
    predictive_metrics = _average_metrics(replications, "predictive")
    bootstrap_mean = _bootstrap_ci(deltas_mean, seed)
    bootstrap_under8 = _bootstrap_ci(deltas_under8, seed + 17)
    bootstrap_unfinished = _bootstrap_ci(deltas_unfinished, seed + 29)
    t_test = _paired_t_test(deltas_mean)
    wilcoxon = _wilcoxon_signed_rank(deltas_mean)
    model_metrics = historical._read_json(historical._dataset_paths(dataset)["metrics"]).get("global", {}).get(model, {})
    validation = model_metrics.get("validation", {})
    test = model_metrics.get("test", {})

    result = {
        "scenario": "dia_normal",
        "dataset_id": dataset,
        "model_id": model,
        "semilla": int(seed),
        "duracion_min": duration_min,
        "num_ambulancias": int(num_ambulances),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "experiment": {
            "phase": "8",
            "design": "paired_replications",
            "repetitions": repetitions,
            "start_minute": int(start_minute),
            "demand_source": demand_source,
            "primary_outcome": "delta_mean_response_min_traditional_minus_predictive",
            "unit_of_inference": "replica",
            "positive_delta_interpretation": "favorece politica predictiva",
        },
        "traditional_run": {"metrics": traditional_metrics, "incidents": []},
        "predictive_run": {"metrics": predictive_metrics, "incidents": []},
        "replications": replications,
        "paired_incident_sample": sampled_pairs,
        "statistical_tests": {
            "t_test": t_test,
            "wilcoxon": wilcoxon,
            "bootstrap_ci": {
                "delta_tiempo_promedio": bootstrap_mean,
                "delta_cumplimiento_8min": bootstrap_under8,
                "delta_razon_disparidad": {"mean": 0, "ci_lower": 0, "ci_upper": 0},
            },
            "ml_evaluacion": {
                "mae": _round(test.get("mae")),
                "rmse": _round(test.get("rmse")),
                "r2": 0,
                "mae_baseline": _round(validation.get("mae")),
                "rmse_baseline": _round(validation.get("rmse")),
            },
        },
        "resumen_ejecutivo": {
            "reduccion_tiempo_promedio_min": bootstrap_mean["mean"],
            "reduccion_p90_min": _bootstrap_ci(deltas_p90, seed + 41)["mean"],
            "aumento_cumplimiento_8min_pct": bootstrap_under8["mean"],
            "reduccion_no_finalizados": bootstrap_unfinished["mean"],
            "mejora_razon_disparidad": 0,
            "tiempo_promedio_q1_trad": 0,
            "tiempo_promedio_q1_pred": 0,
            "interpretacion": (
                "La politica predictiva muestra menor tiempo medio en este presupuesto de replicas."
                if bootstrap_mean["mean"] > 0
                else "La politica predictiva no mejora el tiempo medio en este presupuesto de replicas."
            ),
        },
        "limitations": [
            "Comparacion simulada con datos historicos de demanda; no valida una operacion real.",
            "No hay GPS real de ambulancias ni capacidad hospitalaria observada.",
            "La inferencia depende de supuestos de flota, tiempos de servicio y periodo seleccionado.",
            "Los indicadores de equidad socioeconomica quedan fuera porque el dataset no contiene quintiles.",
        ],
    }
    result["artifacts"] = _write_phase8_report(dataset, result)
    return result
