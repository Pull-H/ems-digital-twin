from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = "20260909T040537085584Z-56d48fe7ce9b"
FEATURES = [
    "hour",
    "day_of_week",
    "day_of_month",
    "month",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_mean_24h",
    "rolling_sum_24h",
    "rolling_mean_168h",
    "rolling_sum_168h",
]
ZONE_ORDER = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "RICHMOND / STATEN ISLAND"]


def matrix(frame: pd.DataFrame, columns: list[str] | None = None) -> tuple[pd.DataFrame, list[str]]:
    base = frame[FEATURES].copy()
    base["is_weekend"] = base["is_weekend"].astype(int)
    zones = pd.get_dummies(frame["zone_id"], prefix="zone")
    result = pd.concat([base, zones], axis=1)
    if columns is None:
        columns = result.columns.tolist()
    for column in columns:
        if column not in result:
            result[column] = 0
    return result[columns].astype("float64"), columns


def metric_row(model_id: str, fold: str, actual: pd.Series, prediction: np.ndarray) -> dict[str, Any]:
    actual_values = actual.astype(float).to_numpy()
    prediction = np.clip(np.asarray(prediction, dtype=float), 0, None)
    errors = prediction - actual_values
    absolute = np.abs(errors)
    return {
        "model_id": model_id,
        "fold": fold,
        "rows": int(len(actual_values)),
        "mae": float(np.mean(absolute)),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "wape_pct": float(absolute.sum() / max(1e-9, actual_values.sum()) * 100),
        "bias": float(errors.mean()),
    }


def temporal_baseline(train: pd.DataFrame, evaluation: pd.DataFrame) -> np.ndarray:
    target = "target_demand_count"
    primary = train.groupby(["zone_id", "day_of_week", "hour"], observed=True)[target].mean().reset_index(name="prediction")
    zone_hour = train.groupby(["zone_id", "hour"], observed=True)[target].mean().reset_index(name="prediction")
    zone = train.groupby(["zone_id"], observed=True)[target].mean().reset_index(name="prediction")
    global_mean = float(train[target].mean())
    result = evaluation[["zone_id", "day_of_week", "hour"]].merge(primary, on=["zone_id", "day_of_week", "hour"], how="left")["prediction"]
    fallback = evaluation[["zone_id", "hour"]].merge(zone_hour, on=["zone_id", "hour"], how="left")["prediction"]
    result = result.fillna(fallback)
    fallback = evaluation[["zone_id"]].merge(zone, on=["zone_id"], how="left")["prediction"]
    return result.fillna(fallback).fillna(global_mean).clip(lower=0).to_numpy()


def rolling_origin_cv(panel: pd.DataFrame) -> pd.DataFrame:
    folds = [
        ("fold_1", "2026-05-02", "2026-05-09"),
        ("fold_2", "2026-05-09", "2026-05-16"),
        ("fold_3", "2026-05-16", "2026-05-23"),
        ("fold_4", "2026-05-23", "2026-06-01"),
        ("fold_5", "2026-06-01", "2026-06-08"),
    ]
    rows: list[dict[str, Any]] = []
    for fold_name, start, end in folds:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        train = panel[panel["target_start"] < start_ts]
        evaluation = panel[(panel["target_start"] >= start_ts) & (panel["target_start"] < end_ts)]
        if train.empty or evaluation.empty:
            continue
        train_matrix, columns = matrix(train)
        eval_matrix, _ = matrix(evaluation, columns)
        target = train["target_demand_count"].astype(float)
        models = {
            "baseline_temporal_v1": None,
            "random_forest_v1": RandomForestRegressor(
                n_estimators=120,
                max_depth=18,
                min_samples_leaf=3,
                random_state=2026,
                n_jobs=-1,
            ),
            "hist_gradient_boosting_v1": HistGradientBoostingRegressor(
                max_iter=180,
                learning_rate=0.06,
                max_leaf_nodes=31,
                l2_regularization=0.05,
                random_state=2026,
            ),
        }
        for model_id, model in models.items():
            if model is None:
                prediction = temporal_baseline(train, evaluation)
            else:
                model.fit(train_matrix, target)
                prediction = model.predict(eval_matrix)
            rows.append(metric_row(model_id, fold_name, evaluation["target_demand_count"], prediction))
    return pd.DataFrame(rows)


