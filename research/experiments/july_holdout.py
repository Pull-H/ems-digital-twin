"""Temporal NYC EMS holdout with frozen Q2 forecasts and simulator calibration."""

from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys

import joblib
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

from research.pipeline import nyc_ems as pipeline
from research.experiments import fleet_sensitivity as fleet


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "research/config/nyc_ems_july_holdout_v1.json"
BASE_CONFIG_PATH = ROOT / "research/config/nyc_ems_2026.json"
EXTRACTION_CONFIG_PATH = ROOT / "data/nyc_ems/july_holdout_config.json"
PACKAGE_ID = "july_holdout_v1"
PACKAGE_DIR = ROOT / "data/nyc_ems" / PACKAGE_ID
RESULT_DIR = ROOT / "reports/nyc_ems" / PACKAGE_ID / "evaluation"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_config() -> Path:
    protocol = read_json(PROTOCOL_PATH)
    config = deepcopy(read_json(BASE_CONFIG_PATH))
    start = protocol["extraction_window"]["start_inclusive"]
    end = protocol["extraction_window"]["end_exclusive"]
    config["study_id"] = protocol["protocol_id"]
    config["window"].update(
        selection_mode="frozen_july_temporal_holdout",
        start_inclusive=start,
        end_exclusive=end,
        pilot_start_inclusive=start,
        pilot_end_exclusive="2026-07-08T00:00:00",
        publication_reference={"status": "new_source_snapshot_required", "protocol": PROTOCOL_PATH.name},
    )
    config["forecast"].update(
        train={"start_inclusive": start, "end_exclusive": "2026-07-02T00:00:00"},
        validation={"start_inclusive": "2026-07-02T00:00:00", "end_exclusive": "2026-07-08T00:00:00"},
        test={"start_inclusive": "2026-07-08T00:00:00", "end_exclusive": end},
    )
    EXTRACTION_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    pipeline.save_json(EXTRACTION_CONFIG_PATH, config)
    pipeline.load_config(EXTRACTION_CONFIG_PATH)
    return EXTRACTION_CONFIG_PATH


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(july_snapshot_id: str) -> Path:
    protocol = read_json(PROTOCOL_PATH)
    q2_id = protocol["development_snapshot_id"]
    q2 = ROOT / "data/nyc_ems" / q2_id
    july = ROOT / "data/nyc_ems" / july_snapshot_id
    july_config = read_json(july / "config.json")
    july_manifest, _ = pipeline.load_snapshot(july, july_config, strict=False)
    if july_manifest["status"] != "complete" or july_manifest["window"] != protocol["extraction_window"]:
        raise ValueError("July extraction must be complete and match the frozen protocol")
    if PACKAGE_DIR.exists():
        raise FileExistsError(f"Evaluation package already exists: {PACKAGE_DIR}")
    q2_manifest = read_json(q2 / "manifest.json")
    if q2_manifest["status"] != "complete":
        raise ValueError("Q2 development snapshot is incomplete")
    q2_config = read_json(q2 / "config.json")
    model_root = ROOT / "research/artifacts/nyc_ems" / q2_id / "phase5"
    card_path = model_root / "reports/model_card.json"
    card = read_json(card_path)
    if card["training_window"]["end_exclusive"] != q2_config["forecast"]["train"]["end_exclusive"]:
        raise ValueError("Model card does not match Q2 training boundary")

    panel_path = july / "processed/model_ready_hourly_demand_panel.parquet"
    clean_path = july / "processed/incidents_clean.parquet"
    if not panel_path.exists() or not clean_path.exists():
        raise FileNotFoundError("Run July phase3 and phase4 before building the evaluation package")
    frame = pd.read_parquet(panel_path)
    frame = frame[frame["target_start"] >= pd.Timestamp("2026-07-08")].sort_values(
        ["zone_id", "target_start"]
    ).reset_index(drop=True)
    if frame.empty or frame["target_start"].min() != pd.Timestamp("2026-07-08"):
        raise ValueError("July features do not cover the first required forecast hour")
    zones = set(pd.read_parquet(q2 / "processed/hourly_demand_panel.parquet")["zone_id"].unique())
    if set(frame["zone_id"].unique()) != zones or frame.duplicated(["zone_id", "target_start"]).any():
        raise ValueError("July panel zone coverage or keys differ from Q2")
    features = card["input_features"]
    encoded = card["encoded_feature_columns"]
    matrix, _ = pipeline.model_matrix(frame, features, encoded)
    forecasts = []
    model_paths = {}
    for model_id in protocol["forecast_models"]:
        model_path = model_root / "models" / f"{model_id}.joblib"
        model_paths[model_id] = model_path
        artifact = joblib.load(model_path)
        if artifact["feature_columns"] != features:
            raise ValueError(f"Frozen feature columns changed for {model_id}")
        if model_id == "baseline_temporal_v1":
            values = pipeline.predict_temporal_baseline(artifact["model"], frame)
            family = "baseline_temporal"
        else:
            if artifact["trained_columns"] != encoded:
                raise ValueError(f"Frozen encoded columns changed for {model_id}")
            values = artifact["model"].predict(matrix)
            family = artifact["model"].__class__.__name__
        forecasts.append(pipeline.build_forecast_rows(model_id, family, frame, values, q2_config))
    july_forecasts = pd.concat(forecasts, ignore_index=True).sort_values(
        ["model_id", "target_start", "zone_id"]
    ).reset_index(drop=True)
    if july_forecasts["training_window_end"].nunique() != 1 or (
        july_forecasts["training_window_end"].iloc[0] != q2_config["forecast"]["train"]["end_exclusive"]
    ):
        raise ValueError("July forecasts must retain the Q2 training cutoff")
    q2_forecasts = pd.read_parquet(q2 / "processed/retrospective_forecasts.parquet")
    combined_forecasts = pd.concat([q2_forecasts, july_forecasts], ignore_index=True)
    if combined_forecasts.duplicated(["model_id", "target_start", "zone_id"]).any():
        raise ValueError("Duplicate forecast keys after combining periods")

    clean = pd.read_parquet(clean_path)
    components = pipeline.build_time_components(clean)
    july_replay = pipeline.build_historical_replay_inputs(clean, components, july_config)
    q2_epoch = pd.Timestamp(q2_config["window"]["start_inclusive"])
    july_replay["sim_time_min"] = (july_replay["incident_datetime_parsed"] - q2_epoch).dt.total_seconds() / 60
    q2_replay = pd.read_parquet(q2 / "simulation/historical_replay_inputs.parquet")
    combined_replay = pd.concat([q2_replay, july_replay], ignore_index=True).sort_values(
        ["sim_time_min", "incident_id"]
    ).reset_index(drop=True)
    if combined_replay["incident_id"].duplicated().any():
        raise ValueError("Duplicate incident IDs across Q2 and July")
    if july_replay["incident_datetime_parsed"].min() < pd.Timestamp("2026-07-01"):
        raise ValueError("July replay contains an earlier incident")

    (PACKAGE_DIR / "processed").mkdir(parents=True)
    (PACKAGE_DIR / "simulation").mkdir()
    pipeline.write_parquet(combined_replay, PACKAGE_DIR / "simulation/historical_replay_inputs.parquet")
    pipeline.write_parquet(combined_forecasts, PACKAGE_DIR / "processed/retrospective_forecasts.parquet")
    for source, destination in (
        (q2 / "processed/temporal_partitions.json", PACKAGE_DIR / "processed/temporal_partitions.json"),
        (q2 / "simulation/calibration_parameters.json", PACKAGE_DIR / "simulation/calibration_parameters.json"),
        (q2 / "simulation/nyc_scenario.json", PACKAGE_DIR / "simulation/nyc_scenario.json"),
        (q2 / "simulation/resource_assumptions.json", PACKAGE_DIR / "simulation/resource_assumptions.json"),
    ):
        shutil.copy2(source, destination)
    phase6 = read_json(q2 / "simulation/phase6_manifest.json")
    phase6.update(snapshot_id=PACKAGE_ID, source_snapshots=[q2_id, july_snapshot_id],
                  historical_arrivals=len(combined_replay),
                  prediction_models_available=protocol["forecast_models"])
    pipeline.save_json(PACKAGE_DIR / "simulation/phase6_manifest.json", phase6)
    manifest = {
        "kind": "derived_temporal_evaluation_package_not_source_snapshot",
        "snapshot_id": PACKAGE_ID,
        "study_id": protocol["protocol_id"],
        "status": "complete",
        "window": {"start_inclusive": q2_config["window"]["start_inclusive"],
                   "end_exclusive": july_config["window"]["end_exclusive"]},
        "source_snapshots": [q2_id, july_snapshot_id],
        "expected_rows": q2_manifest["expected_rows"] + july_manifest["expected_rows"],
        "holdout_forecast_rows": len(july_forecasts),
        "holdout_replay_rows": len(july_replay),
        "protocol_sha256": file_hash(PROTOCOL_PATH),
        "input_sha256": {
            str(path.relative_to(ROOT)): file_hash(path)
            for path in [q2 / "manifest.json", july / "manifest.json", panel_path, clean_path,
                         q2 / "simulation/historical_replay_inputs.parquet", card_path, *model_paths.values()]
        },
    }
    pipeline.save_json(PACKAGE_DIR / "manifest.json", manifest)
    metrics = report_forecasts()
    print(json.dumps({"package": str(PACKAGE_DIR), "holdout_forecast_rows": len(july_forecasts),
                      "holdout_replay_rows": len(july_replay), "july_model_metrics": metrics}, indent=2))
    return PACKAGE_DIR


