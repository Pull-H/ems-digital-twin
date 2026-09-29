from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "Artículo de Investigación-avance.docx"
OUTPUT = ROOT / "docs" / "Artículo de Investigación-final-v2.docx"
SNAPSHOT = "20260909T040537085584Z-56d48fe7ce9b"
REPORTS = ROOT / "reports" / "nyc_ems" / SNAPSHOT
ASSETS = ROOT / "docs" / "article_assets"


def insert_element_before_reference(doc: Document, element) -> None:
    ref = next(p for p in doc.paragraphs if p.text.strip() == "Referencias")
    ref._p.addprevious(element)


def move_last_body_element_before_reference(doc: Document) -> None:
    body = doc._body._element
    element = body[-1]
    if element.tag.endswith("sectPr"):
        element = body[-2]
    body.remove(element)
    insert_element_before_reference(doc, element)


def add_paragraph_before_refs(doc: Document, text: str = "", style: str | None = None, bold: bool = False) -> None:
    paragraph = doc.add_paragraph(style=style)
    if text:
        run = paragraph.add_run(text)
        run.bold = bold
    paragraph.paragraph_format.space_after = Pt(6)
    if style is None:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    move_last_body_element_before_reference(doc)


def add_heading_before_refs(doc: Document, text: str, level: int = 2) -> None:
    paragraph = doc.add_heading(text, level=level)
    paragraph.paragraph_format.space_before = Pt(10)
    paragraph.paragraph_format.space_after = Pt(6)
    move_last_body_element_before_reference(doc)


def add_picture_before_refs(doc: Document, path: Path, caption: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(6.2))
    move_last_body_element_before_reference(doc)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    run.italic = True
    run.font.size = Pt(9)
    move_last_body_element_before_reference(doc)


def add_table_before_refs(doc: Document, caption: str, headers: list[str], rows: list[list[str]], note: str | None = None) -> None:
    add_paragraph_before_refs(doc, caption, bold=True)
    table = doc.add_table(rows=1, cols=len(headers))
    try:
        table.style = "Table Grid"
    except KeyError:
        pass
    for i, header in enumerate(headers):
        table.rows[0].cells[i].text = header
        for run in table.rows[0].cells[i].paragraphs[0].runs:
            run.bold = True
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
    move_last_body_element_before_reference(doc)
    if note:
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(note)
        run.italic = True
        run.font.size = Pt(8.5)
        move_last_body_element_before_reference(doc)


def find_paragraph(doc: Document, text: str):
    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == text:
            return paragraph
    raise ValueError(f"No se encontro el parrafo: {text}")


def insert_after(paragraph, new_paragraph) -> None:
    paragraph._p.addnext(new_paragraph._p)


def insert_summary_after_heading(doc: Document) -> None:
    heading = find_paragraph(doc, "1. Resumen")
    summary_text = (
        "Resumen. Los servicios médicos de emergencia requieren anticipar demanda y evaluar políticas de despacho sin asumir que una mejora predictiva produce automáticamente una mejora operacional. "
        "Este estudio desarrolla un gemelo digital basado en simulación para analizar despacho predictivo y relocalización dinámica de ambulancias con datos históricos reales. "
        f"Se utiliza el dataset público EMS Incident Dispatch Data de Nueva York, con una extracción local versionada ({SNAPSHOT}) correspondiente a abril-junio de 2026 y 405 998 incidentes. "
        "La metodología integra limpieza y cohortes, construcción de un panel borough-hora, comparación de modelos predictivos, simulación de eventos discretos, visualización 2D/3D y evaluación instrumental mediante Aiken, Cronbach y KR-20 cuando se recojan datos de participantes. "
        "En la evaluación predictiva se comparan baseline temporal, Gradient Boosting y Random Forest; en prueba final Random Forest obtiene MAE = 5.557, RMSE = 7.501 y WAPE = 14.45 %. "
        "La simulación operacional muestra que la política predictiva v1 aún no mejora al despacho tradicional en diez réplicas pareadas de 12 horas (diferencia media = 0.000 min; p = 1.000), por lo que el aporte principal es un marco reproducible para convertir predicciones en experimentos de decisión auditables. "
        "El trabajo delimita explícitamente sus supuestos: no valida beneficios clínicos reales, no utiliza GPS operativo ni reconstruye el despacho FDNY; propone una base verificable para futuras políticas de reubicación optimizada."
    )
    keywords = "Palabras clave: gemelo digital; servicios médicos de emergencia; despacho predictivo; simulación de eventos discretos; aprendizaje automático; ambulancias."
    tmp_summary = doc.add_paragraph(summary_text)
    tmp_summary.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    tmp_keywords = doc.add_paragraph(keywords)
    summary_xml = copy.deepcopy(tmp_summary._p)
    keywords_xml = copy.deepcopy(tmp_keywords._p)
    body = doc._body._element
    for _ in range(2):
        element = body[-1]
        if element.tag.endswith("sectPr"):
            element = body[-2]
        body.remove(element)
    heading._p.addnext(keywords_xml)
    heading._p.addnext(summary_xml)