def hyperparameter_search(panel: pd.DataFrame) -> pd.DataFrame:
    train = panel[panel["split"] == "train"]
    validation = panel[panel["split"] == "validation"]
    train_matrix, columns = matrix(train)
    val_matrix, _ = matrix(validation, columns)
    target = train["target_demand_count"].astype(float)
    candidates: list[tuple[str, dict[str, Any], Any]] = [
        ("random_forest_v1", {"n_estimators": 120, "max_depth": 14, "min_samples_leaf": 3}, RandomForestRegressor(n_estimators=120, max_depth=14, min_samples_leaf=3, random_state=2026, n_jobs=-1)),
        ("random_forest_v1", {"n_estimators": 180, "max_depth": 18, "min_samples_leaf": 3}, RandomForestRegressor(n_estimators=180, max_depth=18, min_samples_leaf=3, random_state=2026, n_jobs=-1)),
        ("random_forest_v1", {"n_estimators": 220, "max_depth": 18, "min_samples_leaf": 2}, RandomForestRegressor(n_estimators=220, max_depth=18, min_samples_leaf=2, random_state=2026, n_jobs=-1)),
        ("hist_gradient_boosting_v1", {"max_iter": 180, "learning_rate": 0.04, "max_leaf_nodes": 31, "l2_regularization": 0.05}, HistGradientBoostingRegressor(max_iter=180, learning_rate=0.04, max_leaf_nodes=31, l2_regularization=0.05, random_state=2026)),
        ("hist_gradient_boosting_v1", {"max_iter": 260, "learning_rate": 0.06, "max_leaf_nodes": 31, "l2_regularization": 0.05}, HistGradientBoostingRegressor(max_iter=260, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=0.05, random_state=2026)),
        ("hist_gradient_boosting_v1", {"max_iter": 320, "learning_rate": 0.05, "max_leaf_nodes": 45, "l2_regularization": 0.10}, HistGradientBoostingRegressor(max_iter=320, learning_rate=0.05, max_leaf_nodes=45, l2_regularization=0.10, random_state=2026)),
    ]
    rows = []
    for index, (model_id, params, model) in enumerate(candidates, 1):
        model.fit(train_matrix, target)
        prediction = model.predict(val_matrix)
        row = metric_row(model_id, f"candidate_{index}", validation["target_demand_count"], prediction)
        row["params"] = json.dumps(params, ensure_ascii=False)
        row["selected_current"] = params in [
            {"n_estimators": 180, "max_depth": 18, "min_samples_leaf": 3},
            {"max_iter": 260, "learning_rate": 0.06, "max_leaf_nodes": 31, "l2_regularization": 0.05},
        ]
        rows.append(row)
    result = pd.DataFrame(rows)
    result["rank_by_mae_within_model"] = result.groupby("model_id")["mae"].rank(method="first")
    return result