def report_forecasts() -> dict:
    protocol = read_json(PROTOCOL_PATH)
    manifest = read_json(PACKAGE_DIR / "manifest.json")
    frame = pd.read_parquet(PACKAGE_DIR / "processed/retrospective_forecasts.parquet")
    study = protocol["evaluation_window"]
    frame = frame[(frame["target_start"] >= pd.Timestamp(study["start_inclusive"]))
                  & (frame["target_start"] < pd.Timestamp(study["end_exclusive"]))]
    expected = study["days"] * 24 * 5
    metrics = {model_id: pipeline.regression_metrics(group) for model_id, group in
               frame.groupby("model_id", observed=True)}
    if set(metrics) != set(protocol["forecast_models"]) or any(m["rows"] != expected for m in metrics.values()):
        raise ValueError("July forecast holdout window is incomplete")
    report = ROOT / "reports/nyc_ems" / PACKAGE_ID / "forecast"
    report.mkdir(parents=True, exist_ok=True)
    pipeline.save_json(report / "july_model_metrics.json", {
        "source_snapshot_id": manifest["source_snapshots"][1],
        "training_snapshot_id": manifest["source_snapshots"][0],
        "evaluation_window": study,
        "metrics": metrics,
    })
    return metrics


def jobs_for_protocol(protocol: dict) -> list[tuple[dict, int, str]]:
    study = protocol["evaluation_window"]
    comparison = protocol["policy_comparison"]
    start = datetime.fromisoformat(study["start_inclusive"])
    end = datetime.fromisoformat(study["end_exclusive"])
    if (end - start).days != study["days"] or (end - start).seconds:
        raise ValueError("The protocol's calendar-day count is inconsistent")
    jobs = []
    for offset in range(study["days"]):
        day = (start + timedelta(days=offset)).date().isoformat()
        scenario = {
            "scenario_id": f"july_{day}_fleet_{comparison['primary_fleet_assumption']}",
            "family": "holdout", "day": day, "fleet": comparison["primary_fleet_assumption"],
            "demand_source": "historical", "variant": "base",
            "warmup_min": study["warmup_minutes_per_day"],
            "cross_zone_travel_multiplier": 1.0, "release_multiplier": 1.0,
        }
        for replicate in range(comparison["paired_replicates_per_day"]):
            seed = comparison["first_seed"] + replicate
            jobs.append((scenario, seed, f"july_{day}_s{seed}"))
    return jobs


