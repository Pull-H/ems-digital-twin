from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT = "20260909T040537085584Z-56d48fe7ce9b"
MODEL_LABELS = {
    "baseline_temporal_v1": "Baseline temporal",
    "random_forest_v1": "Random Forest",
    "hist_gradient_boosting_v1": "Gradient Boosting",
}
COLORS = ["#334155", "#2563eb", "#059669", "#dc2626", "#7c3aed", "#d97706"]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def svg_text(x: float, y: float, text: str, size: int = 11, anchor: str = "middle", weight: str = "400", fill: str = "#334155") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-family="Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}">{html.escape(text)}</text>'


def write_svg(path: Path, content: str, width: int = 980, height: int = 560) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>\n{content}\n</svg>\n',
        encoding="utf-8",
    )


def global_metric_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for model_id, splits in metrics["global"].items():
        for split, values in splits.items():
            rows.append(
                {
                    "model_id": model_id,
                    "model_label": MODEL_LABELS.get(model_id, model_id),
                    "split": split,
                    "rows": values["rows"],
                    "mae": round(values["mae"], 4),
                    "rmse": round(values["rmse"], 4),
                    "wape": round(values["wape"], 4),
                    "wape_pct": round(values["wape"] * 100, 2),
                    "bias": round(values["bias"], 4),
                    "actual_sum": round(values["actual_sum"], 2),
                    "prediction_sum": round(values["prediction_sum"], 2),
                }
            )
    return rows


def by_zone_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for model_id, splits in metrics["by_zone"].items():
        for split, zones in splits.items():
            for zone, values in zones.items():
                rows.append(
                    {
                        "model_id": model_id,
                        "model_label": MODEL_LABELS.get(model_id, model_id),
                        "split": split,
                        "zone_id": zone,
                        "rows": values["rows"],
                        "mae": round(values["mae"], 4),
                        "rmse": round(values["rmse"], 4),
                        "wape": round(values["wape"], 4),
                        "wape_pct": round(values["wape"] * 100, 2),
                        "bias": round(values["bias"], 4),
                    }
                )
    return rows


def grouped_bar_svg(title: str, rows: list[dict[str, Any]], metrics: list[tuple[str, str]], path: Path) -> None:
    width, height = 980, 560
    left, right, top, bottom = 90, 30, 70, 100
    plot_w = width - left - right
    plot_h = height - top - bottom
    values = [float(row[key]) for row in rows for key, _ in metrics]
    max_value = max(values) * 1.15 if values else 1
    group_w = plot_w / max(1, len(rows))
    bar_w = min(48, group_w / (len(metrics) + 1))
    parts = [svg_text(width / 2, 32, title, 18, weight="700", fill="#0f172a")]
    for tick in range(6):
        value = max_value * tick / 5
        y = top + plot_h - (value / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>')
        parts.append(svg_text(left - 12, y + 4, f"{value:.1f}", 10, anchor="end", fill="#64748b"))
    for idx, row in enumerate(rows):
        center = left + group_w * idx + group_w / 2
        start_x = center - (len(metrics) * bar_w) / 2
        for metric_idx, (key, label) in enumerate(metrics):
            value = float(row[key])
            bar_h = (value / max_value) * plot_h
            x = start_x + metric_idx * bar_w
            y = top + plot_h - bar_h
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w-3:.1f}" height="{bar_h:.1f}" rx="3" fill="{COLORS[metric_idx]}"/>')
            parts.append(svg_text(x + (bar_w - 3) / 2, y - 5, f"{value:.1f}", 9, fill="#334155"))
        parts.append(svg_text(center, height - 72, row["model_label"], 10, fill="#334155"))
        parts.append(svg_text(center, height - 56, row["split"], 9, fill="#64748b"))
    legend_x = left
    for metric_idx, (_, label) in enumerate(metrics):
        x = legend_x + metric_idx * 150
        parts.append(f'<rect x="{x}" y="{height-35}" width="12" height="12" rx="2" fill="{COLORS[metric_idx]}"/>')
        parts.append(svg_text(x + 18, height - 25, label, 11, anchor="start", fill="#334155"))
    write_svg(path, "\n".join(parts), width, height)