def model_statistical_tests(predictions: pd.DataFrame) -> pd.DataFrame:
    test = predictions[predictions["split"] == "test"].copy()
    pivot = test.pivot_table(index=["target_start", "zone_id"], columns="model_id", values=["actual", "prediction"], aggfunc="first")
    actual = pivot["actual"].iloc[:, 0]
    model_ids = sorted(test["model_id"].unique())
    errors = {model_id: (pivot["prediction"][model_id] - actual).abs().dropna() for model_id in model_ids}
    pairs = [
        ("baseline_temporal_v1", "random_forest_v1"),
        ("baseline_temporal_v1", "hist_gradient_boosting_v1"),
        ("hist_gradient_boosting_v1", "random_forest_v1"),
    ]
    rows = []
    rng = np.random.default_rng(2026)
    for left, right in pairs:
        diff = errors[left].to_numpy() - errors[right].to_numpy()
        boot = []
        for _ in range(2000):
            sample = rng.choice(diff, size=len(diff), replace=True)
            boot.append(float(sample.mean()))
        t_stat, t_p = stats.ttest_rel(errors[left], errors[right])
        try:
            w_stat, w_p = stats.wilcoxon(errors[left], errors[right], zero_method="zsplit")
        except ValueError:
            w_stat, w_p = np.nan, np.nan
        rows.append(
            {
                "comparacion_de_modelos": f"{left} menos {right}",
                "prueba_t_pareada_p": float(t_p),
                "wilcoxon_signed_rank_p": float(w_p),
                "bootstrap_percentil_95_ic_inferior": float(np.percentile(boot, 2.5)),
                "bootstrap_percentil_95_ic_superior": float(np.percentile(boot, 97.5)),
                "diferencia_media_error_absoluto": float(diff.mean()),
                "interpretacion": "Diferencia positiva favorece al segundo modelo; se comparan errores absolutos pareados en prueba.",
            }
        )
    return pd.DataFrame(rows)


def feature_importance(panel: pd.DataFrame, snapshot: str) -> pd.DataFrame:
    model_path = ROOT / "research" / "artifacts" / "nyc_ems" / snapshot / "phase5" / "models" / "random_forest_v1.joblib"
    model = joblib.load(model_path)
    train = panel[panel["split"] == "train"]
    train_matrix, columns = matrix(train)
    importances = getattr(model, "feature_importances_", np.zeros(len(columns)))
    rows = pd.DataFrame({"feature": columns, "importance": importances})
    rows["importance_pct"] = rows["importance"] / rows["importance"].sum() * 100
    rows["interpretation"] = rows["feature"].map(feature_interpretation).fillna("Aporta señal tabular al pronóstico horario.")
    return rows.sort_values("importance", ascending=False)


def feature_interpretation(feature: str) -> str:
    if feature.startswith("lag_"):
        return "Demanda reciente observada; captura dependencia temporal antes de la hora objetivo."
    if feature.startswith("rolling_"):
        return "Tendencia móvil previa; suaviza ciclos de 24 h o 168 h."
    if feature.startswith("zone_"):
        return "Efecto territorial del borough; ajusta diferencias estructurales de volumen."
    if feature == "hour":
        return "Ciclo intradía de llamadas EMS."
    if feature == "day_of_week":
        return "Patrón semanal de demanda."
    if feature == "is_weekend":
        return "Diferencia entre fin de semana y días laborables."
    if feature == "day_of_month":
        return "Control calendárico de baja interpretación causal."
    if feature == "month":
        return "Control temporal del trimestre estudiado."
    return "Variable predictiva tabular."


def save_table(path: Path, frame: pd.DataFrame) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8")
    return path.relative_to(ROOT).as_posix()


