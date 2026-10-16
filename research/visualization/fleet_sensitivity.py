"""Publication-sized descriptive plots for completed phase 8D batches."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

LABELS = {"tradicional": "Tradicional", "predictivo": "Predictiva v1"}
COLORS = {"tradicional": "#2563eb", "predictivo": "#c2410c"}


def render_report(output):
    output = Path(output)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest["status"] != "complete":
        raise ValueError("Figures require all configured pairs, not a favorable subset")
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    runs = pd.read_csv(output / "tables/run_metrics.csv")
    summary = pd.read_csv(output / "tables/scenario_summary.csv")
    fleet = pd.read_csv(output / "tables/historical_fleet_summary.csv")
    zones = pd.read_csv(output / "tables/by_zone_metrics.csv")
    figures = output / "figures"
    figures.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    interpretations = []

    def save(fig, name, title, interpretation, limitation):
        fig.tight_layout()
        fig.savefig(figures / f"{name}.png", dpi=180, bbox_inches="tight")
        fig.savefig(figures / f"{name}.svg", bbox_inches="tight")
        plt.close(fig)
        interpretations.append({"artifact": name, "title": title,
                                "interpretation": interpretation, "limitation": limitation})

    historical = runs[runs.family == "fleet"]
    for metric, name, title, ylabel in (
        ("after_drain_mean_response_min", "fleet_response", "Respuesta frente a flota asumida", "Respuesta media tras vaciado (min)"),
        ("at_cut_unanswered", "fleet_unanswered", "Incidentes sin llegada a escena al corte", "Incidentes sin respuesta al corte (cantidad)"),
        ("measurement_utilization", "fleet_utilization", "Uso de unidades durante las 24 horas medidas", "Fraccion de tiempo ocupado (0-1)"),
    ):
        fig, ax = plt.subplots(figsize=(9, 4.8))
        for policy in LABELS:
            group = historical[historical.policy == policy].groupby("fleet")[metric].agg(["mean", "min", "max"]).sort_index()
            ax.plot(group.index, group["mean"], label=LABELS[policy], color=COLORS[policy],
                    marker="o" if policy == "tradicional" else "s", linestyle="-" if policy == "tradicional" else "--")
            ax.fill_between(group.index, group["min"], group["max"], color=COLORS[policy], alpha=.12)
        ax.set(title=title, xlabel="Flota asumida (unidades)", ylabel=ylabel)
        ax.set_xticks(sorted(config["fleet_sizes"]))
        ax.grid(alpha=.2)
        ax.legend()
        fig.text(.5, -.01, "Media de dias/semillas. Bandas: minimo-maximo observado; no intervalos de confianza.", ha="center", fontsize=9)
        values = fleet[metric]
        save(fig, name, title, f"Las medias por flota y politica abarcan {values.min():.3f} a {values.max():.3f}. "
             "Comparar ambas curvas y la dispersion entre dias/semillas; coincidencia significa resultados iguales a esta escala.",
             "Tres dias de desarrollo. Una media de respuesta baja no basta si quedan casos sin respuesta; consultar completitud.")

    controls = summary[(summary.family == "assumption") |
                       ((summary.family == "fleet") & (summary.day == config["assumption_day"]) & (summary.fleet == config["assumption_fleet"]))]
    fig, ax = plt.subplots(figsize=(10, 5))
    for policy in LABELS:
        group = controls[controls.policy == policy].set_index("variant").sort_index()
        ax.plot(group.index, group.after_drain_mean_response_min, marker="o", color=COLORS[policy],
                linestyle="-" if policy == "tradicional" else "--", label=LABELS[policy])
    ax.set(title=f"Sensibilidad de supuestos: {config['assumption_fleet']} unidades, {config['assumption_day']}",
           xlabel="Variante (un factor por vez)", ylabel="Respuesta media tras vaciado (min)")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(alpha=.2)
    ax.legend()
    save(fig, "assumptions", "Sensibilidad de supuestos",
         "Comparar travel_080/120 y release_080/120 con base; son multiplicadores 0.8/1.2. warmup_000/720 usa 0/12 horas frente a 6 horas base.",
         "Un dia y una flota fijados previamente. Perturbaciones exploratorias de +/-20%, no incertidumbre empirica estimada.")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    day = config["forecast_days"][0]
    for ax, family, title in zip(axes, ("fleet", "forecast"), ("Llegadas historicas", "Llegadas generadas desde pronosticos")):
        subset = summary[(summary.family == family) & (summary.day == day)]
        for policy in LABELS:
            group = subset[subset.policy == policy].sort_values("fleet")
            ax.plot(group.fleet, group.after_drain_mean_response_min, marker="o", color=COLORS[policy],
                    linestyle="-" if policy == "tradicional" else "--", label=LABELS[policy])
        ax.set(title=title, xlabel="Flota asumida (unidades)")
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Respuesta media tras vaciado (min)")
    axes[1].legend()
    fig.suptitle(f"Entradas de demanda separadas: {day}")
    save(fig, "demand_sources", "Historico y demanda generada",
         "Los paneles mantienen el mismo dia y flotas. Cada politica comparte llegadas dentro de su fuente; las fuentes no representan los mismos incidentes.",
         "Las diferencias entre paneles mezclan cambios de volumen/composicion. No son errores de prediccion ni efectos causales.")

    fig, ax = plt.subplots(figsize=(10, 5))
    subset = zones[(zones.family == "fleet") & (zones.fleet == config["assumption_fleet"])]
    for policy in LABELS:
        group = subset[subset.policy == policy].groupby("zone_name").mean_response_min.mean().sort_index()
        ax.plot(group.index, group.values, marker="o", color=COLORS[policy],
                linestyle="-" if policy == "tradicional" else "--", label=LABELS[policy])
    ax.set(title=f"Respuesta por borough: {config['assumption_fleet']} unidades", xlabel="Borough",
           ylabel="Media por dia/semilla tras vaciado (min)")
    ax.tick_params(axis="x", rotation=15)
    ax.legend()
    ax.grid(alpha=.2)
    save(fig, "borough_response", "Resultados territoriales",
         "La media global puede ocultar diferencias entre boroughs. Esta figura promedia cada dia/semilla con el mismo peso dentro de cada zona.",
         "Diferencias territoriales no equivalen a equidad por ingresos, genero o raza; esas variables no se integraron.")
    pd.DataFrame(interpretations).to_csv(output / "tables/artifact_interpretation.csv", index=False)
    lines = ["# Fase 8D: sensibilidad de flota y supuestos", "",
             f"Lote: `{output.name}`. Estado: completo. Pares: {len(manifest['completed'])}; corridas: {len(runs)}.",
             "", "Evaluacion descriptiva de desarrollo. No se estiman valores p ni se declara superioridad de una politica.", "",
             f"Dias historicos: {', '.join(config['development_days'])}. {config['repetitions']} semillas por escenario.",
             "Medicion: 24 horas; calentamiento base: 6 horas; vaciado maximo: 24 horas sin nuevas llegadas.", "",
             "## Flota historica", "",
             "Medias con el mismo peso por dia/semilla. Pendientes al corte no son servicios sin completar.", "",
             "| Flota | Politica | Respuesta (min) | P90 (min) | Sin respuesta al corte | Sin respuesta tras vaciado | Utilizacion |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for row in fleet.to_dict("records"):
        lines.append(f"| {row['fleet']} | {LABELS[row['policy']]} | {row['after_drain_mean_response_min']:.3f} | "
                     f"{row['after_drain_p90_response_min']:.3f} | {row['at_cut_unanswered']:.2f} | "
                     f"{row['after_drain_unanswered']:.2f} | {row['measurement_utilization']:.3f} |")
    lines += ["", "## Completitud y lectura", "",
              f"Corridas con respuestas pendientes tras vaciado: {int((runs.after_drain_unanswered > 0).sum())}/{len(runs)}.",
              f"Corridas con algun servicio (incluido calentamiento) sin terminar al limite: {int(runs.drain_capped_with_unfinished.sum())}.",
              "La media/P90 tras vaciado usa respuestas conocidas; consultar siempre su completitud. El P90 de esta tabla es la media de P90 por corrida, no el P90 de todos los incidentes agrupados.",
              "El porcentaje <=8 min se guarda con dos denominadores: respondedores y todas las llegadas. El segundo es una cota inferior si hay respuestas desconocidas.",
              "La utilizacion recorta intervalos ocupados a las 24 horas medidas; no incluye el tiempo de vaciado en el denominador.",
              "", "## Figuras", ""]
    for item in interpretations:
        lines += [f"### {item['title']}", "", item["interpretation"], "",
                  f"![{item['title']}](figures/{item['artifact']}.png)", "", f"Limite: {item['limitation']}", ""]
    lines += ["## Tablas y procedencia", "",
              "- scenario_matrix.csv: rejilla congelada antes de ejecutar.",
              "- tables/run_metrics.csv: resultados sin redondear por corrida y corte.",
              "- tables/by_zone_metrics.csv: resultados por borough.",
              "- tables/paired_differences.csv: diferencias descriptivas pareadas, sin pruebas inferenciales.",
              "- tables/scenario_summary.csv: promedios por escenario y politica, con numero de replicas.",
              "- tables/historical_fleet_summary.csv: resumen de flota, solo llegadas historicas.",
              "- pairs/: JSON por par y Parquet por incidente, incluidos casos de calentamiento.",
              "- manifest.json: codigo/entradas/entorno y hashes que se verifican al reanudar.", "",
              "## Limites", "", *[f"- {text}" for text in config["limitations"]],
              "- El vaciado conserva el pronostico de la ultima hora anterior al corte; no incorpora informacion futura.",
              "- La politica predictiva sigue siendo v1, sin reubicacion preventiva. Su ampliacion pertenece a 8E.",
              "- La inferencia temporal/estadistica final sigue pendiente de 8F; la integracion en pantallas pertenece a 8G."]
    (output / "SENSITIVITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    render_report(parser.parse_args().batch)