def heatmap_svg(title: str, rows: list[dict[str, Any]], row_key: str, col_keys: list[tuple[str, str]], path: Path) -> None:
    width, height = 900, 420
    left, top = 210, 80
    cell_w, cell_h = 150, 54
    values = [float(row[key]) for row in rows for key, _ in col_keys]
    min_v, max_v = min(values), max(values)
    span = max(max_v - min_v, 1e-9)
    parts = [svg_text(width / 2, 32, title, 18, weight="700", fill="#0f172a")]
    for col_idx, (_, label) in enumerate(col_keys):
        parts.append(svg_text(left + col_idx * cell_w + cell_w / 2, top - 18, label, 12, weight="700", fill="#334155"))
    for row_idx, row in enumerate(rows):
        y = top + row_idx * cell_h
        parts.append(svg_text(left - 14, y + 32, row[row_key], 11, anchor="end", fill="#334155"))
        for col_idx, (key, _) in enumerate(col_keys):
            value = float(row[key])
            intensity = (value - min_v) / span
            blue = int(245 - 115 * intensity)
            color = f"rgb({blue},{blue + 5},{255})"
            x = left + col_idx * cell_w
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w-8}" height="{cell_h-8}" rx="4" fill="{color}" stroke="#cbd5e1"/>')
            parts.append(svg_text(x + (cell_w - 8) / 2, y + 29, f"{value:.3f}", 12, weight="700", fill="#0f172a"))
    write_svg(path, "\n".join(parts), width, height)


def line_svg(title: str, series: pd.DataFrame, path: Path) -> None:
    width, height = 980, 520
    left, right, top, bottom = 70, 30, 70, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_value = max(float(series["actual"].max()), float(series["prediction"].max())) * 1.1
    parts = [svg_text(width / 2, 32, title, 18, weight="700", fill="#0f172a")]
    for tick in range(6):
        value = max_value * tick / 5
        y = top + plot_h - (value / max_value) * plot_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        parts.append(svg_text(left - 10, y + 4, f"{value:.0f}", 10, anchor="end", fill="#64748b"))
    def points(column: str) -> str:
        coords = []
        total = max(1, len(series) - 1)
        for idx, value in enumerate(series[column].tolist()):
            x = left + plot_w * idx / total
            y = top + plot_h - (float(value) / max_value) * plot_h
            coords.append(f"{x:.1f},{y:.1f}")
        return " ".join(coords)
    parts.append(f'<polyline fill="none" stroke="#0f766e" stroke-width="2.2" points="{points("actual")}"/>')
    parts.append(f'<polyline fill="none" stroke="#4f46e5" stroke-width="2.2" points="{points("prediction")}"/>')
    parts.append(f'<rect x="{left}" y="{height-42}" width="12" height="12" fill="#0f766e" rx="2"/>')
    parts.append(svg_text(left + 18, height - 32, "Real", 11, anchor="start"))
    parts.append(f'<rect x="{left+85}" y="{height-42}" width="12" height="12" fill="#4f46e5" rx="2"/>')
    parts.append(svg_text(left + 103, height - 32, "Predicho", 11, anchor="start"))
    first = str(series["target_start"].iloc[0])[:10]
    last = str(series["target_start"].iloc[-1])[:10]
    parts.append(svg_text(width / 2, height - 18, f"Periodo test: {first} a {last}", 10, fill="#64748b"))
    write_svg(path, "\n".join(parts), width, height)