def evaluation_config(protocol: dict) -> dict:
    study = protocol["evaluation_window"]
    comparison = protocol["policy_comparison"]
    return {
        "dataset_id": PACKAGE_ID,
        "model_id": comparison["selected_model_id"],
        "policies": comparison["policies"],
        "measured_duration_min": study["measurement_minutes_per_day"],
        "drain_cap_min": study["drain_cap_minutes"],
    }


def evaluation_provenance(protocol: dict) -> dict:
    manifest = read_json(PACKAGE_DIR / "manifest.json")
    paths = [PROTOCOL_PATH, Path(__file__), ROOT / "research/experiments/fleet_sensitivity.py",
             ROOT / "backend/app/services/ems_simulator.py",
             ROOT / "backend/app/services/historical_data_service.py",
             PACKAGE_DIR / "manifest.json", PACKAGE_DIR / "simulation/historical_replay_inputs.parquet",
             PACKAGE_DIR / "processed/retrospective_forecasts.parquet",
             PACKAGE_DIR / "simulation/calibration_parameters.json", PACKAGE_DIR / "simulation/nyc_scenario.json",
             PACKAGE_DIR / "simulation/resource_assumptions.json"]
    if manifest["protocol_sha256"] != file_hash(PROTOCOL_PATH):
        raise ValueError("Protocol changed since evaluation package was built")
    return {
        "protocol": protocol, "package_manifest_sha256": file_hash(PACKAGE_DIR / "manifest.json"),
        "input_sha256": {str(path.relative_to(ROOT)): file_hash(path) for path in paths},
        "environment": {"python": platform.python_version(), **{
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "scipy", "statsmodels", "simpy", "pyarrow", "scikit-learn")
        }},
    }


