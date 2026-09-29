"""Zone-level EMS experiment. All resources and movements are scenario assumptions."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from hashlib import sha256
from math import cos, hypot, radians, expm1, pi, sin
from typing import Any

import numpy as np
import pandas as pd
import simpy

from app.services import historical_data_service as data
from app.services.demo_data import empty_metrics


def distance(a, b):
    return hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * cos(radians((a[0] + b[0]) / 2)))


class EMSSimulator:
    def __init__(self, payload: dict[str, Any]):
        self.payload = dict(payload)
        self.dataset = payload.get("dataset_id") or data.DEFAULT_DATASET_ID
        self.model = payload.get("model_id") or data.DEFAULT_MODEL_ID
        self.source = payload.get("demand_source", "historical")
        self.start = int(payload.get("start_minute", 64800))
        self.end = self.start + int(payload.get("duration_min", 720))
        self.seed = int(payload.get("seed", 12345))
        self.policy = payload.get("policy", "tradicional")
        self.profile = data.dataset_profile(self.dataset)
        self.epoch = pd.Timestamp(self.profile["window"]["start_inclusive"])
        partitions = data._read_json(data._snapshot_dir(self.dataset) / "processed/temporal_partitions.json")
        train_end = pd.Timestamp(partitions["splits"]["train"]["end_exclusive"])
        if self.epoch + pd.Timedelta(minutes=self.start) < train_end:
            raise ValueError("El escenario debe comenzar despues del periodo de entrenamiento.")
        if self.epoch + pd.Timedelta(minutes=self.end) > pd.Timestamp(self.profile["window"]["end_exclusive"]):
            raise ValueError("El escenario excede la ventana del dataset.")
        scenario = data._scenario(self.dataset)
        self.zones = [data._zone_to_frontend(z) for z in scenario["zones"]]
        for zone in self.zones:
            for field in ('poblacion', 'ingreso_promedio', 'quintil_socioeconomico', 'nivel_vulnerabilidad', 'area_km2'):
                zone[field] = None
        self.by_zone = {z["id"]: z for z in self.zones}
        self.bases = [data._base_to_frontend(b, i) for i, b in enumerate(scenario["bases"], 1)]
        self.hospitals = [data._hospital_to_frontend(h, i) for i, h in enumerate(scenario["hospitals"], 1)]
        self.fleet = data._ambulances_from_bases(self.bases, int(payload.get("num_ambulances", 691)))
        self.env = simpy.Environment(initial_time=self.start)
        self.incidents: list[dict] = []
        self.waiting: list[dict] = []
        self.logs = deque(maxlen=120)
        self.motions: dict[int, tuple] = {}
        self.busy_intervals: list[tuple] = []
        self.busy_since: dict[int, float] = {}
        self.replay = data._replay(self.dataset)
        training_columns = ['zone_id', 'prioridad', 'tipo', 'requiere_traslado',
                            'observed_assignment_to_scene_min', 'observed_scene_to_departure_min',
                            'observed_transport_to_hospital_min', 'observed_call_to_close_min']
        training = self.replay.loc[self.replay.incident_datetime_parsed < train_end, training_columns]
        self.training = {z: group.reset_index(drop=True) for z, group in training.groupby("zone_id")}
        self.training_end = train_end.isoformat()
        forecasts = data._forecasts(self.dataset)
        self.forecasts = forecasts[forecasts.model_id == self.model].copy()
        self.baselines = forecasts[forecasts.model_id == 'baseline_temporal_v1']
        if self.forecasts.empty:
            raise ValueError("Modelo sin pronosticos disponibles.")
        self.prediction_cache: dict[int, list] = {}
        if self.source == "forecast" or self.policy == "predictivo":
            for minute in range(self.start // 60 * 60, self.end, 60):
                if len(self.predictions(minute)) != len(self.zones):
                    raise ValueError("Faltan pronosticos emitidos para una o mas horas del escenario.")
        if self.source == "historical":
            rows = self.replay[(self.replay.sim_time_min >= self.start) & (self.replay.sim_time_min < self.end)]
            self.excluded = int((~rows.zone_id.isin(self.by_zone)).sum())
            self.arrivals = rows[rows.zone_id.isin(self.by_zone)].sort_values(["sim_time_min", "incident_id"]).to_dict("records")
        else:
            self.excluded = 0
            self.arrivals = self.forecast_arrivals()
        self.env.process(self.arrival_process())

    def rng(self, key):
        digest = sha256(f"{self.seed}:{key}".encode()).digest()
        return np.random.default_rng(int.from_bytes(digest[:8], "big"))

    def synthetic_location(self, zone, hour, index):
        rng = self.rng(f"synthetic-location:{hour}:{zone['id']}:{index}")
        angle = float(rng.uniform(0, 2 * pi))
        radius_km = float(rng.uniform(0.25, 2.8))
        center_lat, center_lng = zone["centroide"]
        lat = center_lat + (radius_km / 111.2) * cos(angle)
        lng = center_lng + (radius_km / (111.2 * max(0.2, cos(radians(center_lat))))) * sin(angle)
        return lat, lng

    def predictions(self, minute):
        hour = int(minute // 60 * 60)
        if hour not in self.prediction_cache:
            timestamp = self.epoch + pd.Timedelta(minutes=hour)
            rows = self.forecasts[(self.forecasts.target_start == timestamp) & (self.forecasts.issued_at <= timestamp)]
            lookup = {z["codigo"]: z for z in self.zones}
            lookup["RICHMOND / STATEN ISLAND"] = self.zones[-1]
            result = []
            for row in rows.to_dict("records"):
                zone = lookup.get(str(row["zone_id"]))
                if zone:
                    value = max(0, float(row["prediction"]))
                    baseline = self.baselines[(self.baselines.target_start == timestamp) & (self.baselines.zone_id == row['zone_id'])]
                    result.append({"zona_id": zone["id"], "zona_nombre": zone["nombre"], "horizonte_min": 60,
                                   "demanda_predicha_ml": round(value, 2), "demanda_predicha_base": float(baseline.iloc[0]['prediction']) if not baseline.empty else value,
                                   "nivel_riesgo": data._risk(value), "probabilidad_incidente": -expm1(-value),
                                   "factores_principales": ["Pronostico retrospectivo horario"],
                                   "fecha_generacion": str(row["issued_at"]), "target_start": str(row["target_start"]),
                                   "target_end": str(row["target_end"])})
            self.prediction_cache[hour] = result
        return self.prediction_cache[hour]

    def forecast_arrivals(self):
        rows = []
        for hour in range(self.start // 60 * 60, self.end, 60):
            for prediction in self.predictions(hour):
                zone = self.by_zone[prediction["zona_id"]]
                rng = self.rng(f"arrivals:{hour}:{zone['id']}")
                count = int(rng.poisson(prediction["demanda_predicha_ml"]))
                for index, minute in enumerate(sorted(hour + rng.uniform(0, 60, count))):
                    if self.start <= minute < self.end:
                        sample = self.training[zone["id"]].iloc[int(rng.integers(len(self.training[zone["id"]])))]
                        lat, lng = self.synthetic_location(zone, hour, index)
                        rows.append({"incident_id": f"SYN-{hour}-{zone['id']}-{index}", "sim_time_min": float(minute),
                                     "incident_datetime_parsed": self.epoch + pd.Timedelta(minutes=minute),
                                     "zone_id": zone["id"], "latitud": lat, "longitud": lng,
                                     "prioridad": sample["prioridad"], "tipo": sample["tipo"], "quintile_proxy": 3})
        return sorted(rows, key=lambda r: (r["sim_time_min"], r["incident_id"]))

    def log(self, kind, incident, ambulance=None):
        self.logs.append({"id": f"{incident['id']}:{kind}", "sim_time_min": float(self.env.now),
                          "tipo_evento": kind, "descripcion": f"{kind.replace('_', ' ')}: {incident['id']}",
                          "incidente_id": incident["id"], "ambulancia_codigo": ambulance["codigo"] if ambulance else None})

    def arrival_process(self):
        for row in self.arrivals:
            yield self.env.timeout(max(0, float(row["sim_time_min"]) - self.env.now))
            incident = data._incident_to_frontend(row)
            incident.update(estado="pendiente", tiempo_despacho=None, tiempo_llegada_escena=None,
                            tiempo_respuesta_min=None, tiempo_llegada_hospital=None, tiempo_liberacion=None,
                            source=self.source, observed_response_min=data._safe_float(row.get("observed_response_min")) if row.get('response_cohort') else None)
            incident['quintil_socioeconomico'] = None
            rng = self.rng(f"service:{incident['id']}")
            samples = self.training[incident["zona_id"]]
            sample = samples.iloc[int(rng.integers(len(samples)))]
            def duration(key, fallback):
                return max(0.1, data._safe_float(sample.get(key), fallback) or fallback)
            travel = duration("observed_assignment_to_scene_min", 10)
            scene = duration("observed_scene_to_departure_min", 25)
            transport = duration("observed_transport_to_hospital_min", 12)
            # Closure is only a proxy for resource release. Never use the current case's outcome.
            release = max(10, duration("observed_call_to_close_min", 80) - travel - scene - transport)
            incident["service"] = (travel, scene, transport, release)
            incident["requiere_traslado"] = bool(sample.get("requiere_traslado", False))
            incident["duracion_atencion_escena_min"] = scene
            self.incidents.append(incident)
            self.log("incidente_creado", incident)
            self.env.process(self.ready(incident))

    def ready(self, incident):
        yield self.env.timeout(0.5)
        self.waiting.append(incident)
        self.dispatch()

    def dispatch(self):
        self.waiting.sort(key=lambda i: ({"alta": 0, "media": 1, "baja": 2}.get(i["prioridad"], 1), i["tiempo_llamada"], i["id"]))
        while self.waiting:
            available = [a for a in self.fleet if a["estado"] == "disponible"]
            if not available:
                break
            incident = self.waiting.pop(0)
            demand = {p["zona_id"]: p["demanda_predicha_ml"] for p in self.predictions(self.env.now)}
            counts = {z: sum(a["zona_actual_id"] == z for a in available) for z in self.by_zone}
            def score(a):
                travel = self.travel(a, incident)
                reserve = demand.get(a["zona_actual_id"], 0) / max(1, counts[a["zona_actual_id"]])
                return (travel + (2 * reserve if self.policy == "predictivo" else 0), a["id"])
            ambulance = min(available, key=score)
            ambulance.update(estado="asignada", incidente_asignado_id=incident["id"])
            self.busy_since[ambulance["id"]] = float(self.env.now)
            incident.update(estado="despachado", ambulancia_id=ambulance["id"], tiempo_despacho=float(self.env.now),
                            politica_usada=self.policy, explicacion_despacho="Tiempo estimado + reserva de demanda" if self.policy == "predictivo" else "Menor tiempo estimado")
            self.log("ambulancia_despachada", incident, ambulance)
            self.env.process(self.serve(ambulance, incident))

    def travel(self, ambulance, incident):
        origin = self.by_zone[ambulance["zona_actual_id"]]["centroide"]
        target = self.by_zone[incident["zona_id"]]["centroide"]
        return incident["service"][0] + distance(origin, target) / 38 * 60

    def move(self, ambulance, destination, duration, status):
        origin = (ambulance["latitud"], ambulance["longitud"])
        self.motions[ambulance["id"]] = (origin, destination, float(self.env.now), duration)
        ambulance.update(estado=status, target_lat=destination[0], target_lng=destination[1])
        yield self.env.timeout(duration)
        ambulance.update(latitud=destination[0], longitud=destination[1])
        ambulance["kilometraje_total"] += distance(origin, destination)
        ambulance.pop("target_lat", None)
        ambulance.pop("target_lng", None)
        self.motions.pop(ambulance["id"], None)

    def serve(self, ambulance, incident):
        _, scene, transport, handover = incident["service"]
        yield from self.move(ambulance, (incident["latitud"], incident["longitud"]), self.travel(ambulance, incident), "en ruta")
        ambulance.update(estado="en escena", zona_actual_id=incident["zona_id"])
        incident.update(estado="en_atencion", tiempo_llegada_escena=float(self.env.now),
                        tiempo_respuesta_min=float(self.env.now - incident["tiempo_llamada"]))
        self.log("llegada_escena", incident, ambulance)
        yield self.env.timeout(scene)
        if incident["requiere_traslado"]:
            hospital = next(h for h in self.hospitals if h["zona_id"] == incident["zona_id"])
            incident.update(estado="trasladando", hospital_id=hospital["id"])
            self.log("inicio_traslado", incident, ambulance)
            yield from self.move(ambulance, (hospital["latitud"], hospital["longitud"]), transport, "trasladando")
            incident["tiempo_llegada_hospital"] = float(self.env.now)
            ambulance["estado"] = "en hospital"
            self.log("llegada_hospital", incident, ambulance)
            yield self.env.timeout(handover)
        incident.update(estado="completado", tiempo_liberacion=float(self.env.now))
        ambulance.update(estado="disponible", incidente_asignado_id=None, disponible_desde_min=float(self.env.now))
        ambulance["incidentes_atendidos"] += 1
        self.busy_intervals.append((self.busy_since.pop(ambulance["id"]), float(self.env.now)))
        self.log("ambulancia_liberada", incident, ambulance)
        self.dispatch()

    def step(self, delta):
        target = min(self.end, self.env.now + delta)
        # Include events exactly on the requested boundary, consistently across chunk sizes.
        while self.env.peek() <= target:
            self.env.step()
        if self.env.now < target:
            self.env.run(until=target)
        return self.snapshot()

    def snapshot(self):
        now = float(self.env.now)
        responses = [i["tiempo_respuesta_min"] for i in self.incidents if i["tiempo_respuesta_min"] is not None]
        metrics = empty_metrics()
        metrics.update(por_quintil={}, razon_disparidad=None, diferencia_max_min_quintiles=None)
        metrics.update(incidentes_totales=len(self.incidents), incidentes_atendidos=len(responses),
                       incidentes_pendientes=sum(i["estado"] == "pendiente" for i in self.incidents))
        if responses:
            metrics.update(tiempo_promedio_respuesta=float(np.mean(responses)), mediana_respuesta=float(np.median(responses)),
                           p90_respuesta=float(np.quantile(responses, .9)), tiempo_maximo_respuesta=max(responses),
                           porcentaje_menor_8min=float(np.mean(np.array(responses) <= 8) * 100))
        busy = sum(b - a for a, b in self.busy_intervals) + sum(now - a for a in self.busy_since.values())
        metrics["utilizacion_ambulancias"] = busy / max(1, (now - self.start) * len(self.fleet))
        fleet = deepcopy(self.fleet)
        for ambulance in fleet:
            motion = self.motions.get(ambulance["id"])
            if motion:
                origin, target, start, duration = motion
                progress = min(1, max(0, (now - start) / duration))
                ambulance.update(latitud=origin[0] + (target[0] - origin[0]) * progress,
                                 longitud=origin[1] + (target[1] - origin[1]) * progress)
                ambulance["kilometraje_total"] += distance(origin, target) * progress
        metrics["distancia_total_km"] = sum(a["kilometraje_total"] for a in fleet)
        visible = sorted(self.incidents, key=lambda i: (i["estado"] == "completado", -i["tiempo_llamada"]))[:1000]
        observed = [i["observed_response_min"] for i in self.incidents if i["observed_response_min"] is not None
                    and i["tiempo_llamada"] + i["observed_response_min"] <= now]
        summaries = []
        for zone in self.zones:
            cases = [i for i in self.incidents if i["zona_id"] == zone["id"]]
            summaries.append({"zone_id": zone["id"], "arrived": len(cases),
                              "pending": sum(i["estado"] == "pendiente" for i in cases),
                              "active": sum(i["estado"] not in {"pendiente", "completado"} for i in cases),
                              "completed": sum(i["estado"] == "completado" for i in cases),
                              "available": sum(a["zona_actual_id"] == zone["id"] and a["estado"] == "disponible" for a in fleet)})
        return {"sim_minute": now, "start_minute": self.start, "total_duration_min": self.end,
                "is_running": False, "scenario": "dia_normal", "policy": self.policy, "seed": self.seed,
                "speed_multiplier": 1, "traffic_factor": 1, "weather_factor": 1,
                "zones": self.zones, "bases": self.bases, "hospitals": self.hospitals, "ambulances": fleet,
                "incidents": [{k: v for k, v in i.items() if k not in {"service", "observed_response_min"}} for i in visible],
                "predictions": self.predictions(min(now, self.end - .001)), "relocation_recommendations": [],
                "event_logs": list(self.logs), "metrics": metrics, "weights": self.payload.get("weights", {}),
                "data_mode": "historical", "dataset_id": self.dataset, "model_id": self.model,
                "simulation": {"engine": "simpy", "demand_source": self.source, "status": "finished" if now >= self.end else "ready",
                               "clock": (self.epoch + pd.Timedelta(minutes=now)).isoformat(), "timezone": "America/New_York",
                               "training_end": self.training_end, "visible_incidents": len(visible),
                               "excluded_unknown_zone": self.excluded, "zone_summary": summaries,
                               "observed_response_mean": float(np.mean(observed)) if observed else None,
                               "observed_response_count": len(observed),
                               "completed": sum(i["estado"] == "completado" for i in self.incidents),
                               "unfinished": sum(i["estado"] != "completado" for i in self.incidents),
                               "assumptions": ["Recursos y ubicaciones aproximados; sin GPS ni camas observadas.",
                                               "Tiempos muestreados del entrenamiento; cierre como proxy de liberacion.",
                                               "Inicio con flota libre; corte sin vaciado final. Evaluacion experimental pendiente.",
                                               "Pronosticos retrospectivos de una hora; no pronostico multihora abierto."]}}
