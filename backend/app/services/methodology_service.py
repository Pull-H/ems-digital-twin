from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.core.paths import PROJECT_ROOT, REPORTS_DIR
from app.services.historical_data_service import DEFAULT_DATASET_ID, _snapshot_dir


TABLE_LABELS = {
    "crisp_dm_traceability": "Trazabilidad CRISP-DM",
    "eda_quality_summary": "EDA y calidad de datos",
    "temporal_cv_metrics": "Validacion temporal rolling-origin",
    "hyperparameter_search": "Busqueda de hiperparametros",
    "model_statistical_tests": "t pareada, Wilcoxon y bootstrap 95 %",
    "interpretability_feature_importance": "Interpretabilidad de variables",
    "artifact_interpretation": "Interpretacion de artefactos",
}


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _read_csv(path: Path, limit: int = 5000) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for index, row in enumerate(csv.DictReader(handle)) if index < limit]


def _base_dir(dataset_id: str) -> Path:
    _snapshot_dir(dataset_id)
    path = REPORTS_DIR / "nyc_ems" / dataset_id / "crisp_dm"
    if not path.exists():
        raise FileNotFoundError(
            "No existe el paquete CRISP-DM. Ejecuta "
            f"`python research\\visualization\\crisp_dm_methodology.py --snapshot {dataset_id}`."
        )
    return path


def crisp_dm_report(dataset_id: str = DEFAULT_DATASET_ID) -> dict[str, Any]:
    base = _base_dir(dataset_id)
    summary_path = base / "crisp_dm_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Falta {summary_path.relative_to(PROJECT_ROOT)}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    figures = []
    for figure in summary.get("figures", []):
        path = PROJECT_ROOT / figure["path"]
        if path.exists():
            figures.append({**figure, "svg": path.read_text(encoding="utf-8")})

    tables = {}
    for key, relative in summary.get("tables", {}).items():
        path = PROJECT_ROOT / relative
        if path.exists():
            tables[key] = {
                "title": TABLE_LABELS.get(key, key.replace("_", " ").title()),
                "path": _relative(path),
                "rows": _read_csv(path),
            }

    report_path = base / "CRISP_DM_REPORT.md"
    return {
        "dataset_id": dataset_id,
        "methodology": summary.get("methodology"),
        "status": summary.get("status"),
        "key_findings": summary.get("key_findings", {}),
        "report_path": _relative(report_path) if report_path.exists() else None,
        "figures": figures,
        "tables": tables,
    }