def run_evaluation(workers: int, limit_pairs: int | None) -> Path:
    protocol = read_json(PROTOCOL_PATH)
    if not PACKAGE_DIR.exists():
        raise FileNotFoundError("Build the frozen evaluation package first")
    if workers < 1 or workers > 4 or (limit_pairs is not None and limit_pairs < 1):
        raise ValueError("workers must be 1-4; limit-pairs must be positive")
    provenance = evaluation_provenance(protocol)
    study_hash = hashlib.sha256(json.dumps(provenance, sort_keys=True).encode()).hexdigest()
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pairs_dir = RESULT_DIR / "pairs"
    pairs_dir.mkdir(exist_ok=True)
    manifest_path = RESULT_DIR / "manifest.json"
    jobs = jobs_for_protocol(protocol)
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest["study_sha256"] != study_hash or manifest["provenance"] != provenance:
            raise ValueError("Resume blocked: code, environment, protocol or inputs changed")
    else:
        manifest = {"study_sha256": study_hash, "provenance": provenance,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "running", "planned_pairs": len(jobs), "completed": {}}
        fleet.atomic_json(manifest_path, manifest)
    expected = {pair_id for _, _, pair_id in jobs}
    if set(manifest["completed"]) - expected:
        raise ValueError("Manifest contains unexpected pairs")
    for pair_id, checksum in manifest["completed"].items():
        fleet.verify_completed(pairs_dir, pair_id, checksum)
    pending = [(scenario, seed, pair_id) for scenario, seed, pair_id in jobs
               if pair_id not in manifest["completed"]]
    if limit_pairs is not None:
        pending = pending[:limit_pairs]
    print(f"July holdout: {len(manifest['completed'])}/{len(jobs)} verified; {len(pending)} pending", flush=True)
    config = evaluation_config(protocol)
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            remaining = iter(pending)
            active = {}
            def enqueue():
                job = next(remaining, None)
                if job is not None:
                    scenario, seed, pair_id = job
                    future = executor.submit(fleet.execute_and_store, config, scenario, seed, pair_id, str(pairs_dir))
                    active[future] = pair_id
            for _ in range(workers):
                enqueue()
            while active:
                completed, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in completed:
                    active.pop(future)
                    pair_id, checksum = future.result()
                    manifest["completed"][pair_id] = checksum
                    fleet.atomic_json(manifest_path, manifest)
                    print(f"{len(manifest['completed'])}/{len(jobs)} {pair_id}", flush=True)
                    enqueue()
        manifest["status"] = "complete" if len(manifest["completed"]) == len(jobs) else "partial"
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        fleet.atomic_json(manifest_path, manifest)
        fleet.build_tables(RESULT_DIR, manifest)
    except BaseException as error:
        manifest.update(status="interrupted", error=f"{type(error).__name__}: {error}")
        fleet.atomic_json(manifest_path, manifest)
        raise
    print(f"Evaluation status: {manifest['status']}", flush=True)
    return RESULT_DIR