def preserve_references_snapshot(doc: Document) -> list[str]:
    refs: list[str] = []
    capture = False
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text == "Referencias":
            capture = True
            continue
        if capture and text:
            refs.append(text)
    return refs


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    shutil.copy2(SOURCE, OUTPUT)
    doc = Document(OUTPUT)
    original_refs = preserve_references_snapshot(doc)
    insert_summary_after_heading(doc)

    metrics = pd.read_csv(REPORTS / "model_performance" / "tables" / "global_model_metrics.csv")
    test = metrics[metrics["split"] == "test"].copy()
    rf = test[test["model_id"] == "random_forest_v1"].iloc[0]
    baseline = test[test["model_id"] == "baseline_temporal_v1"].iloc[0]
    gb = test[test["model_id"] == "hist_gradient_boosting_v1"].iloc[0]
    exp = json.loads((REPORTS / "phase8" / "paired_experiment_results.json").read_text(encoding="utf-8"))
    trad = exp["traditional_run"]["metrics"]
    pred = exp["predictive_run"]["metrics"]

    add_heading_before_refs(doc, "4.7. Integración metodológica bajo CRISP-DM", 3)
    add_paragraph_before_refs(doc, (
        "El desarrollo del software y el análisis experimental se organizan bajo CRISP-DM, adaptado al contexto de gemelos digitales para EMS. "
        "La comprensión del negocio corresponde a la definición del problema de investigación: anticipar demanda y evaluar si una política asistida por pronósticos modifica el desempeño del despacho. "
        "La comprensión de datos se refleja en el EDA, el perfilado de calidad, los conteos por borough, la revisión de faltantes y la separación de cohortes de demanda, respuesta y transporte. "
        "La preparación de datos incluye limpieza, particiones temporales, generación de rezagos, ventanas móviles y panel borough-hora."
    ))
    add_paragraph_before_refs(doc, (
        "La fase de modelado incluye entrenamiento de tres modelos, selección basada en validación, documentación de hiperparámetros y búsqueda ligera de candidatos. "
        "Debido a la naturaleza temporal del problema, la validación cruzada convencional aleatoria se reemplaza por validación temporal tipo rolling-origin, evitando que información futura ingrese al entrenamiento. "
        "La evaluación incluye métricas predictivas, pruebas estadísticas pareadas de errores absolutos, intervalos bootstrap y análisis de la política simulada. "
        "La fase de despliegue se expresa como prototipo académico: API, visualización 2D/3D, panel CRISP-DM, reportes exportables y asistente analítico."
    ))
    add_table_before_refs(doc, "Tabla 5. Correspondencia CRISP-DM en el software y el artículo.", ["Fase CRISP-DM", "Evidencia en el software", "Evidencia en el artículo"], [
        ["Comprensión del negocio", "Plan de implementación, contrato de simulación y objetivos EMS", "Problema, preguntas de investigación y aporte"],
        ["Comprensión de datos", "EDA, cohortes, conteos por borough, cuarentena", "Fuente de datos, población, muestra y criterios"],
        ["Preparación de datos", "Panel zona-hora, rezagos, ventanas móviles, particiones", "Ingeniería de variables y particiones temporales"],
        ["Modelado", "Baseline, Random Forest, Gradient Boosting, hiperparámetros", "Desarrollo y validación de modelos predictivos"],
        ["Evaluación", "Métricas, rolling-origin, pruebas estadísticas, interpretabilidad", "Resultados, discusión y amenazas a la validez"],
        ["Despliegue", "FastAPI, React, visualización 2D/3D, asistente LangGraph", "Reproducibilidad y disponibilidad"],
    ], "Nota. La validación cruzada se implementa como validación temporal rolling-origin, no como k-fold aleatorio, para prevenir fuga temporal.")

    add_heading_before_refs(doc, "5. Resultados", 2)
    add_paragraph_before_refs(doc, (
        "Esta sección complementa la metodología anterior con los resultados obtenidos por el software implementado. "
        "Se mantienen las advertencias ya descritas: los datos históricos permiten evaluar demanda, pronósticos y escenarios simulados, pero no prueban efectos clínicos reales ni equivalen a una operación con GPS en vivo."
    ))

    add_heading_before_refs(doc, "5.1. Preparación del dataset y cohortes", 3)
    add_paragraph_before_refs(doc, (
        "La extracción completa conserva 405 998 incidentes entre el 1 de abril y el 30 de junio de 2026. "
        "La cohorte de demanda retiene la totalidad de registros, la cohorte de respuesta válida conserva 365 578 registros y la cohorte de transporte conserva 223 333. "
        "Se identificaron 11 filas en cuarentena por inconsistencias temporales relacionadas con llegada hospitalaria anterior a llegada a escena. "
        "Estos controles permiten separar la predicción de demanda de la caracterización de tiempos, evitando convertir faltantes o banderas inválidas en ceros."
    ))
    add_table_before_refs(doc, "Tabla 6. Resumen de preparación y cohortes del dataset.", ["Indicador", "Valor"], [
        ["Filas crudas verificadas", "405 998"],
        ["Cohorte de demanda", "405 998"],
        ["Cohorte de respuesta válida", "365 578"],
        ["Cohorte de transporte", "223 333"],
        ["Boroughs utilizados", "5"],
        ["Filas en cuarentena", "11"],
        ["Ventana temporal", "2026-04-01 a 2026-07-01"],
    ], "Nota. Los originales permanecen versionados localmente; las cohortes se derivan de reglas documentadas en el pipeline.")

    add_heading_before_refs(doc, "5.2. Desempeño de modelos predictivos", 3)
    add_paragraph_before_refs(doc, (
        f"En prueba final, Random Forest obtiene el menor error global (MAE = {rf['mae']:.3f}, RMSE = {rf['rmse']:.3f}, WAPE = {rf['wape_pct']:.2f} %). "
        f"Gradient Boosting alcanza MAE = {gb['mae']:.3f}, RMSE = {gb['rmse']:.3f} y WAPE = {gb['wape_pct']:.2f} %. "
        f"El baseline temporal obtiene MAE = {baseline['mae']:.3f}, RMSE = {baseline['rmse']:.3f} y WAPE = {baseline['wape_pct']:.2f} %. "
        "La reducción de MAE respecto al baseline es moderada, pero suficiente para justificar su integración experimental en el gemelo digital."
    ))
    add_table_before_refs(doc, "Tabla 7. Métricas globales de modelos en prueba.", ["Modelo", "MAE", "RMSE", "WAPE %", "Sesgo"], [
        [row.model_label, f"{row.mae:.3f}", f"{row.rmse:.3f}", f"{row.wape_pct:.2f}", f"{row.bias:.3f}"]
        for row in test.sort_values("model_label").itertuples(index=False)
    ], "Nota. MAE y RMSE están expresados en incidentes por hora; WAPE se reporta como porcentaje.")
    add_picture_before_refs(doc, ASSETS / "fig2_global_metrics.png", "Figura 3. Comparación global de desempeño predictivo en la partición de prueba.")
    add_picture_before_refs(doc, ASSETS / "fig4_actual_vs_predicted.png", "Figura 4. Serie real y predicha en prueba, suavizada con media móvil de 24 horas.")

    add_heading_before_refs(doc, "5.3. Integración del gemelo digital y simulación", 3)
    add_paragraph_before_refs(doc, (
        "El prototipo integra backend FastAPI, motor SimPy, frontend React con visualización 2D/3D y un asistente analítico basado en LangGraph. "
        "La entrada histórica reproduce la secuencia de llegadas y zonas; la entrada pronosticada genera incidentes sintéticos con media horaria igual al pronóstico. "
        "Las posiciones visibles son aproximaciones para análisis y visualización, no coordenadas GPS observadas. La flota inicial de 691 ambulancias es un supuesto proxy calculado para experimentación y no representa una flota oficial."
    ))
    add_picture_before_refs(doc, ASSETS / "fig1_architecture.png", "Figura 5. Arquitectura implementada del gemelo digital EMS.")

    add_heading_before_refs(doc, "5.4. Comparación experimental de políticas", 3)
    add_paragraph_before_refs(doc, (
        "La comparación pareada ejecutada con 10 réplicas de 12 horas no mostró diferencia entre la política tradicional y la política predictiva v1. "
        f"Ambas políticas obtuvieron respuesta media de {trad['tiempo_promedio_respuesta']:.3f} min, mediana de {trad['mediana_respuesta']:.3f} min, P90 de {trad['p90_respuesta']:.3f} min y cumplimiento de ocho minutos de {trad['porcentaje_menor_8min']:.3f} %. "
        "La diferencia media tradicional menos predictiva fue 0.000 min, con p = 1.000. Este resultado se interpreta como evidencia de que la primera heurística predictiva no modifica suficientemente las decisiones, no como evidencia contra el uso de pronósticos."
    ))
    add_table_before_refs(doc, "Tabla 8. Resultados agregados de la comparación pareada de políticas.", ["Indicador", "Tradicional", "Predictiva v1", "Diferencia"], [
        ["Respuesta media (min)", f"{trad['tiempo_promedio_respuesta']:.3f}", f"{pred['tiempo_promedio_respuesta']:.3f}", "0.000"],
        ["Mediana respuesta (min)", f"{trad['mediana_respuesta']:.3f}", f"{pred['mediana_respuesta']:.3f}", "0.000"],
        ["P90 respuesta (min)", f"{trad['p90_respuesta']:.3f}", f"{pred['p90_respuesta']:.3f}", "0.000"],
        ["Meta <= 8 min (%)", f"{trad['porcentaje_menor_8min']:.3f}", f"{pred['porcentaje_menor_8min']:.3f}", "0.000"],
        ["Utilización temporal", f"{trad['utilizacion_ambulancias']:.3f}", f"{pred['utilizacion_ambulancias']:.3f}", "0.000"],
    ], "Nota. La diferencia se calcula como tradicional menos predictiva; valores positivos favorecerían la política predictiva.")
    add_picture_before_refs(doc, ASSETS / "fig5_policy_experiment.png", "Figura 6. Comparación visual de métricas principales entre políticas.")

    add_heading_before_refs(doc, "6. Discusión", 2)
    add_paragraph_before_refs(doc, (
        "Los resultados confirman que el componente predictivo aporta información útil sobre demanda horaria, pero también muestran una separación importante entre predicción y decisión. "
        "El mejor modelo en prueba reduce errores frente al baseline temporal; sin embargo, la política asistida por pronóstico implementada en esta fase no mejora el despacho simulado. "
        "Esta diferencia fortalece el artículo porque evita presentar el gemelo digital como una solución terminada y lo ubica como una plataforma experimental para probar reglas prescriptivas."
    ))
    add_paragraph_before_refs(doc, (
        "La contribución del software se encuentra en su trazabilidad: cada resultado puede vincularse con extracción, limpieza, partición temporal, entrenamiento, simulación y visualización. "
        "Así, el sistema permite identificar cuándo una mejora pertenece al modelo predictivo, cuándo a la política de despacho y cuándo a supuestos de flota o servicio."
    ))

    add_heading_before_refs(doc, "6.1. Amenazas a la validez", 3)
    add_paragraph_before_refs(doc, (
        "Validez interna: la política predictiva v1 puede no alterar decisiones con la flota proxy utilizada. Validez de constructo: el tiempo de respuesta simulado no equivale a resultado clínico. "
        "Validez externa: Nueva York no representa automáticamente Trujillo u otros contextos. Validez de conclusión: las 10 réplicas pareadas son suficientes para documentar este resultado nulo inicial, pero no para descartar políticas predictivas más fuertes. "
        "Validez de datos: no se observan GPS, bases reales, disponibilidad hospitalaria ni reglas FDNY; por ello se declaran como supuestos."
    ))

    add_heading_before_refs(doc, "7. Conclusiones", 2)
    add_paragraph_before_refs(doc, (
        "El estudio completa una base de gemelo digital EMS con datos históricos reales, modelos predictivos, simulación discreta y visualización operacional. "
        "El modelo Random Forest obtuvo el mejor desempeño predictivo en prueba, pero la política predictiva v1 no mejoró el desempeño operacional frente al despacho tradicional. "
        "La conclusión principal es que el pronóstico es una condición necesaria, pero no suficiente: el siguiente avance debe centrarse en relocalización preventiva, sensibilidad de flota, optimización multiobjetivo y validación externa."
    ))

    add_heading_before_refs(doc, "8. Disponibilidad de datos, código y reproducibilidad", 2)
    add_paragraph_before_refs(doc, (
        f"El estudio se reproduce con el snapshot {SNAPSHOT}, los scripts del directorio research, los servicios del backend FastAPI y los reportes ubicados en reports/nyc_ems. "
        "Los datos crudos se mantienen fuera de Git por tamaño, pero el manifiesto conserva conteos, hashes y configuración. "
        "Los comandos principales de verificación son: python -m research.pipeline.nyc_ems verify --snapshot, python -m unittest discover -s research/tests -v, python -m unittest discover -s backend/tests -v, npm run lint y npm run build."
    ))

    add_heading_before_refs(doc, "9. Declaraciones éticas, confidencialidad y uso de IA", 2)
    add_paragraph_before_refs(doc, (
        "El estudio usa datos públicos abiertos y no interviene sobre pacientes, operadores ni servicios reales. No se accede a historias clínicas ni se realiza seguimiento individual. "
        "Si posteriormente se aplican los instrumentos descritos en la metodología a expertos o usuarios, se solicitará aprobación ética o exención institucional y consentimiento informado antes de recolectar respuestas."
    ))
    add_paragraph_before_refs(doc, (
        "Se utilizó IA generativa como apoyo para programación, depuración, organización de resultados y redacción técnica. Los autores revisaron y verificaron manualmente el contenido, los supuestos y las métricas antes de incorporarlos. "
        "No se usó IA para fabricar datos, resultados experimentales ni respuestas de participantes."
    ))
    add_paragraph_before_refs(doc, (
        "Los autores declaran no tener conflictos de interés. No se reporta financiamiento externo específico para este avance."
    ))

    final_refs = preserve_references_snapshot(doc)
    if final_refs != original_refs:
        raise RuntimeError("Las referencias cambiaron; se cancela la escritura para preservar la lista original.")
    doc.save(OUTPUT)


if __name__ == "__main__":
    main()
