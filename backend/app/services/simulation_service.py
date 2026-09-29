from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.services.demo_data import BASES, HOSPITALS, ZONES, build_ambulances, empty_metrics, generate_predictions
from app.services.ems_simulator import EMSSimulator
from app.services import run_storage
from uuid import uuid4
from threading import RLock


DEFAULT_WEIGHTS = {
    "peso_tiempo": 0.45,
    "peso_demanda": 0.25,
    "peso_cobertura": 0.15,
    "peso_equidad": 0.15,
}


class SimulationRuntime:
    def __init__(self) -> None:
        self.lock = RLock()
        self.engine: EMSSimulator | None = None
        self.run_id: str | None = None
        self.historical_payload: dict[str, Any] | None = None
        self.state = self.create_state({})
        self._load_active_record()

    def _load_active_record(self) -> None:
        record = run_storage.load_active_run()
        if not record:
            return
        self.run_id = record.get("run_id")
        self.state = record.get("state") or self.state
        payload = record.get("payload") or {}
        self.historical_payload = dict(payload) if payload.get("data_mode") == "historical" else None
        self.engine = None

    def _ensure_recovered_engine(self) -> None:
        if self.engine is not None or self.state.get("data_mode") != "historical":
            return
        payload = self.historical_payload
        if payload is None:
            active = run_storage.load_active_run()
            payload = (active or {}).get("payload")
        if not payload:
            raise ValueError("No hay parametros persistidos para recuperar la corrida historica.")
        target_minute = float(self.state.get("sim_minute", payload.get("start_minute", 0)))
        self.engine = EMSSimulator(payload)
        self.historical_payload = dict(payload)
        delta = max(0, target_minute - self.engine.start)
        self.state = self.engine.step(delta)

    def create_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("data_mode") == "historical":
            engine = EMSSimulator(payload)
            state = engine.step(0)
            self.engine = engine
            self.historical_payload = dict(payload)
            return state

        self.engine = None
        self.historical_payload = None
        scenario = payload.get("scenario", "dia_normal")
        policy = payload.get("policy", "predictivo")
        seed = int(payload.get("seed", 12345))
        duration_min = int(payload.get("duration_min", 720))
        num_ambulances = int(payload.get("num_ambulances", 12))
        weights = {**DEFAULT_WEIGHTS, **payload.get("weights", {})}

        return {
            "sim_minute": 0,
            "is_running": False,
            "scenario": scenario,
            "policy": policy,
            "seed": seed,
            "speed_multiplier": 1,
            "total_duration_min": duration_min,
            "traffic_factor": 1.4 if scenario == "tormenta" else 1.0,
            "weather_factor": 1.5 if scenario == "tormenta" else 1.0,
            "zones": deepcopy(ZONES),
            "bases": deepcopy(BASES),
            "hospitals": deepcopy(HOSPITALS),
            "ambulances": build_ambulances(num_ambulances),
            "incidents": [],
            "predictions": generate_predictions(0, scenario),
            "relocation_recommendations": [],
            "event_logs": [],
            "metrics": empty_metrics(),
            "weights": weights,
        }

    def reset(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.state = self.create_state(payload)
        self.run_id = f"SIM-{uuid4().hex}"
        run_storage.save_run(self.run_id, dict(payload), self.state, "reset")
        return {
            "run_id": self.run_id,
            "message": "Simulacion inicializada con exito.",
            "state": self.state,
        }

    def step(self, delta_minutes: int = 5) -> dict[str, Any]:
        self._ensure_recovered_engine()
        if self.engine is not None:
            self.state = self.engine.step(delta_minutes)
            if self.run_id:
                run_storage.save_run(self.run_id, self.historical_payload or {}, self.state, "step")
            return self.state

        self.state["sim_minute"] = min(
            self.state["sim_minute"] + int(delta_minutes),
            self.state["total_duration_min"],
        )
        self.state["predictions"] = generate_predictions(self.state["sim_minute"], self.state["scenario"])
        if self.run_id:
            run_storage.save_run(self.run_id, self.historical_payload or {}, self.state, "step")
        return self.state

    def update_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._ensure_recovered_engine()
        if self.engine is not None:
            raise ValueError("Crea una nueva corrida para cambiar la politica o configuracion NYC.")
        policy = payload.get("policy")
        if policy:
            self.state["policy"] = policy
            if self.historical_payload is not None:
                self.historical_payload["policy"] = policy
        if payload.get("weights"):
            self.state["weights"] = {**self.state["weights"], **payload["weights"]}
            if self.historical_payload is not None:
                self.historical_payload["weights"] = self.state["weights"]
        if self.run_id:
            run_storage.save_run(self.run_id, self.historical_payload or {}, self.state, "config")
        return self.state

    def run_complete(self) -> dict[str, Any]:
        self._ensure_recovered_engine()
        if self.engine is not None:
            return self.step(self.state["total_duration_min"] - self.state["sim_minute"])
        self.state["sim_minute"] = self.state["total_duration_min"]
        if self.run_id:
            run_storage.save_run(self.run_id, self.historical_payload or {}, self.state, "run_complete")
        return self.state

    def restore_latest(self) -> dict[str, Any]:
        self._load_active_record()
        if not self.run_id:
            raise FileNotFoundError("No hay corridas persistidas para recuperar.")
        self._ensure_recovered_engine()
        return {"run_id": self.run_id, "state": self.state}


runtime = SimulationRuntime()
