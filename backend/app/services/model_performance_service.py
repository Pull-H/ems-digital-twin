from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.core.paths import PROJECT_ROOT, REPORTS_DIR
from app.services.historical_data_service import DEFAULT_DATASET_ID, _snapshot_dir


FIGURES = {
    "global_test_metrics": {
        "title": "Metricas globales de prueba",
        "description": "Compara MAE, RMSE y WAPE entre modelos sobre el split de prueba.",
        "file": "global_test_metrics.svg",
    },
    "model_metric_matrix": {
        "title": "Matriz modelo-metrica",
        "description": "Resume MAE, RMSE, WAPE y sesgo por modelo.",
        "file": "model_metric_matrix.svg",
    },
    "borough_mae_test": {
        "title": "MAE por borough",
        "description": "Muestra el error absoluto medio por borough y modelo.",
        "file": "borough_mae_test.svg",
    },
    "actual_vs_predicted_test": {
        "title": "Real vs predicho",
        "description": "Serie temporal agregada del modelo seleccionado en el split de prueba.",
        "file": "actual_vs_predicted_test.svg",
    },
}

TABLES = {
    "global_model_metrics": "global_model_metrics.csv",
    "by_zone_model_metrics": "by_zone_model_metrics.csv",
    "test_model_metric_matrix": "test_model_metric_matrix.csv",
    "selected_model_test_timeseries": "selected_model_test_timeseries.csv",
}


def _base_dir(dataset_id: str) -> Path:
    _snapshot_dir(dataset_id)
    path = REPORTS_DIR / "nyc_ems" / dataset_id / "model_performance"
    if not path.exists():
        raise FileNotFoundError(
            "No existe el paquete de visualizacion predictiva. Ejecuta "
            f"`python research\\visualization\\model_performance.py --snapshot {dataset_id}`."
        )
    return path


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _read_csv(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = []
        for index, row in enumerate(csv.DictReader(handle)):
            if index >= limit:
                break
            rows.append(row)
        return rows


def model_performance_report(dataset_id: str = DEFAULT_DATASET_ID) -> dict[str, Any]:
    base = _base_dir(dataset_id)
    figures = []
    for key, meta in FIGURES.items():
        path = base / "figures" / meta["file"]
        if path.exists():
            figures.append(
                {
                    "id": key,
                    "title": meta["title"],
                    "description": meta["description"],
                    "path": _relative(path),
                    "svg": path.read_text(encoding="utf-8"),
                }
            )
    tables = {}
    for key, filename in TABLES.items():
        path = base / "tables" / filename
        if path.exists():
            tables[key] = {"path": _relative(path), "rows": _read_csv(path)}
    summary_path = base / "MODEL_PERFORMANCE_VISUAL_REPORT.md"
    return {
        "dataset_id": dataset_id,
        "report_path": _relative(summary_path) if summary_path.exists() else None,
        "figures": figures,
        "tables": tables,
    }
