"""Reproducible paired fleet/supposition sensitivity, without starting the application."""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services import historical_data_service as data
from app.services.ems_simulator import EMSSimulator
from research.experiments.audit_phase8c import file_hash, fingerprint

DEFAULT_CONFIG = ROOT / "research/config/nyc_ems_phase8d_sensitivity_v1.json"


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def scenarios(config):
    if config["policies"] != ["tradicional", "predictivo"]:
        raise ValueError("Phase 8D compares only frozen traditional and predictive v1 policies.")
    for field in ("repetitions", "measured_duration_min"):
        if not isinstance(config[field], int) or config[field] <= 0:
            raise ValueError(f"{field} must be a positive integer")
    for field in ("warmup_min", "drain_cap_min"):
        if not isinstance(config[field], int) or config[field] < 0:
            raise ValueError(f"{field} must be a nonnegative integer")
    if not config["fleet_sizes"] or any(not isinstance(n, int) or n < 1 for n in config["fleet_sizes"]):
        raise ValueError("Fleet sizes must be positive integers")
    base = {"warmup_min": config["warmup_min"], "cross_zone_travel_multiplier": 1., "release_multiplier": 1.}
    rows = []
    for day in config["development_days"]:
        for fleet in config["fleet_sizes"]:
            rows.append({**base, "scenario_id": f"historical_{day}_{fleet}", "family": "fleet",
                         "day": day, "fleet": fleet, "demand_source": "historical", "variant": "base"})
    for variant in config["assumption_variants"]:
        changes = {k: v for k, v in variant.items() if k != "id"}
        if not changes or set(changes) - set(base):
            raise ValueError("Unknown or empty sensitivity override")
        if len(changes) != 1:
            raise ValueError("Assumption sensitivity changes one factor at a time")
        rows.append({**base, **changes, "scenario_id": f"assumption_{variant['id']}", "family": "assumption",
                     "day": config["assumption_day"], "fleet": config["assumption_fleet"],
                     "demand_source": "historical", "variant": variant["id"]})
    for day in config["forecast_days"]:
        for fleet in config["fleet_sizes"]:
            rows.append({**base, "scenario_id": f"forecast_{day}_{fleet}", "family": "forecast",
                         "day": day, "fleet": fleet, "demand_source": "forecast", "variant": "base"})
    if len({r["scenario_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate scenario identifiers")
    for row in rows:
        if not isinstance(row["warmup_min"], int) or row["warmup_min"] < 0:
            raise ValueError("Invalid warmup")
        if not all(np.isfinite(row[k]) and row[k] > 0 for k in ("cross_zone_travel_multiplier", "release_multiplier")):
            raise ValueError("Invalid sensitivity multiplier")
    return rows


def window_metrics(engine, start, end):
    cases = [i for i in engine.incidents if start <= i["tiempo_llamada"] < end]
    responses = [i["tiempo_respuesta_min"] for i in cases if i["tiempo_respuesta_min"] is not None]
    answered = len(responses)
    successful = sum(r <= 8 for r in responses)
    result = {
        "arrivals": len(cases), "responded": answered,
        "unanswered": len(cases) - answered,
        "pending_dispatch": sum(i["tiempo_despacho"] is None for i in cases),
        "completed": sum(i["estado"] == "completado" for i in cases),
        "unfinished": sum(i["estado"] != "completado" for i in cases),
        "mean_response_min": float(np.mean(responses)) if responses else None,
        "p90_response_min": float(np.quantile(responses, .9)) if responses else None,
        "response_le_8min_pct_responded": 100 * successful / answered if answered else None,
        "response_le_8min_pct_all_arrivals_lower_bound": 100 * successful / len(cases) if cases else None,
        "response_completeness_pct": 100 * answered / len(cases) if cases else None,
    }
    return result


def measured_utilization(engine, start, end):
    intervals = [*engine.busy_intervals, *((t, float(engine.env.now)) for t in engine.busy_since.values())]
    busy = sum(max(0., min(b, end) - max(a, start)) for a, b in intervals)
    return busy / ((end - start) * len(engine.fleet))


def run_pair(config, scenario, seed, pair_id):
    started = perf_counter()
    epoch = pd.Timestamp(data.dataset_profile(config["dataset_id"])["window"]["start_inclusive"])
    measure_start = int((pd.Timestamp(scenario["day"]) - epoch).total_seconds() / 60)
    measure_end = measure_start + config["measured_duration_min"]
    records, results, signatures = [], [], []
    for policy in config["policies"]:
        clock = perf_counter()
        payload = {"dataset_id": config["dataset_id"], "model_id": config["model_id"],
                   "start_minute": measure_start - scenario["warmup_min"],
                   "duration_min": config["measured_duration_min"] + scenario["warmup_min"],
                   "num_ambulances": scenario["fleet"], "policy": policy, "seed": seed,
                   "demand_source": scenario["demand_source"],
                   "cross_zone_travel_multiplier": scenario["cross_zone_travel_multiplier"],
                   "release_multiplier": scenario["release_multiplier"]}
        engine = EMSSimulator(payload)
        engine.step(payload["duration_min"])
        cut = window_metrics(engine, measure_start, measure_end)
        cut_records = {i["id"]: {"state_at_cut": i["estado"], "response_at_cut": i["tiempo_respuesta_min"]}
                       for i in engine.incidents}
        utilization = measured_utilization(engine, measure_start, measure_end)
        expected_total = len(engine.incidents)
        excluded_measure = 0
        if scenario["demand_source"] == "historical":
            subset = engine.replay[(engine.replay.sim_time_min >= measure_start) & (engine.replay.sim_time_min < measure_end)]
            excluded_measure = int((~subset.zone_id.isin(engine.by_zone)).sum())
        signature = fingerprint([{"id": i["id"], "zone": i["zona_id"], "arrival": i["tiempo_llamada"],
                                  "priority": i["prioridad"], "service": i["service"], "transport": i["requiere_traslado"]}
                                 for i in engine.incidents])
        signatures.append(signature)
        engine.drain(config["drain_cap_min"])
        final = window_metrics(engine, measure_start, measure_end)
        if len(engine.incidents) != expected_total or not 0 <= utilization <= 1 + 1e-10:
            raise AssertionError("Conservation/utilization failed")
        if final["arrivals"] != final["completed"] + final["unfinished"]:
            raise AssertionError("Incident reconciliation failed")
        if final["arrivals"] != cut["arrivals"] or final["responded"] < cut["responded"]:
            raise AssertionError("Drain changed cohort or lost responses")
        zone_results = []
        for zone in engine.zones:
            cases = [i for i in engine.incidents if measure_start <= i["tiempo_llamada"] < measure_end and i["zona_id"] == zone["id"]]
            responses = [i["tiempo_respuesta_min"] for i in cases if i["tiempo_respuesta_min"] is not None]
            zone_results.append({"zone_id": zone["id"], "zone_name": zone["nombre"], "arrivals": len(cases),
                                 "responded": len(responses), "unanswered": len(cases) - len(responses),
                                 "unanswered_at_cut": sum(cut_records[i["id"]]["response_at_cut"] is None for i in cases),
                                 "mean_response_min": float(np.mean(responses)) if responses else None,
                                 "p90_response_min": float(np.quantile(responses, .9)) if responses else None})
        for incident in engine.incidents:
            records.append({"pair_id": pair_id, "policy": policy, "incident_id": incident["id"],
                            "zone_id": incident["zona_id"], "arrival_min": incident["tiempo_llamada"],
                            "is_measurement": measure_start <= incident["tiempo_llamada"] < measure_end,
                            "ambulance_id": incident["ambulancia_id"], "dispatch_min": incident["tiempo_despacho"],
                            "response_min": incident["tiempo_respuesta_min"], "release_min": incident["tiempo_liberacion"],
                            "state_after_drain": incident["estado"], **cut_records[incident["id"]]})
        results.append({"policy": policy, "policy_version": "predictivo_v1" if policy == "predictivo" else "tradicional_v1",
                        "at_cut": cut, "after_drain": final, "by_zone": zone_results,
                        "measurement_utilization": utilization, "excluded_unknown_zone_measurement": excluded_measure,
                        "warmup_arrivals": expected_total - cut["arrivals"],
                        "drain_elapsed_min": float(engine.env.now - engine.end),
                        "drain_capped_with_unfinished": any(i["estado"] != "completado" for i in engine.incidents),
                        "exogenous_sha256": signature, "elapsed_seconds": perf_counter() - clock})
    if signatures[0] != signatures[1]:
        raise AssertionError("Policies did not receive identical arrivals/service draws")
    trad, pred = results
    a, b = trad["after_drain"], pred["after_drain"]
    delta = lambda key: a[key] - b[key] if a[key] is not None and b[key] is not None else None
    paired = {"mean_response_min_trad_minus_pred": delta("mean_response_min"),
              "p90_response_min_trad_minus_pred": delta("p90_response_min"),
              "unanswered_trad_minus_pred": delta("unanswered"),
              "complete_response_cohort_both": a["unanswered"] == b["unanswered"] == 0}
    return {"pair_id": pair_id, "scenario": scenario, "seed": seed, "runs": results,
            "paired": paired, "paired_exogenous_equal": True, "elapsed_seconds": perf_counter() - started}, records


def execute_and_store(config, scenario, seed, pair_id, directory):
    result, records = run_pair(config, scenario, seed, pair_id)
    directory = Path(directory)
    data_path = directory / f"{pair_id}.parquet"
    temporary = data_path.with_suffix(".parquet.tmp")
    pd.DataFrame(records).to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(data_path)
    result["incidents_file"] = data_path.name
    result["incidents_sha256"] = file_hash(data_path)
    result_path = directory / f"{pair_id}.json"
    atomic_json(result_path, result)
    return pair_id, file_hash(result_path)


def provenance(config, config_path):
    paths = data._dataset_paths(config["dataset_id"])
    files = [config_path.resolve(), config_path.parent / config["parent_protocol"], Path(__file__).resolve(),
             ROOT / "backend/app/services/ems_simulator.py", ROOT / "backend/app/services/historical_data_service.py",
             ROOT / "backend/app/services/demo_data.py", ROOT / "research/experiments/audit_phase8c.py",
             ROOT / "research/visualization/fleet_sensitivity.py",
             *(paths[k] for k in ("manifest", "replay", "forecasts", "scenario", "resources")),
             paths["folder"] / "processed/temporal_partitions.json"]
    return {"config": config, "input_sha256": {str(p.resolve().relative_to(ROOT)): file_hash(p) for p in files},
            "environment": {"python": platform.python_version(),
                            **{name: importlib.metadata.version(name) for name in ("numpy", "pandas", "simpy", "pyarrow", "matplotlib")}}}


def verify_completed(directory, pair_id, expected_hash):
    path = directory / f"{pair_id}.json"
    if not path.exists() or file_hash(path) != expected_hash:
        raise ValueError(f"Result missing or changed: {pair_id}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["pair_id"] != pair_id or result["incidents_file"] != f"{pair_id}.parquet":
        raise ValueError(f"Inconsistent artifact identity: {pair_id}")
    artifact = directory / result["incidents_file"]
    if not artifact.exists() or file_hash(artifact) != result["incidents_sha256"]:
        raise ValueError(f"Incident artifact missing or changed: {pair_id}")
    return result


def build_tables(output, manifest):
    rows, zones, paired = [], [], []
    for pair_id, checksum in manifest["completed"].items():
        result = verify_completed(output / "pairs", pair_id, checksum)
        base = {**result["scenario"], "pair_id": pair_id, "seed": result["seed"]}
        paired.append({**base, **result["paired"]})
        for run in result["runs"]:
            row = {**base, "policy": run["policy"], "policy_version": run["policy_version"],
                   "measurement_utilization": run["measurement_utilization"],
                   "elapsed_seconds": run["elapsed_seconds"], "drain_elapsed_min": run["drain_elapsed_min"],
                   "warmup_arrivals": run["warmup_arrivals"], "excluded_unknown_zone": run["excluded_unknown_zone_measurement"],
                   "drain_capped_with_unfinished": run["drain_capped_with_unfinished"]}
            for label in ("at_cut", "after_drain"):
                row.update({f"{label}_{k}": v for k, v in run[label].items()})
            rows.append(row)
            zones.extend({**base, "policy": run["policy"], **z} for z in run["by_zone"])
    folder = output / "tables"
    folder.mkdir(exist_ok=True)
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame = frame.sort_values(["scenario_id", "seed", "policy"])
    frame.to_csv(folder / "run_metrics.csv", index=False)
    pd.DataFrame(zones).sort_values(["scenario_id", "seed", "policy", "zone_id"]).to_csv(folder / "by_zone_metrics.csv", index=False)
    pd.DataFrame(paired).sort_values(["scenario_id", "seed"]).to_csv(folder / "paired_differences.csv", index=False)
    metrics = [c for c in frame if c.startswith(("at_cut_", "after_drain_"))] + ["measurement_utilization", "elapsed_seconds"]
    groups = ["scenario_id", "family", "day", "demand_source", "variant", "fleet", "warmup_min",
              "cross_zone_travel_multiplier", "release_multiplier", "policy"]
    summary = frame.groupby(groups, dropna=False)[metrics].mean().reset_index()
    counts = frame.groupby(groups, dropna=False).size().reset_index(name="replicates")
    summary = summary.merge(counts, on=groups, validate="one_to_one")
    summary.to_csv(folder / "scenario_summary.csv", index=False)
    fleet = summary[summary.family == "fleet"].groupby(["fleet", "policy"])[metrics].mean().reset_index()
    fleet.to_csv(folder / "historical_fleet_summary.csv", index=False)
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--limit-pairs", type=int, help="Intentional partial execution; resume without this option to finish")
    args = parser.parse_args()
    if args.limit_pairs is not None and args.limit_pairs < 1:
        parser.error("--limit-pairs must be positive")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    matrix = scenarios(config)
    identity = provenance(config, args.config)
    study_hash = fingerprint(identity)
    output = args.resume or ROOT / "reports/nyc_ems" / config["dataset_id"] / "phase8d" / study_hash[:20]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    pairs_dir = output / "pairs"
    pairs_dir.mkdir(exist_ok=True)
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["study_sha256"] != study_hash or manifest["provenance"] != identity:
            raise ValueError("Resume blocked: configuration, code, environment or input artifacts changed")
    else:
        manifest = {"study_sha256": study_hash, "provenance": identity,
                    "created_at": datetime.now(timezone.utc).isoformat(), "status": "running", "completed": {}}
        atomic_json(manifest_path, manifest)
        atomic_json(output / "config.json", config)
        pd.DataFrame(matrix).to_csv(output / "scenario_matrix.csv", index=False)
    jobs = [(s, config["first_seed"] + rep, f"{s['scenario_id']}_s{config['first_seed'] + rep}")
            for s in matrix for rep in range(config["repetitions"])]
    expected = {key for _, _, key in jobs}
    if set(manifest["completed"]) - expected:
        raise ValueError("Unexpected completed pair in manifest")
    for pair_id, checksum in manifest["completed"].items():
        verify_completed(pairs_dir, pair_id, checksum)
    pending = [job for job in jobs if job[2] not in manifest["completed"]]
    if args.limit_pairs is not None:
        pending = pending[:args.limit_pairs]
    manifest.update(status="running", planned_pairs=len(jobs))
    atomic_json(manifest_path, manifest)
    print(f"Batch: {output}\nPlanned pairs: {len(jobs)}; verified: {len(manifest['completed'])}; pending this session: {len(pending)}", flush=True)
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            remaining = iter(pending)
            active = {}
            def enqueue():
                job = next(remaining, None)
                if job is not None:
                    scenario, seed, pair_id = job
                    future = executor.submit(execute_and_store, config, scenario, seed, pair_id, str(pairs_dir))
                    active[future] = pair_id
            for _ in range(args.workers):
                enqueue()
            while active:
                done, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    active.pop(future)
                    pair_id, checksum = future.result()
                    manifest["completed"][pair_id] = checksum
                    atomic_json(manifest_path, manifest)
                    print(f"{len(manifest['completed'])}/{len(jobs)} {pair_id}", flush=True)
                    enqueue()
        manifest["status"] = "complete" if len(manifest["completed"]) == len(jobs) else "partial"
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_json(manifest_path, manifest)
        build_tables(output, manifest)
        if manifest["status"] == "complete":
            from research.visualization.fleet_sensitivity import render_report
            render_report(output)
    except BaseException as error:
        manifest.update(status="interrupted", error=f"{type(error).__name__}: {error}")
        atomic_json(manifest_path, manifest)
        raise
    print(json.dumps({"output": str(output), "status": manifest["status"], "completed_pairs": len(manifest["completed"])}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
