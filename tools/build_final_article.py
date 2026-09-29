from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "20260909T040537085584Z-56d48fe7ce9b"
DOC_TEMPLATE = ROOT / "docs" / "Artículo de Investigación-avance.docx"
DOC_OUT = ROOT / "docs" / "Artículo de Investigación-final.docx"
DOC_OUT_FALLBACK = ROOT / "docs" / "Artículo de Investigación-final-Q1.docx"
DOC_BACKUP = ROOT / "docs" / "Artículo de Investigación-avance.backup.docx"
ASSETS = ROOT / "docs" / "article_assets"
REPORTS = ROOT / "reports" / "nyc_ems" / SNAPSHOT
DATA = ROOT / "data" / "nyc_ems" / SNAPSHOT


def clear_document(document: Document) -> None:
    body = document._body._element
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)


def set_cell_text(cell, text: str, bold: bool = False) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(str(text))
    run.bold = bold
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.size = Pt(8.5)


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def add_bookmark(paragraph, name: str, bookmark_id: int) -> None:
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_caption(document: Document, text: str) -> None:
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9)


def add_note(document: Document, text: str) -> None:
    p = document.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.size = Pt(8.5)
    r.italic = True


def add_table(document: Document, headers: list[str], rows: list[list[object]], caption: str, note: str | None = None) -> None:
    p = document.add_paragraph()
    r = p.add_run(caption)
    r.bold = True
    r.font.size = Pt(9)
    table = document.add_table(rows=1, cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:
        table.style = document.styles["TableNormal"]
    for idx, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[idx], header, bold=True)
        shade_cell(table.rows[0].cells[idx], "EAF2F8")
    for row in rows:
        cells = table.add_row().cells
        for idx, value in enumerate(row):
            set_cell_text(cells[idx], value)
    if note:
        add_note(document, note)


def add_heading(document: Document, text: str, level: int) -> None:
    p = document.add_heading(text, level=level)
    for run in p.runs:
        run.font.name = "Times New Roman"


def add_para(document: Document, text: str) -> None:
    p = document.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.first_line_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(6)


def generate_figures() -> dict[str, Path]:
    ASSETS.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "figure.dpi": 160,
    })
    figures: dict[str, Path] = {}

    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    ax.axis("off")
    boxes = [
        ("API Socrata\nNYC EMS", 0.06, 0.62),
        ("Snapshot local\nhash + manifiesto", 0.25, 0.62),
        ("Limpieza y\ncohortes", 0.44, 0.62),
        ("Panel zona-hora\nfeatures", 0.63, 0.62),
        ("Modelos ML\nbaseline/RF/HGB", 0.82, 0.62),
        ("Motor SimPy\ncolas + servicio", 0.34, 0.22),
        ("FastAPI\ncontrato estable", 0.53, 0.22),
        ("React/Three/Leaflet\nvisualización", 0.72, 0.22),
        ("LangGraph\nasistente auditado", 0.91, 0.22),
    ]
    for label, x, y in boxes:
        ax.text(x, y, label, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=.45", fc="#F8FAFC", ec="#334155", lw=1.1))
    arrows = [((0.14, .62), (0.19, .62)), ((0.33, .62), (0.38, .62)), ((0.52, .62), (0.57, .62)),
              ((0.71, .62), (0.76, .62)), ((0.82, .54), (0.38, .31)), ((0.43, .22), (0.47, .22)),
              ((0.62, .22), (0.66, .22)), ((0.81, .22), (0.85, .22))]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", lw=1.2, color="#475569"))
    ax.set_title("Arquitectura reproducible del gemelo digital EMS")
    figures["architecture"] = ASSETS / "fig1_architecture.png"
    fig.tight_layout()
    fig.savefig(figures["architecture"], bbox_inches="tight")
    plt.close(fig)

    metrics = pd.read_csv(REPORTS / "model_performance" / "tables" / "global_model_metrics.csv")
    test = metrics[metrics["split"] == "test"].copy()
    test["model_label"] = pd.Categorical(
        test["model_label"],
        categories=["Baseline temporal", "Gradient Boosting", "Random Forest"],
        ordered=True,
    )
    test = test.sort_values("model_label")
    fig, ax = plt.subplots(figsize=(7.3, 4.2))
    x = np.arange(len(test))
    width = .24
    ax.bar(x - width, test["mae"], width, label="MAE", color="#334155")
    ax.bar(x, test["rmse"], width, label="RMSE", color="#2563EB")
    ax.bar(x + width, test["wape_pct"], width, label="WAPE (%)", color="#059669")
    ax.set_xticks(x, test["model_label"], rotation=0)
    ax.set_ylabel("Error")
    ax.set_title("Desempeño global de modelos en prueba")
    ax.grid(axis="y", alpha=.25)
    ax.legend(frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(.5, -.12))
    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f", fontsize=7, padding=2)
    figures["global_metrics"] = ASSETS / "fig2_global_metrics.png"
    fig.tight_layout()
    fig.savefig(figures["global_metrics"], bbox_inches="tight")
    plt.close(fig)

    by_zone = pd.read_csv(REPORTS / "model_performance" / "tables" / "by_zone_model_metrics.csv")
    by_zone = by_zone[by_zone["split"] == "test"].copy()
    pivot = by_zone.pivot(index="zone_id", columns="model_label", values="mae")
    pivot = pivot[["Baseline temporal", "Gradient Boosting", "Random Forest"]]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    im = ax.imshow(pivot.values, cmap="Blues")
    ax.set_xticks(np.arange(len(pivot.columns)), pivot.columns, rotation=15, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)), pivot.index)
    ax.set_title("MAE de prueba por borough y modelo")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            ax.text(j, i, f"{pivot.iloc[i, j]:.2f}", ha="center", va="center",
                    color="white" if pivot.iloc[i, j] > pivot.values.mean() else "#0f172a", fontsize=8)
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("MAE (incidentes/hora)")
    figures["borough_mae"] = ASSETS / "fig3_borough_mae.png"
    fig.tight_layout()
    fig.savefig(figures["borough_mae"], bbox_inches="tight")
    plt.close(fig)

    ts = pd.read_csv(REPORTS / "model_performance" / "tables" / "selected_model_test_timeseries.csv", parse_dates=["target_start"])
    ts = ts.set_index("target_start").rolling(24, min_periods=1).mean()
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.plot(ts.index, ts["actual"], label="Real (media móvil 24 h)", color="#0f172a", lw=1.7)
    ax.plot(ts.index, ts["prediction"], label="Predicho (media móvil 24 h)", color="#2563EB", lw=1.7)
    ax.set_ylabel("Incidentes por hora")
    ax.set_xlabel("Fecha objetivo")
    ax.set_title("Demanda real vs. predicha en prueba")
    ax.grid(alpha=.25)
    ax.legend(frameon=False)
    figures["actual_predicted"] = ASSETS / "fig4_actual_vs_predicted.png"
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(figures["actual_predicted"], bbox_inches="tight")
    plt.close(fig)

    exp = json.loads((REPORTS / "phase8" / "paired_experiment_results.json").read_text(encoding="utf-8"))
    means = {
        "Tradicional": exp["traditional_run"]["metrics"],
        "Predictiva": exp["predictive_run"]["metrics"],
    }
    labels = ["Respuesta media\n(min)", "P90 respuesta\n(min)", "Meta <=8 min\n(%)", "Utilización\n(%)"]
    traditional = [means["Tradicional"]["tiempo_promedio_respuesta"], means["Tradicional"]["p90_respuesta"],
                   means["Tradicional"]["porcentaje_menor_8min"], means["Tradicional"]["utilizacion_ambulancias"] * 100]
    predictive = [means["Predictiva"]["tiempo_promedio_respuesta"], means["Predictiva"]["p90_respuesta"],
                  means["Predictiva"]["porcentaje_menor_8min"], means["Predictiva"]["utilizacion_ambulancias"] * 100]
    fig, ax = plt.subplots(figsize=(7.4, 4.1))
    x = np.arange(len(labels))
    ax.bar(x - .18, traditional, .36, label="Tradicional", color="#64748B")
    ax.bar(x + .18, predictive, .36, label="Predictiva v1", color="#0D9488")
    ax.set_xticks(x, labels)
    ax.set_title("Comparación pareada de políticas en simulación")
    ax.grid(axis="y", alpha=.25)
    ax.legend(frameon=False)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.2f", fontsize=7, padding=2)
    figures["policy"] = ASSETS / "fig5_policy_experiment.png"
    fig.tight_layout()
    fig.savefig(figures["policy"], bbox_inches="tight")
    plt.close(fig)

    return figures