def make_figures(out: Path, data: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    figures = out / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
    generated = []

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.axis("off")
    phases = ["Negocio", "Datos", "Preparación", "Modelado", "Evaluación", "Despliegue"]
    x = np.linspace(0.08, 0.92, len(phases))
    for i, phase in enumerate(phases):
        ax.text(x[i], 0.55, phase, ha="center", va="center", bbox=dict(boxstyle="round,pad=.35", fc="#eef2ff", ec="#334155"))
        if i < len(phases) - 1:
            ax.annotate("", xy=(x[i + 1] - .065, .55), xytext=(x[i] + .065, .55), arrowprops=dict(arrowstyle="->", color="#475569"))
    ax.text(.5, .18, "Iteración: evaluación alimenta ajustes de datos, features, hiperparámetros y política", ha="center", color="#475569")
    path = figures / "01_crisp_dm_flow.svg"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    generated.append({"id": "crisp_dm_flow", "title": "Flujo CRISP-DM", "path": path.relative_to(ROOT).as_posix()})

    eda = data["eda_counts"]
    fig, ax = plt.subplots(figsize=(7.4, 4))
    ax.bar(eda["borough"], eda["demand"], color="#0f766e")
    ax.set_title("EDA: demanda por borough")
    ax.set_ylabel("Incidentes")
    ax.tick_params(axis="x", rotation=20)
    path = figures / "02_eda_demand_by_borough.svg"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    generated.append({"id": "eda_demand_by_borough", "title": "EDA por borough", "path": path.relative_to(ROOT).as_posix()})

    split = data["split_summary"]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    colors = {"train": "#334155", "validation": "#2563eb", "test": "#059669"}
    for i, row in split.iterrows():
        start = pd.Timestamp(row["start"])
        end = pd.Timestamp(row["end"])
        ax.barh(0, (end - start).days, left=start, color=colors[row["split"]], label=row["split"])
    ax.set_yticks([])
    ax.set_title("Partición temporal train/validation/test")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys(), ncols=3, frameon=False)
    path = figures / "03_temporal_split.svg"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    generated.append({"id": "temporal_split", "title": "Particiones temporales", "path": path.relative_to(ROOT).as_posix()})

    cv = data["temporal_cv_metrics"]
    fig, ax = plt.subplots(figsize=(7.4, 4))
    for model_id, subset in cv.groupby("model_id"):
        ax.plot(subset["fold"], subset["mae"], marker="o", label=model_id)
    ax.set_title("Validación temporal rolling-origin")
    ax.set_ylabel("MAE")
    ax.tick_params(axis="x", rotation=20)
    ax.legend(frameon=False, fontsize=7)
    path = figures / "04_temporal_cv_mae.svg"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    generated.append({"id": "temporal_cv_mae", "title": "MAE por fold temporal", "path": path.relative_to(ROOT).as_posix()})

    hyp = data["hyperparameter_search"]
    fig, ax = plt.subplots(figsize=(7.4, 4))
    labels = [f"{row.model_id.replace('_v1', '')}\n{row.fold}" for row in hyp.itertuples()]
    ax.bar(labels, hyp["mae"], color=["#2563eb" if selected else "#94a3b8" for selected in hyp["selected_current"]])
    ax.set_title("Búsqueda ligera de hiperparámetros en validación")
    ax.set_ylabel("MAE")
    ax.tick_params(axis="x", rotation=35)
    path = figures / "05_hyperparameters_mae.svg"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    generated.append({"id": "hyperparameters_mae", "title": "Hiperparámetros vs MAE", "path": path.relative_to(ROOT).as_posix()})

    imp = data["feature_importance"].head(12).sort_values("importance")
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.barh(imp["feature"], imp["importance_pct"], color="#7c3aed")
    ax.set_title("Interpretabilidad: importancia de variables Random Forest")
    ax.set_xlabel("Importancia relativa (%)")
    path = figures / "06_feature_importance.svg"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    generated.append({"id": "feature_importance", "title": "Importancia de variables", "path": path.relative_to(ROOT).as_posix()})
    return generated