def build_report(snapshot: str, output_dir: Path, global_rows: list[dict[str, Any]], figures: dict[str, Path], metrics: dict[str, Any]) -> None:
    selection = metrics.get("selection", {})
    test_rows = [row for row in global_rows if row["split"] == "test"]
    best_test_mae = min(test_rows, key=lambda row: row["mae"])
    def rel(path: Path) -> str:
        return path.resolve().relative_to(ROOT).as_posix()
    lines = [
        "# NYC EMS - Mini fase EMS-019B: visualizacion de rendimiento predictivo",
        "",
        f"Snapshot: `{snapshot}`.",
        "",
        "## Objetivo",
        "",
        "Generar tablas y graficos exportables para comparar el desempeno de los modelos de demanda usados por el sistema.",
        "",
        "## Lectura principal",
        "",
        f"- Modelo seleccionado por validacion: `{selection.get('best_model_id')}`.",
        f"- Criterio de seleccion: {selection.get('criterion')}.",
        f"- Mejor MAE en prueba final: `{best_test_mae['model_id']}` con MAE {best_test_mae['mae']}.",
        "",
        "## Graficos generados",
        "",
    ]
    for name, path in figures.items():
        lines.append(f"- {name}: `{rel(path)}`")
    lines.extend(
        [
            "",
            "## Tablas generadas",
            "",
            f"- Metricas globales: `{rel(output_dir / 'tables/global_model_metrics.csv')}`",
            f"- Metricas por borough: `{rel(output_dir / 'tables/by_zone_model_metrics.csv')}`",
            f"- Matriz test modelo-metrica: `{rel(output_dir / 'tables/test_model_metric_matrix.csv')}`",
            f"- Serie real vs predicho: `{rel(output_dir / 'tables/selected_model_test_timeseries.csv')}`",
            "",
            "## Nota metodologica",
            "",
            "No se genera una matriz de confusion porque el problema es de regresion de conteos horarios, no clasificacion. En su lugar se entrega una matriz modelo x metrica y errores por borough.",
        ]
    )
    (output_dir / "MODEL_PERFORMANCE_VISUAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate(snapshot: str) -> Path:
    metrics_path = ROOT / "research" / "artifacts" / "nyc_ems" / snapshot / "phase5" / "reports" / "metrics.json"
    forecasts_path = ROOT / "data" / "nyc_ems" / snapshot / "processed" / "retrospective_forecasts.parquet"
    metrics = read_json(metrics_path)
    output_dir = ROOT / "reports" / "nyc_ems" / snapshot / "model_performance"
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    global_rows = global_metric_rows(metrics)
    zone_rows = by_zone_rows(metrics)
    write_csv(tables_dir / "global_model_metrics.csv", global_rows)
    write_csv(tables_dir / "by_zone_model_metrics.csv", zone_rows)

    test_rows = [row for row in global_rows if row["split"] == "test"]
    matrix_rows = [
        {
            "model": row["model_label"],
            "mae": row["mae"],
            "rmse": row["rmse"],
            "wape_pct": row["wape_pct"],
            "bias": row["bias"],
        }
        for row in test_rows
    ]
    write_csv(tables_dir / "test_model_metric_matrix.csv", matrix_rows)

    forecasts = pd.read_parquet(forecasts_path)
    selected_model = metrics["selection"]["best_model_id"]
    ts = (
        forecasts[(forecasts["split"] == "test") & (forecasts["model_id"] == selected_model)]
        .groupby("target_start", as_index=False)[["actual", "prediction"]]
        .sum()
        .sort_values("target_start")
    )
    ts.to_csv(tables_dir / "selected_model_test_timeseries.csv", index=False)
    sampled_ts = ts.iloc[:: max(1, len(ts) // 120)].reset_index(drop=True)

    figures = {
        "Comparacion global en prueba": figures_dir / "global_test_metrics.svg",
        "Matriz modelo-metrica": figures_dir / "model_metric_matrix.svg",
        "MAE por borough en prueba": figures_dir / "borough_mae_test.svg",
        "Serie temporal real vs predicho": figures_dir / "actual_vs_predicted_test.svg",
    }
    grouped_bar_svg(
        "Metricas globales de prueba por modelo",
        test_rows,
        [("mae", "MAE"), ("rmse", "RMSE"), ("wape_pct", "WAPE %")],
        figures["Comparacion global en prueba"],
    )
    heatmap_svg(
        "Matriz de rendimiento en prueba",
        matrix_rows,
        "model",
        [("mae", "MAE"), ("rmse", "RMSE"), ("wape_pct", "WAPE %"), ("bias", "Sesgo")],
        figures["Matriz modelo-metrica"],
    )
    zone_test_rows = [row for row in zone_rows if row["split"] == "test"]
    grouped_bar_svg(
        "MAE por borough en prueba",
        zone_test_rows,
        [("mae", "MAE")],
        figures["MAE por borough en prueba"],
    )
    line_svg(
        f"Demanda real vs predicha - {MODEL_LABELS.get(selected_model, selected_model)}",
        sampled_ts,
        figures["Serie temporal real vs predicho"],
    )
    build_report(snapshot, output_dir, global_rows, figures, metrics)
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NYC EMS model performance tables and SVG figures.")
    parser.add_argument("--snapshot", default=DEFAULT_SNAPSHOT)
    args = parser.parse_args()
    output = generate(args.snapshot)
    print(output)


if __name__ == "__main__":
    main()