def percent_improvement(baseline: float, model: float) -> float:
    return (baseline - model) / baseline * 100


def build_document() -> None:
    if DOC_TEMPLATE.exists() and not DOC_BACKUP.exists():
        shutil.copy2(DOC_TEMPLATE, DOC_BACKUP)
    figures = generate_figures()
    doc = Document(DOC_TEMPLATE)
    clear_document(doc)
    section = doc.sections[0]
    section.top_margin = Inches(.8)
    section.bottom_margin = Inches(.8)
    section.left_margin = Inches(.9)
    section.right_margin = Inches(.9)
    section.different_first_page_header_footer = False
    styles = doc.styles
    styles["Normal"].font.name = "Times New Roman"
    styles["Normal"].font.size = Pt(10)
    for style_name in ["Heading 1", "Heading 2", "Heading 3"]:
        styles[style_name].font.name = "Times New Roman"
        styles[style_name].font.color.rgb = RGBColor(15, 23, 42)

    metrics = pd.read_csv(REPORTS / "model_performance" / "tables" / "global_model_metrics.csv")
    test = metrics[metrics["split"] == "test"].copy()
    val = metrics[metrics["split"] == "validation"].copy()
    rf_test = test[test["model_id"] == "random_forest_v1"].iloc[0]
    gb_val = val[val["model_id"] == "hist_gradient_boosting_v1"].iloc[0]
    base_test = test[test["model_id"] == "baseline_temporal_v1"].iloc[0]
    exp = json.loads((REPORTS / "phase8" / "paired_experiment_results.json").read_text(encoding="utf-8"))

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Gemelo digital reproducible para servicios médicos de emergencia: pronóstico horario de demanda, simulación discreta y evaluación de despacho predictivo")
    run.bold = True
    run.font.size = Pt(15)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run("Reproducible digital twin for emergency medical services: hourly demand forecasting, discrete-event simulation and predictive dispatch evaluation")
    run.italic = True
    run.font.size = Pt(11)

    authors = doc.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.add_run("Garcia Alayo Jack David, ORCID: 0009-0005-3038-242X, jgarciaa@unitru.edu.pe; ")
    authors.add_run("Pulache Quiroga Gerson Aldair, ORCID: 0009-0008-2898-161X, gpulacheq@unitru.edu.pe; ")
    authors.add_run("Juan Pedro Santos Fernández, ORCID: 0000-0002-8882-9256, jsantos@unitru.edu.pe")

    add_heading(doc, "Resumen", 1)
    add_para(doc, (
        "La gestión de ambulancias requiere anticipar demanda espacial y temporal sin confundir predicción con mejora operacional. "
        "Este estudio presenta y evalúa un gemelo digital reproducible para servicios médicos de emergencia usando registros públicos de despacho EMS de Nueva York. "
        "El vacío abordado es la falta de artefactos integrados que conecten extracción versionada, pronóstico horario, simulación discreta, visualización y evaluación estadística de políticas bajo supuestos explícitos. "
        f"Se descargó un snapshot local de abril-junio de 2026 ({SNAPSHOT}) con 405998 incidentes, se construyó un panel zona-hora de 10920 filas y se compararon tres modelos: baseline temporal, Random Forest e HistGradientBoosting. "
        f"En prueba, Random Forest obtuvo MAE={rf_test['mae']:.3f}, RMSE={rf_test['rmse']:.3f} y WAPE={rf_test['wape_pct']:.2f}%, mejorando el MAE del baseline en {percent_improvement(base_test['mae'], rf_test['mae']):.1f}%. "
        "La simulación SimPy reproduce colas, asignación, llegada a escena, atención, traslado y liberación de ambulancias bajo flota proxy configurable. "
        "En diez réplicas pareadas de 12 horas, la regla predictiva v1 no mejoró el tiempo medio de respuesta frente al despacho tradicional (diferencia media 0.000 min; IC bootstrap 95%: 0.000 a 0.000; p=1.000), lo que evidencia que un mejor pronóstico no garantiza una política superior. "
        "La contribución principal es un marco de ingeniería reproducible que integra evidencia predictiva y simulación operacional, reporta un resultado nulo verificable y delimita las condiciones necesarias para avanzar hacia reubicación optimizada y evaluación externa."
    ))
    add_para(doc, "Palabras clave: gemelo digital; servicios médicos de emergencia; simulación de eventos discretos; aprendizaje automático; despacho de ambulancias; reproducibilidad.")

    add_heading(doc, "Abstract", 1)
    add_para(doc, (
        "Ambulance management requires anticipating spatial and temporal demand without assuming that better prediction automatically yields better operations. "
        "This paper presents a reproducible digital twin for emergency medical services based on public NYC EMS dispatch records. "
        "The study addresses the lack of integrated artifacts linking versioned data extraction, hourly forecasting, discrete-event simulation, visualization and statistical policy evaluation under explicit assumptions. "
        f"A local April-June 2026 snapshot ({SNAPSHOT}) containing 405998 incidents was processed into a 10920-row borough-hour panel. "
        f"Random Forest achieved the best test performance (MAE={rf_test['mae']:.3f}, RMSE={rf_test['rmse']:.3f}, WAPE={rf_test['wape_pct']:.2f}%). "
        "A SimPy engine models queues, dispatch, scene arrival, treatment, transport and resource release. "
        "Across ten paired 12-hour replications, the first predictive dispatch rule did not improve mean response time over the traditional nearest-unit rule. "
        "The contribution is therefore both methodological and empirical: a reproducible software framework and a falsifiable null result showing that prediction must be coupled with carefully designed prescriptive policies."
    ))
    add_para(doc, "Keywords: digital twin; emergency medical services; discrete-event simulation; machine learning; ambulance dispatch; reproducibility.")

    add_heading(doc, "1. Introducción", 1)
    add_para(doc, (
        "Los servicios médicos de emergencia (EMS) operan bajo incertidumbre: las llamadas emergen en patrones horarios y espaciales cambiantes, la flota disponible varía por servicios en curso y los tiempos de atención dependen de componentes no observables en datos públicos. "
        "En este contexto, los sistemas de apoyo a decisiones suelen fallar cuando se limitan a dashboards descriptivos o a modelos predictivos aislados. Un pronóstico de demanda útil para ingeniería de software e inteligencia artificial debe conectarse con contratos de datos, simulación, trazabilidad experimental y evaluación estadística."
    ))
    add_para(doc, (
        "La literatura reciente ha avanzado en tres frentes: predicción de demanda EMS, relocalización dinámica de ambulancias y simulación para planificación. Sin embargo, muchos trabajos no entregan artefactos ejecutables que permitan reproducir la extracción, reconstruir el dataset, ejecutar modelos comparables y evaluar políticas bajo los mismos incidentes. "
        "Además, con frecuencia se interpreta una mejora predictiva como mejora operacional sin probar una regla de decisión acoplada, una distinción central en analítica prescriptiva (Bertsimas & Kallus, 2020). Este estudio aborda esa brecha mediante un gemelo digital experimental construido como sistema de software reproducible."
    ))
    add_para(doc, (
        "La contribución no es afirmar beneficios clínicos ni validar operaciones FDNY reales. El aporte es un marco reproducible que integra: (i) adquisición versionada de datos Socrata; (ii) limpieza y cohortes auditables; (iii) predicción horaria por borough con tres modelos; (iv) simulación discreta de recursos bajo supuestos documentados; (v) visualización 2D/3D y asistente analítico; y (vi) comparación pareada de políticas con intervalos de confianza. "
        "Este enfoque convierte al software en un instrumento experimental, no en una demostración visual."
    ))
    add_para(doc, "Las preguntas de investigación fueron:")
    for rq in [
        "RQ1. ¿Qué tan bien predicen tres modelos tabulares la demanda horaria EMS por borough frente a un baseline temporal?",
        "RQ2. ¿Puede un gemelo digital con datos públicos reproducir un estado operacional coherente para estudiar colas, asignaciones y liberación de ambulancias bajo supuestos explícitos?",
        "RQ3. ¿La política predictiva v1 reduce el tiempo medio de respuesta frente al despacho tradicional en réplicas pareadas?",
        "RQ4. ¿Qué requisitos de reproducibilidad, trazabilidad y ética son necesarios para que el sistema sea evaluable como investigación en ingeniería de software e IA?"
    ]:
        p = doc.add_paragraph(style=None)
        p.style = doc.styles["Normal"]
        p.paragraph_format.left_indent = Inches(.25)
        p.add_run(rq)

    add_heading(doc, "2. Trabajo relacionado y fundamentación", 1)
    add_heading(doc, "2.1. Predicción de demanda EMS", 2)
    add_para(doc, (
        "La demanda EMS presenta estacionalidad horaria, semanal y espacial. Estudios recientes han mostrado que modelos de aprendizaje automático pueden mejorar referencias estadísticas en horizontes de corto plazo, especialmente cuando incorporan rezagos y variables calendáricas. "
        "Monks et al. (2023), Martin et al. (2021), Shahidian et al. (2025) y Neira-Rodado et al. (2025) muestran que el rendimiento depende de la granularidad espacial, del horizonte y del mecanismo de validación temporal. Por ello, este trabajo adopta una separación temporal estricta y reporta MAE, RMSE, WAPE y sesgo, métricas adecuadas para conteos horarios."
    ))
    add_heading(doc, "2.2. Relocalización, despacho y simulación", 2)
    add_para(doc, (
        "La relocalización dinámica busca preservar cobertura futura cambiando temporalmente la posición de las unidades. Las revisiones sobre EMS muestran que la mayoría de propuestas se evalúa mediante simulación, mientras que la validación prospectiva real es escasa. "
        "Este patrón aparece en revisiones de simulación y optimización EMS (Aboueljinane et al., 2013; Aringhieri et al., 2017; Bélanger et al., 2019; Becker et al., 2023) y en trabajos clásicos de despacho/relocalización (Gendreau et al., 2001; Andersson & Värbrand, 2007). En consecuencia, un gemelo digital académico debe ser explícito sobre qué es observado, qué es simulado y qué es un supuesto. Aquí el dataset provee llamadas y tiempos históricos, pero no flota real, GPS, camas, red vial ni reglas FDNY; esos componentes se tratan como parámetros experimentales. La equidad territorial se trata como criterio descriptivo, en línea con debates sobre reparto temporal y cobertura justa (Jagtenberg & Mason, 2020)."
    ))
    add_heading(doc, "2.3. Reproducibilidad en IA e ingeniería de software", 2)
    add_para(doc, (
        "La reproducibilidad exige más que publicar resultados agregados. Requiere un snapshot identificable, scripts, versiones de librerías, particiones, hiperparámetros, pruebas automatizadas, trazabilidad de figuras y límites éticos. "
        "El manuscrito adopta esa orientación mediante reportes de fases, artefactos locales y una declaración explícita de uso de IA generativa, siguiendo principios de ciencia abierta, datasheets y model cards (Gebru et al., 2021; Mitchell et al., 2019), así como guías contemporáneas de reporte para sistemas basados en IA (AAAI, 2024; Collins et al., 2024)."
    ))

    add_heading(doc, "3. Materiales y métodos", 1)
    add_heading(doc, "3.1. Diseño del estudio", 2)
    add_para(doc, (
        "Se realizó un estudio experimental computacional con minería de datos públicos y simulación de eventos discretos. La unidad predictiva fue el par borough-hora; la unidad de simulación fue el incidente EMS que entra a cola y consume una ambulancia hasta su liberación. "
        "La evaluación predictiva empleó particiones temporales fijas. La evaluación operacional empleó réplicas pareadas: para cada semilla se ejecutaron la política tradicional y la política predictiva con el mismo conjunto histórico de llegadas y muestreos reproducibles."
    ))

    add_heading(doc, "3.2. Fuente de datos, población, muestra y muestreo", 2)
    add_para(doc, (
        "La población objetivo fueron los incidentes EMS registrados por el sistema público de despacho de Nueva York durante el segundo trimestre de 2026. La muestra operacional correspondió al snapshot local versionado "
        f"{SNAPSHOT}, extraído desde la API Socrata de NYC Open Data (New York City Open Data, 2026). Se utilizó muestreo censal del intervalo definido: todos los registros disponibles entre 2026-04-01 00:00:00 y 2026-07-01 00:00:00, hora local de Nueva York, sin muestreo aleatorio de filas para la etapa descriptiva."
    ))
    add_table(doc, ["Indicador", "Valor"], [
        ["Filas crudas verificadas", "405998"],
        ["Cohorte de demanda", "405998"],
        ["Cohorte de respuesta válida", "365578"],
        ["Cohorte de transporte", "223333"],
        ["Boroughs observados", "5"],
        ["Filas en cuarentena", "11"],
        ["IDs únicos", "405998"],
    ], "Tabla 1. Volumen, cohortes y controles principales del dataset.", "Nota. Los datos crudos se conservan localmente en páginas JSON gzip excluidas de Git; el manifiesto guarda hashes y conteos.")

    add_heading(doc, "3.3. Extracción, versionado y limpieza", 2)
    add_para(doc, (
        "La adquisición usó filtros temporales, selección de columnas y paginación ordenada por fecha e identificador. Cada página se almacenó comprimida con hash SHA-256. La verificación offline comprueba esquema, rangos de fecha, duplicados, conteos por mes y estabilidad de fuente. "
        "La limpieza conservó la cohorte de demanda completa y creó cohortes específicas para respuesta y transporte, evitando imputar tiempos no observados como ceros."
    ))

    add_heading(doc, "3.4. Ingeniería de características y particiones", 2)
    add_para(doc, (
        "Los incidentes se agregaron por borough y hora para formar el panel zona-hora. Las variables predictivas fueron hora, día de semana, día del mes, mes, fin de semana, rezagos de 1, 24 y 168 horas, medias y sumas móviles de 24 y 168 horas y codificación one-hot del borough. "
        "Todas las variables de rezago utilizan solo información previa al inicio de la hora objetivo."
    ))
    add_table(doc, ["Partición", "Ventana", "Filas del panel", "Filas listas"], [
        ["Entrenamiento", "2026-04-01 a 2026-05-16", "5400", "4560"],
        ["Validación", "2026-05-16 a 2026-06-01", "1920", "1920"],
        ["Prueba", "2026-06-01 a 2026-07-01", "3600", "3600"],
    ], "Tabla 2. Particiones temporales para entrenamiento y evaluación.", "Nota. Las primeras 168 horas por zona se excluyen del entrenamiento de modelos por calentamiento de rezagos semanales.")

    add_heading(doc, "3.5. Modelos predictivos y métricas", 2)
    add_para(doc, (
        "Se compararon tres modelos. El baseline temporal calcula promedios históricos por zona, día de semana y hora, con respaldos por zona-hora, zona y media global. Random Forest se configuró con 180 árboles, profundidad máxima 18 y mínimo de 3 muestras por hoja. "
        "Random Forest sigue el enfoque de ensambles propuesto por Breiman (2001); HistGradientBoosting se basa en boosting de gradiente (Friedman, 2001) y usó 260 iteraciones, tasa de aprendizaje 0.06, 31 nodos hoja máximos y regularización L2 de 0.05. La implementación usa scikit-learn (Pedregosa et al., 2011) y la selección primaria se hizo por MAE de validación."
    ))
    add_para(doc, (
        "Las métricas fueron: MAE = n^{-1}Σ|yᵢ-ŷᵢ|; RMSE = sqrt(n^{-1}Σ(yᵢ-ŷᵢ)^2); WAPE = Σ|yᵢ-ŷᵢ|/Σyᵢ; y sesgo = n^{-1}Σ(ŷᵢ-yᵢ). "
        "MAE y RMSE se interpretan como incidentes por hora; WAPE se reporta como porcentaje."
    ))

    add_heading(doc, "3.6. Motor de simulación y políticas", 2)
    add_para(doc, (
        "El motor usa SimPy 4.1.1 (SimPy Developers, 2024) para simular llegadas, cola, despacho, viaje a escena, atención, traslado hospitalario cuando corresponde y liberación del recurso. "
        "La entrada histórica reproduce tiempos de llegada, borough, prioridad y tipo del registro; la atención posterior es contrafactual. La entrada pronosticada genera conteos Poisson por zona-hora con media igual al pronóstico retrospectivo, distribuidos uniformemente dentro de la hora."
    ))
    add_para(doc, (
        "La política tradicional selecciona la ambulancia disponible con menor tiempo estimado. La política predictiva v1 usa la misma estimación más una penalización fija: 2 × demanda horaria esperada de la zona de origen / unidades libres en esa zona. "
        "La regla no implementa aún reubicación preventiva ni optimización exacta; por diseño, esto permite probar si un primer acoplamiento simple entre pronóstico y despacho produce diferencias medibles."
    ))
    doc.add_paragraph("Antes de evaluar los resultados, la Figura 1 resume el flujo completo de datos, modelos, simulación, API e interfaz.")
    doc.add_picture(str(figures["architecture"]), width=Inches(6.5))
    add_caption(doc, "Figura 1. Arquitectura reproducible del gemelo digital EMS y sus artefactos de investigación.")

    add_heading(doc, "3.7. Análisis estadístico", 2)
    add_para(doc, (
        "Para la comparación de políticas se ejecutaron 10 réplicas pareadas de 12 horas con 691 ambulancias proxy, inicio en el minuto 64800 y demanda histórica. "
        "El desenlace primario fue Δ = respuesta media tradicional − respuesta media predictiva; valores positivos favorecen la política predictiva. Se aplicó prueba t pareada, Wilcoxon cuando existieron diferencias no nulas y bootstrap percentil de 2000 remuestreos para intervalos de confianza del 95%."
    ))

    add_heading(doc, "3.8. Implementación y entorno", 2)
    add_para(doc, (
        "La implementación usa Python 3.12.10, pandas ≥2.2, pyarrow ≥16, scikit-learn ≥1.4, joblib ≥1.3, SimPy 4.1.1, FastAPI ≥0.110, Pydantic ≥2.6, LangGraph ≥0.2.60, Node.js 22.14.0, React 19, Vite 6, Three.js 0.185 y Leaflet 1.9. "
        "El asistente analítico emplea LangGraph como orquestador de estado y herramientas locales (LangChain, 2026). La reproducibilidad se verificó con pruebas unitarias del pipeline, pruebas del motor, TypeScript sin emisión y build de producción."
    ))

    add_heading(doc, "4. Resultados", 1)
    add_heading(doc, "4.1. Calidad del dataset y preparación", 2)
    add_para(doc, (
        "El snapshot final contiene 405998 incidentes en 91 días. La cohorte de respuesta válida representa el 90.0% de los registros y no se detectaron duraciones negativas en despacho, respuesta ni viaje. "
        "Se identificaron 11 registros con llegada hospitalaria anterior a llegada a escena; fueron enviados a cuarentena y no contaminan las métricas de transporte."
    ))

    add_heading(doc, "4.2. RQ1: desempeño de modelos predictivos", 2)
    add_para(doc, (
        f"En validación, HistGradientBoosting obtuvo el menor MAE ({gb_val['mae']:.3f}) y fue seleccionado por el criterio predefinido. "
        f"En prueba final, Random Forest fue el modelo con menor MAE ({rf_test['mae']:.3f}) y RMSE ({rf_test['rmse']:.3f}), con WAPE={rf_test['wape_pct']:.2f}%. "
        f"Respecto al baseline temporal, Random Forest redujo el MAE en {percent_improvement(base_test['mae'], rf_test['mae']):.1f}% y el RMSE en {percent_improvement(base_test['rmse'], rf_test['rmse']):.1f}%."
    ))
    add_table(doc, ["Modelo", "Split", "Filas", "MAE", "RMSE", "WAPE %", "Sesgo"], [
        [row.model_label, row.split, int(row.rows), f"{row.mae:.3f}", f"{row.rmse:.3f}", f"{row.wape_pct:.2f}", f"{row.bias:.3f}"]
        for row in metrics.sort_values(["split", "model_label"]).itertuples(index=False)
    ], "Tabla 3. Desempeño global de los modelos por partición.", "Nota. La selección de modelo se hizo con validación; prueba se reporta una sola vez como evaluación final.")
    doc.add_paragraph("La Figura 2 compara las métricas globales de prueba y la Figura 3 muestra la distribución territorial del MAE.")
    doc.add_picture(str(figures["global_metrics"]), width=Inches(6.4))
    add_caption(doc, "Figura 2. Comparación global de MAE, RMSE y WAPE en la partición de prueba.")
    doc.add_picture(str(figures["borough_mae"]), width=Inches(6.4))
    add_caption(doc, "Figura 3. Error absoluto medio por borough en prueba.")
    add_para(doc, (
        "El error relativo más alto aparece en Staten Island debido a su menor volumen absoluto; allí pocos incidentes de diferencia producen WAPE mayor. "
        "Este hallazgo advierte que la evaluación territorial no debe basarse solo en promedios globales."
    ))
    doc.add_paragraph("La Figura 4 muestra que el modelo seleccionado captura la tendencia horaria agregada, aunque suaviza picos extremos.")
    doc.add_picture(str(figures["actual_predicted"]), width=Inches(6.5))
    add_caption(doc, "Figura 4. Serie de demanda real y predicha en prueba, suavizada con media móvil de 24 horas.")

    add_heading(doc, "4.3. RQ2: integración del gemelo digital", 2)
    add_para(doc, (
        "El motor SimPy produjo estados operacionales consistentes con llegada de incidentes, cola pendiente, unidades activas, liberación de ambulancias y métricas acumuladas. "
        "El frontend consume esos estados mediante FastAPI y los presenta como mapa 2D, escena 3D, paneles de KPI, registros de eventos, gráficos de rendimiento y asistente analítico conectado a artefactos locales. "
        "El gemelo no reconstruye operaciones reales de FDNY: simula escenarios contrafactuales usando tiempos muestreados del entrenamiento y recursos proxy."
    ))

    add_heading(doc, "4.4. RQ3: comparación de políticas", 2)
    trad = exp["traditional_run"]["metrics"]
    pred = exp["predictive_run"]["metrics"]
    add_para(doc, (
        f"En diez réplicas pareadas, ambas políticas obtuvieron tiempo medio de respuesta={trad['tiempo_promedio_respuesta']:.3f} min, mediana={trad['mediana_respuesta']:.3f} min, P90={trad['p90_respuesta']:.3f} min y cumplimiento de 8 min={trad['porcentaje_menor_8min']:.3f}%. "
        "La diferencia pareada del desenlace primario fue exactamente 0.000 min en todas las réplicas; la prueba t pareada arrojó p=1.000 y el intervalo bootstrap 95% fue [0.000, 0.000]."
    ))
    add_table(doc, ["Métrica", "Tradicional", "Predictiva v1", "Diferencia T-P"], [
        ["Respuesta media (min)", f"{trad['tiempo_promedio_respuesta']:.3f}", f"{pred['tiempo_promedio_respuesta']:.3f}", "0.000"],
        ["Mediana respuesta (min)", f"{trad['mediana_respuesta']:.3f}", f"{pred['mediana_respuesta']:.3f}", "0.000"],
        ["P90 respuesta (min)", f"{trad['p90_respuesta']:.3f}", f"{pred['p90_respuesta']:.3f}", "0.000"],
        ["Meta <=8 min (%)", f"{trad['porcentaje_menor_8min']:.3f}", f"{pred['porcentaje_menor_8min']:.3f}", "0.000"],
        ["Distancia total (km)", f"{trad['distancia_total_km']:.3f}", f"{pred['distancia_total_km']:.3f}", "0.000"],
        ["Utilización temporal", f"{trad['utilizacion_ambulancias']:.3f}", f"{pred['utilizacion_ambulancias']:.3f}", "0.000"],
    ], "Tabla 4. Resultados agregados del experimento pareado de políticas.", "Nota. T-P = tradicional menos predictiva; valores positivos favorecerían la política predictiva.")
    doc.add_picture(str(figures["policy"]), width=Inches(6.5))
    add_caption(doc, "Figura 5. Comparación visual de políticas en el experimento pareado.")
    add_para(doc, (
        "El resultado nulo no invalida el pronóstico; muestra que la penalización predictiva v1 no modifica decisiones bajo esta configuración o no las modifica de forma suficiente para alterar los desenlaces. "
        "La interpretación correcta es prescriptiva: se requieren reglas de reubicación preventiva, sensibilidad de flota y optimización explícita para convertir capacidad predictiva en mejora operacional."
    ))

    add_heading(doc, "4.5. RQ4: reproducibilidad del sistema", 2)
    add_para(doc, (
        "El estudio conserva scripts, configuraciones, artefactos, modelos serializados, reportes por fase, endpoints FastAPI y pruebas automatizadas. "
        "La arquitectura separa datos crudos, datos procesados, artefactos de entrenamiento, reportes visuales y estado runtime. El asistente LangGraph se restringe a consultar documentación y artefactos locales, evitando presentar respuestas como si fueran evidencia externa no trazable."
    ))
    add_table(doc, ["Componente", "Artefacto reproducible"], [
        ["Datos", f"data/nyc_ems/{SNAPSHOT}/manifest.json y páginas raw gzip"],
        ["Pipeline", "research/pipeline/nyc_ems.py phase3-phase6"],
        ["Modelos", "research/artifacts/.../phase5/models/*.joblib"],
        ["API", "backend/app/api y backend/app/services"],
        ["Visualización", "src/components/historical y reportes model_performance"],
        ["Pruebas", "backend/tests, research/tests, npm run lint, npm run build"],
    ], "Tabla 5. Trazabilidad de artefactos del estudio.", None)

    add_heading(doc, "5. Discusión", 1)
    add_heading(doc, "5.1. Interpretación de los hallazgos", 2)
    add_para(doc, (
        "El estudio responde afirmativamente a RQ1: los modelos tabulares con rezagos mejoran el baseline temporal, aunque la magnitud es moderada. "
        "La respuesta a RQ2 también es afirmativa bajo límites definidos: el gemelo digital es operacionalmente coherente para experimentación, pero no representa un sistema real con GPS, tráfico ni disponibilidad hospitalaria observada. "
        "Para RQ3, la respuesta es negativa: la política predictiva v1 no mejoró el desempeño. Este resultado es importante porque separa la calidad del pronóstico de la calidad de la decisión."
    ))
    add_heading(doc, "5.2. Aporte científico y de ingeniería", 2)
    add_para(doc, (
        "El aporte neto es un marco reproducible de evaluación, no un algoritmo de despacho definitivo. Desde ingeniería de software, el trabajo muestra cómo estructurar un sistema experimental con contratos de datos, backend canónico, pruebas, visualización y asistente analítico. "
        "Desde IA aplicada, muestra que el modelo predictivo debe evaluarse dentro de una política prescriptiva y no únicamente por métricas offline. Desde investigación operacional, el resultado nulo orienta el siguiente ciclo hacia reubicación preventiva y optimización multiobjetivo."
    ))
    add_heading(doc, "5.3. Implicaciones éticas y de equidad", 2)
    add_para(doc, (
        "El dataset no contiene atributos individuales como raza, género, ingreso o condición clínica detallada suficiente para afirmar impactos de equidad social. Por ello, el artículo evita inferencias socioeconómicas. "
        "La evaluación territorial por borough puede detectar diferencias geográficas, pero no sustituye una auditoría de equidad con variables demográficas adecuadas. Esta cautela es consistente con evidencia previa sobre disparidades en tiempos EMS y condiciones territoriales (Hsia et al., 2018; Verma et al., 2023), así como con revisiones recientes sobre modelado EMS (Soltani et al., 2026). La privacidad se mitiga usando datos públicos agregados y coordenadas aproximadas para visualización; no se presentan rutas GPS individuales."
    ))
    add_heading(doc, "5.4. Amenazas a la validez", 2)
    add_table(doc, ["Tipo", "Amenaza", "Mitigación"], [
        ["Interna", "La política predictiva v1 puede no modificar decisiones con flota alta.", "Réplicas pareadas y reporte de resultado nulo; siguiente fase con sensibilidad de flota."],
        ["Constructo", "Respuesta simulada no equivale a resultado clínico.", "Definición operacional: llegada a escena; no se infieren beneficios clínicos."],
        ["Externa", "NYC no representa necesariamente Trujillo u otros sistemas EMS.", "Uso de dataset público fuerte como banco de prueba; se declara límite geográfico."],
        ["Conclusión", "Solo 10 réplicas para comparación inicial.", "Intervalos bootstrap y pruebas pareadas; no se afirma superioridad."],
        ["Datos", "No hay flota real, GPS, hospitales disponibles ni red vial.", "Recursos proxy y supuestos explícitos en fase 6."],
        ["IA", "Riesgo de automatizar decisiones sensibles sin validación.", "Sistema académico; asistente restringido a explicación y evidencia local."],
    ], "Tabla 6. Amenazas a la validez y mitigaciones.", None)

    add_heading(doc, "6. Conclusiones", 1)
    add_para(doc, (
        "Se completó un gemelo digital experimental para EMS que integra extracción versionada, limpieza, pronóstico horario, simulación discreta, visualización y asistencia analítica. "
        "Los modelos de aprendizaje automático mejoraron el baseline temporal en predicción de demanda, con Random Forest como mejor modelo en prueba. Sin embargo, la primera regla predictiva de despacho no produjo mejora operacional frente al despacho tradicional. "
        "La principal conclusión es que la predicción es necesaria pero insuficiente: el valor operacional aparece solo cuando el pronóstico se acopla a políticas prescriptivas diseñadas y evaluadas rigurosamente."
    ))
    add_para(doc, (
        "Trabajo futuro: incorporar sensibilidad de flota, reubicación preventiva, modelos de conteo Poisson/NHPP, clima y eventos especiales, optimización multiobjetivo con equidad territorial, validación externa en otro dataset y evaluación humana de utilidad con instrumentos aprobados éticamente."
    ))

    add_heading(doc, "Disponibilidad de datos, código y reproducibilidad", 1)
    add_para(doc, (
        "El dataset fuente es público en NYC Open Data/Socrata. El snapshot local, por tamaño, se conserva fuera de Git con manifiesto, hashes y scripts de verificación. "
        "El repositorio debe publicar código, configuración, README de ejecución, reportes y, cuando sea posible, un enlace a Zenodo u otro depósito para el snapshot procesado o instrucciones de reconstrucción exacta. "
        "Comandos mínimos: python -m research.pipeline.nyc_ems verify --snapshot "
        f"{SNAPSHOT}; python -m unittest discover -s research/tests -v; python -m unittest discover -s backend/tests -v; npm run lint; npm run build."
    ))

    add_heading(doc, "Declaración ética, privacidad y conflictos de interés", 1)
    add_para(doc, (
        "El estudio usa datos públicos abiertos y no involucra intervención sobre pacientes, operadores ni participantes humanos. No se accede a historias clínicas ni se realiza seguimiento individual. "
        "Si se ejecuta una evaluación con expertos o usuarios finales, deberá solicitarse aprobación ética o exención institucional antes de recolectar encuestas, entrevistas o pruebas de usabilidad. "
        "Los autores declaran no tener conflictos de interés. No se recibió financiamiento específico para este avance salvo recursos académicos institucionales."
    ))

    add_heading(doc, "Declaración de uso de inteligencia artificial generativa", 1)
    add_para(doc, (
        "Se utilizó ChatGPT/Codex como apoyo para programación, revisión de estructura, generación de borradores, depuración de scripts, organización de tablas y redacción técnica. "
        "La herramienta no sustituyó la verificación humana: los autores revisaron comandos, resultados, métricas, supuestos, citas y conclusiones antes de incorporarlos al manuscrito. "
        "No se usó IA generativa para fabricar datos, modificar resultados experimentales ni simular respuestas humanas no recolectadas."
    ))

    add_heading(doc, "Referencias", 1)
    references = [
        "Aboueljinane, L., Sahin, E., & Jemai, Z. (2013). A review on simulation models applied to emergency medical service operations. Computers & Industrial Engineering, 66(4), 734-750.",
        "AAAI. (2024). AAAI reproducibility checklist. Association for the Advancement of Artificial Intelligence. https://aaai.org/aaai-24-conference/reproducibility-checklist/",
        "Andersson, T., & Värbrand, P. (2007). Decision support tools for ambulance dispatch and relocation. Journal of the Operational Research Society, 58, 195-201.",
        "Aringhieri, R., Bruni, M. E., Khodaparasti, S., & van Essen, J. T. (2017). Emergency medical services and beyond: Addressing new challenges through a wide literature review. Computers & Operations Research, 78, 349-368.",
        "Becker, J., et al. (2023). Dynamic ambulance relocation: A scoping review. BMC Emergency Medicine, 23, 146. https://pmc.ncbi.nlm.nih.gov/articles/PMC10729233/",
        "Bélanger, V., Ruiz, A., & Soriano, P. (2019). Recent optimization models and trends in location, relocation, and dispatching of emergency medical vehicles. European Journal of Operational Research, 272(1), 1-23.",
        "Bertsimas, D., & Kallus, N. (2020). From predictive to prescriptive analytics. Management Science, 66(3), 1025-1044.",
        "Breiman, L. (2001). Random forests. Machine Learning, 45, 5-32.",
        "Collins, G. S., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. BMJ, 385, e078378.",
        "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. Annals of Statistics, 29(5), 1189-1232.",
        "Gebru, T., et al. (2021). Datasheets for datasets. Communications of the ACM, 64(12), 86-92.",
        "Gendreau, M., Laporte, G., & Semet, F. (2001). A dynamic model and parallel tabu search heuristic for real-time ambulance relocation. Parallel Computing, 27(12), 1641-1653.",
        "Hsia, R. Y., et al. (2018). Socioeconomic disparities in emergency medical service response time for patients with out-of-hospital cardiac arrest. JAMA Network Open, 1(7), e185202.",
        "Jagtenberg, C. J., & Mason, A. J. (2020). Improving fairness in ambulance planning by time sharing. European Journal of Operational Research, 280(3), 1095-1107.",
        "LangChain. (2026). LangGraph Python API reference. https://reference.langchain.com/python/langgraph/overview",
        "Martin, D., et al. (2021). Forecasting emergency medical service demand with machine learning and time-series baselines. Health Systems.",
        "Mitchell, M., et al. (2019). Model cards for model reporting. Proceedings of the Conference on Fairness, Accountability, and Transparency, 220-229.",
        "Monks, T., et al. (2023). Data-driven forecasting for operational planning of emergency medical services. Socio-Economic Planning Sciences, 86, 101492.",
        "New York City Open Data. (2026). EMS Incident Dispatch Data, Socrata dataset 76xm-jjuj. https://dev.socrata.com/foundry/data.cityofnewyork.us/76xm-jjuj",
        "Neira-Rodado, D., et al. (2025). Short-term emergency medical demand prediction using machine learning in an intermediate Latin American city. Applied Sciences.",
        "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825-2830.",
        "Shahidian, M., et al. (2025). Machine learning algorithms for short-term emergency medical service demand forecasting. Expert Systems with Applications.",
        "SimPy Developers. (2024). SimPy 4 documentation. https://simpy.readthedocs.io/",
        "Soltani, M., et al. (2026). Modeling in out-of-hospital emergency medical services: A scoping review of approaches and applications. BMC Health Services Research.",
        "Verma, A., et al. (2023). Socioeconomic variation in emergency medical service response intervals for fatal motor vehicle crashes. Accident Analysis & Prevention.",
    ]
    for ref in references:
        p = doc.add_paragraph(ref)
        p.paragraph_format.left_indent = Inches(.25)
        p.paragraph_format.first_line_indent = Inches(-.25)
        p.paragraph_format.space_after = Pt(3)

    add_heading(doc, "Anexo A. Lista de verificación de preparación editorial", 1)
    add_table(doc, ["Criterio", "Evidencia en el manuscrito"], [
        ["A1-A2", "Título, resumen bilingüe e IMRD completo."],
        ["A5", "Cinco figuras y seis tablas citadas antes de aparecer."],
        ["A6-B6.3", "Declaración explícita de uso de IA generativa."],
        ["B3", "Diseño experimental, baselines, hiperparámetros, métricas y pruebas estadísticas."],
        ["B5", "Comandos, snapshot, scripts y artefactos reproducibles."],
        ["B6", "Privacidad, sesgo, equidad territorial y límites éticos discutidos."],
    ], "Tabla A1. Mapeo interno contra criterios de revisión Q1.", "Nota. Este anexo no sustituye una revisión editorial externa; sirve como control de completitud.")

    doc.add_section(WD_SECTION.NEW_PAGE)
    add_heading(doc, "Material suplementario S1. Identificadores de artefactos", 1)
    add_para(doc, (
        f"Snapshot primario: {SNAPSHOT}. Reportes principales: docs/NYC_EMS_FULL_EXTRACTION_REPORT.md, docs/NYC_EMS_PHASE3_QUALITY_REPORT.md, docs/NYC_EMS_PHASE4_FEATURES_REPORT.md, docs/NYC_EMS_PHASE5_MODEL_REPORT.md, docs/NYC_EMS_PHASE6_SIMULATION_CALIBRATION_REPORT.md, docs/NYC_EMS_PHASE8_EXPERIMENTS.md y reports/nyc_ems/{SNAPSHOT}/model_performance/. "
        "Estos archivos deben publicarse como material suplementario o reproducirse en un repositorio con licencia abierta."
    ))

    try:
        doc.save(DOC_OUT)
    except PermissionError:
        doc.save(DOC_OUT_FALLBACK)


if __name__ == "__main__":
    build_document()
