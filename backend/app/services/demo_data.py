from __future__ import annotations

from datetime import datetime, timezone
from math import sin
from typing import Any


ZONES: list[dict[str, Any]] = [
    {
        "id": 1,
        "nombre": "Distrito Esperanza Norte",
        "codigo": "Z-01",
        "centroide": [-8.068, -79.042],
        "poligono": [[-8.055, -79.055], [-8.055, -79.030], [-8.080, -79.030], [-8.080, -79.055]],
        "poblacion": 92400,
        "ingreso_promedio": 340,
        "quintil_socioeconomico": 1,
        "nivel_vulnerabilidad": 0.94,
        "demanda_historica_diaria": 18.5,
        "area_km2": 6.8,
    },
    {
        "id": 2,
        "nombre": "Alto Moche Sector Este",
        "codigo": "Z-02",
        "centroide": [-8.155, -78.995],
        "poligono": [[-8.140, -79.010], [-8.140, -78.980], [-8.170, -78.980], [-8.170, -79.010]],
        "poblacion": 78500,
        "ingreso_promedio": 365,
        "quintil_socioeconomico": 1,
        "nivel_vulnerabilidad": 0.91,
        "demanda_historica_diaria": 16.2,
        "area_km2": 7.2,
    },
    {
        "id": 3,
        "nombre": "Centro Civico Historico",
        "codigo": "Z-03",
        "centroide": [-8.111, -79.028],
        "poligono": [[-8.100, -79.040], [-8.100, -79.016], [-8.122, -79.016], [-8.122, -79.040]],
        "poblacion": 62000,
        "ingreso_promedio": 680,
        "quintil_socioeconomico": 3,
        "nivel_vulnerabilidad": 0.50,
        "demanda_historica_diaria": 23.8,
        "area_km2": 3.8,
    },
    {
        "id": 4,
        "nombre": "California Moderna",
        "codigo": "Z-04",
        "centroide": [-8.132, -79.044],
        "poligono": [[-8.120, -79.056], [-8.120, -79.032], [-8.145, -79.032], [-8.145, -79.056]],
        "poblacion": 43200,
        "ingreso_promedio": 1100,
        "quintil_socioeconomico": 4,
        "nivel_vulnerabilidad": 0.26,
        "demanda_historica_diaria": 9.2,
        "area_km2": 3.4,
    },
    {
        "id": 5,
        "nombre": "El Golf Country Club",
        "codigo": "Z-05",
        "centroide": [-8.144, -79.048],
        "poligono": [[-8.132, -79.060], [-8.132, -79.036], [-8.156, -79.036], [-8.156, -79.060]],
        "poblacion": 26500,
        "ingreso_promedio": 1850,
        "quintil_socioeconomico": 5,
        "nivel_vulnerabilidad": 0.12,
        "demanda_historica_diaria": 5.9,
        "area_km2": 4.8,
    },
]

BASES: list[dict[str, Any]] = [
    {
        "id": 1,
        "nombre": "Base Central SAMU",
        "codigo": "BASE-CENTRO",
        "latitud": -8.1085,
        "longitud": -79.0325,
        "capacidad": 4,
        "zona_id": 3,
        "descripcion": "Puesto de mando central y despacho principal.",
    },
    {
        "id": 2,
        "nombre": "Base Norte",
        "codigo": "BASE-NORTE",
        "latitud": -8.0695,
        "longitud": -79.0445,
        "capacidad": 4,
        "zona_id": 1,
        "descripcion": "Cobertura norte y periferica.",
    },
    {
        "id": 3,
        "nombre": "Base Sur",
        "codigo": "BASE-SUR",
        "latitud": -8.1395,
        "longitud": -79.041,
        "capacidad": 4,
        "zona_id": 4,
        "descripcion": "Cobertura sur y eje costero.",
    },
]

HOSPITALS: list[dict[str, Any]] = [
    {
        "id": 1,
        "nombre": "Hospital Regional",
        "codigo": "HOSP-REG",
        "latitud": -8.1065,
        "longitud": -79.036,
        "capacidad": 38,
        "ocupacion": 26,
        "nivel_trauma": 1,
        "tiempo_espera_min": 11,
        "zona_id": 3,
    },
    {
        "id": 2,
        "nombre": "Hospital Belen",
        "codigo": "HOSP-BEL",
        "latitud": -8.112,
        "longitud": -79.026,
        "capacidad": 30,
        "ocupacion": 20,
        "nivel_trauma": 2,
        "tiempo_espera_min": 14,
        "zona_id": 3,
    },
]


def build_ambulances(num_ambulances: int = 12) -> list[dict[str, Any]]:
    ambulances: list[dict[str, Any]] = []
    for idx in range(num_ambulances):
        base = BASES[idx % len(BASES)]
        ambulances.append(
            {
                "id": idx + 1,
                "codigo": f"AMB-{idx + 1:02d}",
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


def empty_metrics() -> dict[str, Any]:
    by_quintile = {}
    for q in range(1, 6):
        by_quintile[str(q)] = {
            "quintil": q,
            "nombre_quintil": f"Q{q}",
            "total_incidentes": 0,
            "tiempo_promedio_respuesta": 0,
            "mediana_respuesta": 0,
            "p90_respuesta": 0,
            "tiempo_maximo": 0,
            "porcentaje_menor_8min": 0,
            "vulnerabilidad_promedio": round(1 - q * 0.15, 2),
        }
    return {
        "tiempo_promedio_respuesta": 0,
        "mediana_respuesta": 0,
        "p90_respuesta": 0,
        "tiempo_maximo_respuesta": 0,
        "porcentaje_menor_8min": 0,
        "distancia_total_km": 0,
        "utilizacion_ambulancias": 0,
        "incidentes_totales": 0,
        "incidentes_atendidos": 0,
        "incidentes_pendientes": 0,
        "por_quintil": by_quintile,
        "diferencia_max_min_quintiles": 0,
        "razon_disparidad": 1,
    }


def generate_predictions(sim_minute: int, scenario: str = "dia_normal") -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    hour_factor = 1 + 0.25 * sin((sim_minute / 60) / 24)
    for zone in ZONES:
        for horizon in (15, 30, 60):
            base = zone["demanda_historica_diaria"] / 24 * (horizon / 60)
            multiplier = hour_factor
            if scenario == "tormenta":
                multiplier *= 1.35
            if scenario == "brote_respiratorio" and zone["quintil_socioeconomico"] <= 2:
                multiplier *= 1.8
            ml_value = round(base * multiplier * (1 + zone["nivel_vulnerabilidad"] * 0.15), 2)
            risk = "alto" if ml_value >= 0.45 else "medio" if ml_value >= 0.25 else "bajo"
            predictions.append(
                {
                    "zona_id": zone["id"],
                    "zona_nombre": zone["nombre"],
                    "horizonte_min": horizon,
                    "demanda_predicha_base": round(base, 2),
                    "demanda_predicha_ml": ml_value,
                    "nivel_riesgo": risk,
                    "probabilidad_incidente": min(round(ml_value / 1.2, 3), 0.95),
                    "factores_principales": [
                        "Demanda historica por zona",
                        "Vulnerabilidad territorial",
                    ],
                    "fecha_generacion": datetime.now(timezone.utc).isoformat(),
                }
            )
    return predictions