def build(snapshot: str = DEFAULT_SNAPSHOT) -> dict[str, Any]:
    folder = ROOT / "data" / "nyc_ems" / snapshot
    processed = folder / "processed"
    reports = ROOT / "reports" / "nyc_ems" / snapshot / "crisp_dm"
    tables = reports / "tables"
    panel = pd.read_parquet(processed / "model_ready_hourly_demand_panel.parquet")
    predictions = pd.read_parquet(processed / "retrospective_forecasts.parquet")
    cohort = json.loads((processed / "cohort_summary.json").read_text(encoding="utf-8"))
    partitions = json.loads((processed / "temporal_partitions.json").read_text(encoding="utf-8"))

    quarantine_path = folder / "interim" / "quarantine.csv"
    quarantine_rows = int(len(pd.read_csv(quarantine_path))) if quarantine_path.exists() else 0
    eda_counts = pd.DataFrame(
        {
            "borough": list(cohort["borough_counts_demand"].keys()),
            "demand": list(cohort["borough_counts_demand"].values()),
            "response": [cohort["borough_counts_response"].get(zone, 0) for zone in cohort["borough_counts_demand"].keys()],
        }
    )
    eda_quality = pd.DataFrame(
        [
            ["raw_rows", cohort["source_rows"], "Registros fuente verificados"],
            ["demand_cohort", cohort["demand_cohort_rows"], "Base para EDA y pronóstico"],
            ["response_cohort", cohort["response_cohort_rows"], "Base para tiempos de respuesta"],
            ["transport_cohort", cohort["transport_cohort_rows"], "Base para tiempos hospitalarios"],
            ["quarantine_rows", quarantine_rows, "Registros trazados por incoherencia"],
        ],
        columns=["indicator", "value", "interpretation"],
    )
    split_summary = pd.DataFrame(
        [
            [name, value["start_inclusive"], value["end_exclusive"], value.get("rows"), value.get("model_ready_rows")]
            for name, value in partitions["splits"].items()
        ],
        columns=["split", "start", "end", "rows", "model_ready_rows"],
    )
    cv = rolling_origin_cv(panel)
    hyper = hyperparameter_search(panel)
    tests = model_statistical_tests(predictions)
    importance = feature_importance(panel, snapshot)
    traceability = pd.DataFrame(
        [
            ["Business understanding", "Definir pregunta: predecir demanda y evaluar despacho", "docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md", "Completo"],
            ["Data understanding", "EDA, calidad, cohortes y conteos por borough", "docs/NYC_EMS_PHASE3_QUALITY_REPORT.md", "Completo"],
            ["Data preparation", "Panel zona-hora, rezagos, particiones temporales", "docs/NYC_EMS_PHASE4_FEATURES_REPORT.md", "Completo"],
            ["Modeling", "Baseline, Random Forest, HistGradientBoosting, hiperparámetros", "docs/NYC_EMS_PHASE5_MODEL_REPORT.md", "Completo"],
            ["Evaluation", "Métricas, rolling-origin, pruebas pareadas y bootstrap", "reports/nyc_ems/<snapshot>/crisp_dm", "Completo con límites"],
            ["Deployment", "FastAPI, frontend 2D/3D, asistente LangGraph", "docs/NYC_EMS_PHASE7_API_FRONTEND_REPORT.md", "Prototipo reproducible"],
        ],
        columns=["crisp_dm_phase", "software_evidence", "artifact", "status"],
    )

    artifact_interpretation = pd.DataFrame(
        [
            ["Figura", "01_crisp_dm_flow", "Muestra cómo el pipeline sigue CRISP-DM y vuelve de evaluación a mejoras.", "Explica trazabilidad metodológica, no desempeño."],
            ["Figura", "02_eda_demand_by_borough", "Permite observar concentración territorial de demanda.", "Brooklyn/Bronx/Manhattan concentran más eventos; Staten Island tiene bajo volumen."],
            ["Figura", "03_temporal_split", "Justifica validación temporal sin fuga de información.", "Entrena con pasado y evalúa futuro."],
            ["Figura", "04_temporal_cv_mae", "Evalúa estabilidad temporal de modelos.", "Variaciones entre folds indican sensibilidad a semanas específicas."],
            ["Figura", "05_hyperparameters_mae", "Compara candidatos de hiperparámetros.", "El menor MAE de validación no garantiza mejor prueba, pero guía selección."],
            ["Figura", "06_feature_importance", "Explica qué variables usa Random Forest.", "Rezagos y ventanas móviles sostienen la predicción; no son causas clínicas."],
            ["Tabla", "crisp_dm_traceability", "Mapea fases CRISP-DM a artefactos del software.", "Permite auditoría de reproducibilidad."],
            ["Tabla", "eda_quality_summary", "Resume calidad de datos y cohortes.", "Distingue demanda, respuesta y transporte."],
            ["Tabla", "temporal_cv_metrics", "Presenta validación cruzada temporal.", "Evita mezclar futuro en entrenamiento."],
            ["Tabla", "hyperparameter_search", "Documenta candidatos y parámetros.", "Evita dejar hiperparámetros como decisión implícita."],
            ["Tabla", "model_statistical_tests", "Prueba diferencias de errores absolutos.", "Intervalos y p-values apoyan comparación de modelos."],
            ["Tabla", "interpretability_feature_importance", "Lista importancia e interpretación de variables.", "Aporta explicabilidad global del modelo seleccionado."],
        ],
        columns=["artifact_type", "artifact_id", "interpretability", "explainability_note"],
    )

    tables.mkdir(parents=True, exist_ok=True)
    table_paths = {
        "crisp_dm_traceability": save_table(tables / "crisp_dm_traceability.csv", traceability),
        "eda_quality_summary": save_table(tables / "eda_quality_summary.csv", eda_quality),
        "temporal_cv_metrics": save_table(tables / "temporal_cv_metrics.csv", cv),
        "hyperparameter_search": save_table(tables / "hyperparameter_search.csv", hyper),
        "model_statistical_tests": save_table(tables / "model_statistical_tests.csv", tests),
        "interpretability_feature_importance": save_table(tables / "interpretability_feature_importance.csv", importance),
        "artifact_interpretation": save_table(tables / "artifact_interpretation.csv", artifact_interpretation),
    }
    figures = make_figures(
        reports,
        {
            "eda_counts": eda_counts,
            "split_summary": split_summary,
            "temporal_cv_metrics": cv,
            "hyperparameter_search": hyper,
            "feature_importance": importance,
        },
    )
    summary = {
        "dataset_id": snapshot,
        "methodology": "CRISP-DM adaptado a gemelo digital EMS",
        "status": "software evidence generated",
        "tables": table_paths,
        "figures": figures,
        "key_findings": {
            "eda": "Demanda completa preservada; respuesta y transporte usan cohortes específicas.",
            "modeling": "Tres modelos comparados; validación temporal y búsqueda ligera agregadas.",
            "statistics": "Comparaciones pareadas de errores con t-test, Wilcoxon y bootstrap.",
            "interpretability": "Importancia global de variables para Random Forest.",
        },
    }
    (reports / "crisp_dm_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    report = [
        "# CRISP-DM aplicado al gemelo digital EMS",
        "",
        f"Snapshot: `{snapshot}`.",
        "",
        "## Evidencia generada",
        "",
        "- 6 tablas principales: trazabilidad, EDA/calidad, validación temporal, hiperparámetros, pruebas estadísticas e interpretabilidad.",
        "- 6 figuras: flujo CRISP-DM, EDA territorial, partición temporal, validación rolling-origin, búsqueda de hiperparámetros e importancia de variables.",
        "- Cada artefacto incluye interpretación y nota de explicabilidad en `artifact_interpretation.csv`.",
        "",
        "## Lectura metodológica",
        "",
        "La validación cruzada convencional se reemplaza por validación temporal rolling-origin para evitar fuga de futuro. "
        "Los hiperparámetros se documentan con una búsqueda ligera en validación. Las pruebas estadísticas comparan errores absolutos pareados en el split de prueba. "
        "La interpretabilidad se reporta como importancia global de variables, útil para auditar patrones usados por el modelo, no para inferencia causal.",
    ]
    (reports / "CRISP_DM_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default=DEFAULT_SNAPSHOT)
    args = parser.parse_args()
    print(json.dumps(build(args.snapshot), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
