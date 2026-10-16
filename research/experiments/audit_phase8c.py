"""Local, read-only data audit and paired diagnostic runs; no web server required."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import historical_data_service as data
from app.services.ems_simulator import EMSSimulator
from app.services.comparison_service import _paired_t_test, _wilcoxon_signed_rank

DEFAULT_PROTOCOL = ROOT / "research/config/nyc_ems_phase8c_protocol_v1.json"


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def temporal_audit(dataset_id):
    paths = data._dataset_paths(dataset_id)
    forecasts = data._forecasts(dataset_id)
    training_end = pd.to_datetime(forecasts.training_window_end, errors="coerce")
    checks = {
        "forecast_keys_unique": not forecasts.duplicated(["model_id", "target_start", "zone_id"]).any(),
        "training_finished_before_issue": bool((training_end <= forecasts.issued_at).all()),
        "issue_no_later_than_target_start": bool((forecasts.issued_at <= forecasts.target_start).all()),
        "one_hour_horizon": bool((forecasts.target_end == forecasts.target_start + pd.Timedelta(hours=1)).all()),
        "finite_nonnegative_forecasts": bool(np.isfinite(forecasts.prediction).all() and (forecasts.prediction >= 0).all()),
    }
    pivot = forecasts.pivot_table(index=["target_start", "zone_id"], columns="model_id",
                                 values=["actual", "prediction"], aggfunc="first")
    checks["model_pairs_complete"] = bool(pivot.notna().all().all())
    checks["models_share_actual_labels"] = bool((pivot["actual"].nunique(axis=1) == 1).all())
    panel = pd.read_parquet(paths["folder"] / "processed/hourly_demand_panel.parquet")
    panel = panel.sort_values(["zone_id", "hour_start"]).reset_index(drop=True)
    grouped = panel.groupby("zone_id")["demand_count"]
    checks["hourly_grid_contiguous"] = bool(
        panel.groupby("zone_id").hour_start.diff().dropna().eq(pd.Timedelta(hours=1)).all())
    features = [c for c in panel if c.startswith(("lag_", "rolling_"))]
    for name in features:
        if name.startswith("lag_"):
            expected = grouped.shift(int(name.split("_")[1][:-1]))
        else:
            _, operation, window = name.split("_")
            expected = grouped.transform(lambda s: s.shift(1).rolling(int(window[:-1]), min_periods=1).agg(operation))
        checks[f"past_only_{name}"] = bool(np.allclose(panel[name], expected, equal_nan=True))
    ready = pd.read_parquet(paths["folder"] / "processed/model_ready_hourly_demand_panel.parquet")
    merged = ready.merge(panel[["zone_id", "target_start", *features]], on=["zone_id", "target_start"],
                         how="left", validate="one_to_one", suffixes=("", "_reference"))
    checks["model_ready_features_match_audited_panel"] = all(
        np.allclose(merged[c], merged[c + "_reference"], equal_nan=True) for c in features)
    return {"forecast_rows": len(forecasts), "panel_rows": len(panel), "checks": checks,
            "scope": "Artifact/feature chronology verified; online data publication latency is not known."}


def incident_records(engine):
    return [{"id": i["id"], "zone": i["zona_id"], "arrival": i["tiempo_llamada"],
             "priority": i["prioridad"], "service": list(i["service"]),
             "transport_required": i["requiere_traslado"], "ambulance": i["ambulancia_id"],
             "dispatch": i["tiempo_despacho"], "scene": i["tiempo_llegada_escena"],
             "response": i["tiempo_respuesta_min"], "release": i["tiempo_liberacion"],
             "state": i["estado"]} for i in engine.incidents]


def invariants(engine, state):
    assigned = [a["incidente_asignado_id"] for a in engine.fleet if a["incidente_asignado_id"] is not None]
    by_id = {i["id"]: i for i in engine.incidents}
    dispatched = [i for i in engine.incidents if i["tiempo_despacho"] is not None]
    arrived = [i for i in engine.incidents if i["tiempo_respuesta_min"] is not None]
    travel_by_incident = {d["incident_id"]: next(c["travel_min"] for c in d["candidates_by_zone"]
                                               if c["zone_id"] == d["selected_zone_id"])
                          for d in engine.decision_audit}
    checks = {
        "fleet_conserved": len(engine.fleet) == int(engine.payload["num_ambulances"]),
        "fleet_ids_unique": len({a["id"] for a in engine.fleet}) == len(engine.fleet),
        "incident_ids_unique": len(by_id) == len(engine.incidents),
        "no_double_assignment": len(assigned) == len(set(assigned)),
        "assignments_consistent": all(by_id[a["incidente_asignado_id"]]["ambulancia_id"] == a["id"]
                                      for a in engine.fleet if a["incidente_asignado_id"] is not None),
        "completed_plus_unfinished_equals_arrivals": state["simulation"]["completed"] + state["simulation"]["unfinished"] == len(engine.incidents),
        "utilization_in_unit_interval": 0 <= state["metrics"]["utilizacion_ambulancias"] <= 1,
        "dispatch_after_ready": all(i["tiempo_despacho"] >= i["tiempo_llamada"] + .5 - 1e-8 for i in dispatched),
        "response_equals_wait_plus_travel": all(abs(i["tiempo_respuesta_min"] -
            (i["tiempo_despacho"] - i["tiempo_llamada"] + travel_by_incident[i["id"]])) < 1e-8 for i in arrived),
        "service_samples_positive_finite": all(all(np.isfinite(v) and v > 0 for v in i["service"]) for i in engine.incidents),
        "release_after_scene": all(i["tiempo_liberacion"] >= i["tiempo_llegada_escena"] for i in engine.incidents if i["tiempo_liberacion"] is not None),
    }
    return checks


def statistical_controls():
    deltas = [1., 2., 3., 4.]
    tied = [1., 1., 2., 2., -1., -2.]
    return {
        "scope": "Artificial numerical controls, not study results; reference uses installed scipy version.",
        "paired_t": {"deltas": deltas, "current": _paired_t_test(deltas),
                     "student_t_reference_p": float(stats.ttest_1samp(deltas, popmean=0).pvalue)},
        "wilcoxon_ties": {"deltas": tied, "current": _wilcoxon_signed_rank(tied),
                          "tie_corrected_asymptotic_reference_p": float(
                              stats.wilcoxon(tied, method="approx", correction=False).pvalue)},
        "degenerate_nonzero": {"current": {k: str(v) if isinstance(v, float) and not np.isfinite(v) else v
                                           for k, v in _paired_t_test([1., 1., 1.]).items()},
                               "issue": "Infinite t statistic is not valid JSON; final inference needs explicit non-estimable state."},
    }


def write_summary_markdown(path, report):
    lines = ["# Fase 8C: auditoria reproducible", "", f"Ejecucion UTC: {report['audit_id']}",
             f"Controles tecnicos: {report['check_count']}; aprobados: {report['checks_passed']}.", "",
             "Una semilla por escenario. Diagnostico, sin inferencia de superioridad.", "",
             "| Caso | Politica | Llegadas | Despachos | Respuestas | Media (min) | Utilizacion |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for name, case in report["cases"].items():
        for policy, values in case["policies"].items():
            lines.append(f"| {name} | {policy} | {values['arrivals']} | {values['dispatched']} | "
                         f"{values['responses']} | {values['mean_response_min']:.6f} | {values['utilization']:.6f} |")
    lines += ["", "## Diagnostico por caso", ""]
    for name, case in report["cases"].items():
        lines.append(f"- {name}: {case['different_ambulance_choices']} elecciones diferentes de "
                     f"{case['paired_dispatched']} despachos comunes; {case['different_responses']} respuestas diferentes de "
                     f"{case['paired_responses']} pares con respuesta. Solo tradicional: "
                     f"{case['response_only_traditional']}; solo predictivo: {case['response_only_predictive']}.")
    lines += ["", "## Bloqueos para inferencia final", "",
              *[f"- {item}" for item in report["blocking_findings_for_final_inference"]], "",
              "Detalles y controles numericos: audit_summary.json. Trazas completas comprimidas por caso/politica.",
              "Manifiesto de integridad: artifact_sha256.json. Protocolo ejecutado: protocol.json."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_case(payload, folder):
    summaries, records, traces = {}, {}, {}
    checks = {}
    for policy in ("tradicional", "predictivo"):
        engine = EMSSimulator({**payload, "policy": policy, "audit_decisions": True})
        state = engine.step(payload["duration_min"])
        checks.update({f"{policy}_{key}": value for key, value in invariants(engine, state).items()})
        records[policy] = incident_records(engine)
        traces[policy] = engine.decision_audit
        summaries[policy] = {
            "arrivals": len(engine.incidents), "dispatched": len(engine.decision_audit),
            "responses": state["metrics"]["incidentes_atendidos"],
            "completed": state["simulation"]["completed"], "unfinished": state["simulation"]["unfinished"],
            "pending": state["metrics"]["incidentes_pendientes"],
            "mean_response_min": state["metrics"]["tiempo_promedio_respuesta"],
            "utilization": state["metrics"]["utilizacion_ambulancias"],
            "same_state_choice_changes": sum(d["same_state_choice_changed"] for d in engine.decision_audit),
            "cross_zone_dispatches": sum(d["selected_zone_id"] != d["incident_zone_id"] for d in engine.decision_audit),
            "queue_delay_over_ready": sum(d["wait_since_call_min"] > .5 + 1e-8 for d in engine.decision_audit),
        }
        with gzip.open(folder / f"{policy}_decisions.jsonl.gz", "wt", encoding="utf-8") as handle:
            for row in engine.decision_audit:
                handle.write(json.dumps(row, allow_nan=False) + "\n")
        with gzip.open(folder / f"{policy}_incidents.jsonl.gz", "wt", encoding="utf-8") as handle:
            for row in records[policy]:
                handle.write(json.dumps(row, allow_nan=False) + "\n")
    exogenous = lambda items: [{k: row[k] for k in ("id", "zone", "arrival", "priority", "service", "transport_required")} for row in items]
    hashes = {p: fingerprint(exogenous(items)) for p, items in records.items()}
    checks["identical_arrivals_and_service_draws"] = len(set(hashes.values())) == 1
    trad = {r["id"]: r for r in records["tradicional"]}
    pred = {r["id"]: r for r in records["predictivo"]}
    shared = trad.keys() & pred.keys()
    both_dispatched = [key for key in shared if trad[key]["dispatch"] is not None and pred[key]["dispatch"] is not None]
    both_responses = [key for key in shared if trad[key]["response"] is not None and pred[key]["response"] is not None]
    # One repeated run also checks invariants at intermediate cutoffs and chunk invariance.
    repeated = EMSSimulator({**payload, "policy": "predictivo", "audit_decisions": True})
    intermediate_ok = True
    while repeated.env.now < repeated.end:
        repeated_state = repeated.step(min(60, repeated.end - repeated.env.now))
        intermediate_ok &= all(invariants(repeated, repeated_state).values())
    checks["intermediate_invariants"] = intermediate_ok
    checks["chunked_incidents_identical"] = incident_records(repeated) == records["predictivo"]
    checks["chunked_decisions_identical"] = repeated.decision_audit == traces["predictivo"]
    return {"configuration": payload, "policies": summaries, "checks": checks, "exogenous_sha256": hashes,
            "paired_dispatched": len(both_dispatched), "paired_responses": len(both_responses),
            "different_ambulance_choices": sum(trad[k]["ambulance"] != pred[k]["ambulance"] for k in both_dispatched),
            "different_responses": sum(abs(trad[k]["response"] - pred[k]["response"]) > 1e-8 for k in both_responses),
            "response_only_traditional": sum(trad[k]["response"] is not None and pred[k]["response"] is None for k in shared),
            "response_only_predictive": sum(pred[k]["response"] is not None and trad[k]["response"] is None for k in shared)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = ROOT / "reports/nyc_ems" / protocol["dataset_id"] / "phase8c" / stamp
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "protocol.json", protocol)
    report = {"audit_id": stamp, "protocol_id": protocol["protocol_id"],
              "scope": "Diagnostic runs, not a statistical evaluation or a claim of operational benefit.",
              "temporal_audit": temporal_audit(protocol["dataset_id"]), "cases": {},
              "statistical_controls": statistical_controls(),
              "environment": {"python": platform.python_version(),
                              **{name: importlib.metadata.version(name) for name in ("numpy", "pandas", "simpy", "scipy")}}}
    for case in protocol["audit_cases"]:
        print(f"Auditing {case['id']}...", flush=True)
        case_folder = output / case["id"]
        case_folder.mkdir()
        payload = {k: v for k, v in case.items() if k != "id"}
        payload.update(dataset_id=protocol["dataset_id"], model_id=protocol["model_id"])
        result = run_case(payload, case_folder)
        report["cases"][case["id"]] = result
        write_json(case_folder / "summary.json", result)
    all_checks = [*report["temporal_audit"]["checks"].values(),
                  *(v for case in report["cases"].values() for v in case["checks"].values())]
    report["checks_passed"] = all(all_checks)
    report["check_count"] = len(all_checks)
    report["formal_inference_ready"] = False
    report["blocking_findings_for_final_inference"] = [
        "Comparison t-test uses normal tails; Wilcoxon lacks tie correction; rounded deltas enter tests.",
        "Model statistics treat correlated zone-hour errors as IID; no multiple-testing correction.",
        "Response means at cutoff use different observed subsets when policies leave different unresolved cases.",
        "No warmup/drain implementation for final protocol; cold start and cutoff affect results.",
        "Comparison legacy fields report unavailable equity/R2 as zero and label selected-model validation as baseline.",
    ]
    paths = data._dataset_paths(protocol["dataset_id"])
    sources = [Path(__file__).resolve(), args.protocol.resolve(),
               ROOT / "backend/app/services/ems_simulator.py",
               ROOT / "backend/app/services/comparison_service.py",
               ROOT / "research/visualization/crisp_dm_methodology.py",
               ROOT / "research/pipeline/nyc_ems.py",
               *(paths[k] for k in ("replay", "forecasts", "resources", "scenario", "calibration", "metrics")),
               *(paths["folder"] / "processed" / name for name in
                 ("hourly_demand_panel.parquet", "model_ready_hourly_demand_panel.parquet", "temporal_partitions.json"))]
    report["input_sha256"] = {str(p.relative_to(ROOT)): file_hash(p) for p in sources}
    write_json(output / "audit_summary.json", report)
    write_summary_markdown(output / "AUDIT_SUMMARY.md", report)
    write_json(output / "artifact_sha256.json", {str(p.relative_to(output)): file_hash(p)
               for p in sorted(output.rglob("*")) if p.is_file()})
    print(json.dumps({"output": str(output), "checks_passed": report["checks_passed"],
                      "check_count": report["check_count"]}), flush=True)
    return 0 if report["checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