def moving_block_interval(values: np.ndarray, block_length: int, draws: int, seed: int) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) < block_length or not np.isfinite(values).all() or draws < 1:
        raise ValueError("Invalid block-bootstrap input")
    rng = np.random.default_rng(seed)
    block_count = int(np.ceil(len(values) / block_length))
    starts = rng.integers(0, len(values), size=(draws, block_count))
    offsets = np.arange(block_length)
    indexes = (starts[:, :, None] + offsets) % len(values)
    draws_mean = values[indexes.reshape(draws, -1)[:, :len(values)]].mean(axis=1)
    return tuple(float(v) for v in np.quantile(draws_mean, [.025, .975]))


def hac_mean(values: np.ndarray, maxlags: int = 3) -> dict:
    values = np.asarray(values, dtype=float)
    if not np.isfinite(values).all() or len(values) <= maxlags + 1:
        raise ValueError("Insufficient valid daily observations for HAC")
    if np.all(values == values[0]):
        return {"mean": float(values[0]), "ci95": [float(values[0])] * 2,
                "p_value": 1.0 if values[0] == 0 else 0.0,
                "degenerate": True}
    fitted = sm.OLS(values, np.ones((len(values), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    return {"mean": float(fitted.params[0]), "ci95": [float(v) for v in fitted.conf_int()[0]],
            "p_value": float(fitted.pvalues[0]), "degenerate": False}


def analyze_evaluation() -> Path:
    protocol = read_json(PROTOCOL_PATH)
    manifest = read_json(RESULT_DIR / "manifest.json")
    jobs = jobs_for_protocol(protocol)
    if manifest["status"] != "complete" or len(manifest["completed"]) != len(jobs):
        raise ValueError("Complete all prespecified pairs before analysis")
    for pair_id, checksum in manifest["completed"].items():
        fleet.verify_completed(RESULT_DIR / "pairs", pair_id, checksum)
    run = pd.read_csv(RESULT_DIR / "tables/run_metrics.csv")
    expected_rows = 2 * len(jobs)
    if len(run) != expected_rows or run.duplicated(["day", "seed", "policy"]).any():
        raise ValueError("Run table has missing or duplicate paired policy rows")
    metric_names = ["after_drain_mean_response_min", "at_cut_unanswered", "after_drain_unanswered",
                    "after_drain_response_le_8min_pct_all_arrivals_lower_bound", "measurement_utilization"]
    wide = run.pivot(index=["day", "seed"], columns="policy", values=metric_names)
    if len(wide) != len(jobs):
        raise ValueError("Paired metric table is incomplete")
    daily = pd.DataFrame(index=sorted(run["day"].unique()))
    for metric in metric_names:
        trad = wide[(metric, "tradicional")]
        pred = wide[(metric, "predictivo")]
        daily[f"trad_{metric}"] = trad.groupby(level="day").mean()
        daily[f"pred_{metric}"] = pred.groupby(level="day").mean()
        daily[f"delta_{metric}"] = (trad - pred).groupby(level="day").mean()
    if len(daily) != protocol["evaluation_window"]["days"] or daily.isna().any().any():
        raise ValueError("Daily outcomes incomplete or missing")
    daily.index.name = "day"
    daily.to_csv(RESULT_DIR / "tables/daily_policy_comparison.csv")
    primary = daily["delta_after_drain_mean_response_min"].to_numpy()
    uncertainty = protocol["uncertainty"]
    primary_result = {
        "outcome": "traditional_minus_predictive_mean_response_minutes",
        "estimate_day_weighted": float(primary.mean()),
        "moving_block_bootstrap_ci95_7day": moving_block_interval(primary, 7, 10000, 20261023),
        "moving_block_bootstrap_ci95_3day": moving_block_interval(primary, 3, 10000, 20261023),
        "hac_lag3_secondary": hac_mean(primary),
        "daily_values": {str(day): float(value) for day, value in zip(daily.index, primary)},
    }
    secondary_names = ["at_cut_unanswered", "after_drain_unanswered",
                       "after_drain_response_le_8min_pct_all_arrivals_lower_bound", "measurement_utilization"]
    secondary = {name: hac_mean(daily[f"delta_{name}"].to_numpy()) for name in secondary_names}
    corrected = multipletests([secondary[name]["p_value"] for name in secondary_names], method="holm")[1]
    for name, adjusted in zip(secondary_names, corrected):
        secondary[name]["holm_adjusted_p"] = float(adjusted)
    # Administrative response times provide only an external descriptive check; they are not simulator ground truth.
    july_id = read_json(PACKAGE_DIR / "manifest.json")["source_snapshots"][1]
    source = pd.read_parquet(ROOT / "data/nyc_ems" / july_id / "processed/response_cohort.parquet")
    source = source[
        (source["incident_datetime_parsed"] >= pd.Timestamp(protocol["evaluation_window"]["start_inclusive"]))
        & (source["incident_datetime_parsed"] < pd.Timestamp(protocol["evaluation_window"]["end_exclusive"]))
    ].copy()
    source["day"] = source["incident_datetime_parsed"].dt.date.astype(str)
    source["observed_response_min"] = source["incident_response_seconds_qy_num"] / 60
    observed = source.groupby("day")["observed_response_min"].agg(
        observed_count="size", observed_mean_min="mean", observed_p90_min=lambda x: x.quantile(.9))
    traditional = run[run["policy"] == "tradicional"].groupby("day").agg(
        simulated_mean_min=("after_drain_mean_response_min", "mean"),
        simulated_p90_min=("after_drain_p90_response_min", "mean"),
        simulated_arrivals=("after_drain_arrivals", "mean"),
        simulated_response_completeness_pct=("after_drain_response_completeness_pct", "mean"))
    observed_check = observed.join(traditional, how="outer", validate="one_to_one")
    if len(observed_check) != len(daily) or observed_check.isna().any().any():
        raise ValueError("Observed/simulated day comparison is incomplete")
    observed_check.to_csv(RESULT_DIR / "tables/observed_descriptive_check.csv")
    result = {
        "scope": "independent July temporal holdout; simulation-only policy effect; not field validation",
        "protocol_sha256": file_hash(PROTOCOL_PATH), "manifest_sha256": file_hash(RESULT_DIR / "manifest.json"),
        "paired_runs": len(jobs), "calendar_days": len(daily), "replicates_per_day": protocol["policy_comparison"]["paired_replicates_per_day"],
        "primary": primary_result, "secondary": secondary,
        "completeness": {
            "unanswered_after_drain_traditional": int(run.loc[run.policy == "tradicional", "after_drain_unanswered"].sum()),
            "unanswered_after_drain_predictive": int(run.loc[run.policy == "predictivo", "after_drain_unanswered"].sum()),
            "minimum_response_completeness_pct": float(run["after_drain_response_completeness_pct"].min()),
        },
        "observed_descriptive_check": {
            "response_cohort_records": int(observed_check["observed_count"].sum()),
            "observed_daily_mean_response_min": float(observed_check["observed_mean_min"].mean()),
            "simulated_traditional_daily_mean_response_min": float(observed_check["simulated_mean_min"].mean()),
            "daily_mean_absolute_error_min": float((observed_check["simulated_mean_min"] - observed_check["observed_mean_min"]).abs().mean()),
            "daily_p90_absolute_error_min": float((observed_check["simulated_p90_min"] - observed_check["observed_p90_min"]).abs().mean()),
        },
        "note": "Block-bootstrap and HAC intervals use 21 calendar days, not incidents or seeds, as inferential units. No causal or operational claim follows.",
    }
    pipeline.save_json(RESULT_DIR / "analysis.json", result)
    print(json.dumps(result, indent=2), flush=True)
    return RESULT_DIR / "analysis.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "build", "forecast-report", "run", "analyze"))
    parser.add_argument("--snapshot", help="Verified complete July source snapshot ID")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit-pairs", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        print(prepare_config())
    elif args.command == "build":
        if not args.snapshot:
            parser.error("build requires --snapshot")
        build_package(args.snapshot)
    elif args.command == "forecast-report":
        print(json.dumps(report_forecasts(), indent=2))
    elif args.command == "run":
        run_evaluation(args.workers, args.limit_pairs)
    elif args.command == "analyze":
        analyze_evaluation()
    return 0


if __name__ == "__main__":
    sys.exit(main())
