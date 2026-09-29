from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict
import unicodedata

from app.core.paths import DOCS_DIR
from app.services import historical_data_service as historical
from app.services import run_storage
from app.services.simulation_service import runtime

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback for environments without langgraph installed yet.
    END = None
    START = None
    StateGraph = None


DOCS_TO_INDEX = [
    ("Plan de implementacion NYC EMS 2026", "PLAN_IMPLEMENTACION_NYC_EMS_2026.md"),
    ("Reporte de extraccion completa NYC EMS", "NYC_EMS_FULL_EXTRACTION_REPORT.md"),
    ("Contrato historico de datos NYC EMS", "NYC_EMS_HISTORICAL_DATA_CONTRACT.md"),
    ("Reporte fase 5 modelos", "NYC_EMS_PHASE5_MODEL_REPORT.md"),
    ("Reporte fase 6 simulacion", "NYC_EMS_PHASE6_SIMULATION_CALIBRATION_REPORT.md"),
    ("Reporte fase 7 API/frontend", "NYC_EMS_PHASE7_API_FRONTEND_REPORT.md"),
    ("Motor e integracion visual", "NYC_EMS_ENGINE_VISUAL_INTEGRATION.md"),
    ("Protocolo de investigacion NYC EMS", "NYC_EMS_RESEARCH_PROTOCOL.md"),
    ("Articulo de investigacion", "Art\u00edculo de Investigaci\u00f3n.md"),
]

AVAILABLE_CAPABILITIES = [
    "Consultar estado del plan y fases implementadas.",
    "Interpretar el snapshot NYC EMS, cohortes y procedencia local.",
    "Explicar metricas reales de los tres modelos predictivos entrenados.",
    "Interpretar la corrida activa o persistida del simulador historico.",
    "Distinguir datos observados, predicciones y simulacion contrafactual.",
]

PENDING_CAPABILITIES = [
    "Concluir mejoras causales u operativas reales fuera del entorno simulado.",
    "Calcular Aiken, Cronbach o KR-20 sin respuestas reales de expertos/participantes.",
]


class AssistantState(TypedDict, total=False):
    request: dict[str, Any]
    normalized_question: str
    intent: str
    documents: list[dict[str, str]]
    evidence: list[dict[str, str]]
    context: dict[str, Any]
    status: str
    answer: str
    trace: list[str]


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn").lower().strip()


def classify_intent(question: str) -> str:
    q = normalize_text(question)
    if any(term in q for term in ["fase", "estado", "avance", "quedamos", "pendiente", "ticket"]):
        return "estado_proyecto"
    if any(term in q for term in ["dataset", "datos", "extraccion", "snapshot", "socrata", "nyc", "cohorte"]):
        return "datos_historicos"
    if any(term in q for term in ["metodologia", "articulo", "investigacion", "formula", "poblacion"]):
        return "metodologia_articulo"
    if any(term in q for term in ["prediccion", "modelo", "entrenamiento", "mae", "rmse", "wape", "gradient", "forest"]):
        return "prediccion"
    if any(term in q for term in ["simulacion", "gemelo", "calibracion", "escenario", "ambulancia", "corrida", "flota"]):
        return "simulacion"
    if any(term in q for term in ["comparacion", "politica", "benchmark", "resultado", "mejor", "tradicional", "predictiva"]):
        return "comparacion"
    if any(term in q for term in ["aiken", "cronbach", "kuder", "kr-20", "encuesta", "instrumento"]):
        return "instrumentos"
    return "general"


def _fmt_number(value: Any, digits: int = 1) -> str:
    if value is None:
        return "no disponible"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return f"{int(number):,}".replace(",", " ")
    return f"{number:,.{digits}f}".replace(",", " ")


def _safe_get(container: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = container
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def read_documents() -> list[dict[str, str]]:
    docs = []
    for title, filename in DOCS_TO_INDEX:
        path = DOCS_DIR / filename
        if path.exists():
            docs.append({"title": title, "source": f"docs/{filename}", "content": path.read_text(encoding="utf-8")})
    return docs


def collect_evidence(documents: list[dict[str, str]], question: str, intent: str) -> list[dict[str, str]]:
    preferred = {
        "estado_proyecto": ["docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md", "docs/NYC_EMS_PHASE7_API_FRONTEND_REPORT.md"],
        "datos_historicos": ["docs/NYC_EMS_FULL_EXTRACTION_REPORT.md", "docs/NYC_EMS_HISTORICAL_DATA_CONTRACT.md"],
        "metodologia_articulo": ["docs/Art\u00edculo de Investigaci\u00f3n.md", "docs/NYC_EMS_RESEARCH_PROTOCOL.md"],
        "instrumentos": ["docs/Art\u00edculo de Investigaci\u00f3n.md", "docs/NYC_EMS_RESEARCH_PROTOCOL.md"],
        "prediccion": ["docs/NYC_EMS_PHASE5_MODEL_REPORT.md", "docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md"],
        "simulacion": ["docs/NYC_EMS_ENGINE_VISUAL_INTEGRATION.md", "docs/NYC_EMS_PHASE6_SIMULATION_CALIBRATION_REPORT.md"],
        "comparacion": ["docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md", "docs/NYC_EMS_ENGINE_VISUAL_INTEGRATION.md"],
    }.get(intent)
    selected = [doc for doc in documents if not preferred or doc["source"] in preferred][:3]
    evidence = []
    for doc in selected:
        lines = [line.strip() for line in doc["content"].splitlines() if line.strip()]
        excerpt = " ".join(lines[:4])
        evidence.append({"title": doc["title"], "source": doc["source"], "excerpt": excerpt[:700]})
    return evidence


def _model_context(dataset_id: str) -> dict[str, Any]:
    profile = historical.dataset_profile(dataset_id)
    paths = historical._dataset_paths(dataset_id)
    metrics = historical._read_json(paths["metrics"]) if paths["metrics"].exists() else {}
    return {
        "profile": profile,
        "selection": metrics.get("selection", profile.get("model_selection", {})),
        "global_metrics": metrics.get("global", {}),
        "by_zone": metrics.get("by_zone", {}),
    }


def _runtime_context() -> dict[str, Any]:
    state = runtime.state or {}
    simulation = state.get("simulation", {})
    metrics = state.get("metrics", {})
    predictions = state.get("predictions", [])
    zone_summary = simulation.get("zone_summary", [])
    top_predictions = sorted(predictions, key=lambda item: item.get("demanda_predicha_ml", 0), reverse=True)[:3]
    busiest_zones = sorted(zone_summary, key=lambda item: item.get("arrived", 0), reverse=True)[:3]
    active_summary = run_storage.storage_summary()
    return {
        "run_id": runtime.run_id,
        "state_loaded": bool(runtime.run_id),
        "data_mode": state.get("data_mode", "demo"),
        "dataset_id": state.get("dataset_id"),
        "model_id": state.get("model_id"),
        "policy": state.get("policy"),
        "seed": state.get("seed"),
        "sim_minute": state.get("sim_minute"),
        "start_minute": state.get("start_minute"),
        "total_duration_min": state.get("total_duration_min"),
        "metrics": metrics,
        "simulation": simulation,
        "top_predictions": top_predictions,
        "busiest_zones": busiest_zones,
        "storage": active_summary,
    }


def collect_system_context(intent: str) -> dict[str, Any]:
    dataset_id = runtime.state.get("dataset_id") or historical.DEFAULT_DATASET_ID
    context: dict[str, Any] = {
        "dataset_id": dataset_id,
        "runtime": _runtime_context(),
    }
    if intent in {"datos_historicos", "prediccion", "simulacion", "comparacion", "estado_proyecto", "general"}:
        context["models"] = _model_context(dataset_id)
    if intent in {"datos_historicos", "estado_proyecto", "general"}:
        context["dataset_profile"] = historical.dataset_profile(dataset_id)
    return context


def collect_context_evidence(context: dict[str, Any], intent: str) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    runtime_context = context.get("runtime", {})
    if runtime_context.get("state_loaded"):
        metrics = runtime_context.get("metrics", {})
        simulation = runtime_context.get("simulation", {})
        evidence.append(
            {
                "title": "Corrida activa/persistida",
                "source": "runtime://simulation",
                "excerpt": (
                    f"run_id={runtime_context.get('run_id')}; politica={runtime_context.get('policy')}; "
                    f"demanda={simulation.get('demand_source')}; total={metrics.get('incidentes_totales')}; "
                    f"atendidos={metrics.get('incidentes_atendidos')}; pendientes={metrics.get('incidentes_pendientes')}."
                ),
            }
        )
    if intent in {"prediccion", "comparacion", "estado_proyecto", "general"}:
        selection = context.get("models", {}).get("selection", {})
        if selection:
            evidence.append(
                {
                    "title": "Metricas de modelos Fase 5",
                    "source": "artifact://phase5/metrics.json",
                    "excerpt": (
                        f"Modelo seleccionado={selection.get('best_model_id')}; criterio={selection.get('criterion')}; "
                        f"MAE validacion={selection.get('validation_mae')}."
                    ),
                }
            )
    return evidence


def determine_status(intent: str, context: dict[str, Any], question: str) -> str:
    if not question.strip():
        return "needs_more_context"
    if intent == "simulacion" and not context.get("runtime", {}).get("state_loaded"):
        return "not_ready"
    return "answered"


def _project_answer() -> str:
    return (
        "El proyecto quedo con Fases 0 a 8 implementadas como base funcional de investigacion. "
        "Ya hay datos historicos, modelos, motor de simulacion, frontend NYC, persistencia local, asistente analitico "
        "y experimentos pareados tradicional vs predictivo.\n\n"
        "La siguiente fase fuerte es Fase 9: instrumentos humanos para Aiken, Cronbach y KR-20. Para el articulo final "
        "todavia se debe congelar el presupuesto definitivo de replicas, flota, sensibilidad y participantes."
    )


def _data_answer(context: dict[str, Any]) -> str:
    profile = context.get("dataset_profile") or context.get("models", {}).get("profile", {})
    window = profile.get("window", {})
    phase6 = profile.get("phase6", {})
    return (
        "El sistema trabaja con el snapshot NYC EMS "
        f"`{profile.get('id', context.get('dataset_id'))}`. La ventana es "
        f"{window.get('start_inclusive')} a {window.get('end_exclusive')} y contiene "
        f"{_fmt_number(profile.get('expected_rows'), 0)} incidentes crudos.\n\n"
        "Para simulacion no se carga el trimestre entero al navegador: FastAPI lee artefactos locales procesados, "
        "incluyendo llegadas historicas, cohortes, parametros de calibracion y pronosticos retrospectivos. "
        f"En Fase 6 quedaron { _fmt_number(phase6.get('historical_arrivals'), 0) } llegadas historicas preparadas "
        f"y { _fmt_number(phase6.get('observed_response_rows'), 0) } respuestas observadas de referencia, si esos campos "
        "estan presentes en el manifiesto."
    )


def _prediction_answer(context: dict[str, Any]) -> str:
    models = context.get("models", {})
    selection = models.get("selection", {})
    global_metrics = models.get("global_metrics", {})
    lines = [
        "Los modelos predicen demanda horaria por borough, no ubicaciones GPS ni desenlaces clinicos.",
        f"Modelo seleccionado: `{selection.get('best_model_id', 'no disponible')}` por `{selection.get('criterion', 'criterio no disponible')}`.",
    ]
    for model_id, model_metrics in global_metrics.items():
        test = model_metrics.get("test", {})
        validation = model_metrics.get("validation", {})
        lines.append(
            f"- `{model_id}`: MAE validacion {_fmt_number(validation.get('mae'))}, "
            f"MAE prueba {_fmt_number(test.get('mae'))}, RMSE prueba {_fmt_number(test.get('rmse'))}, "
            f"WAPE prueba {_fmt_number((test.get('wape') or 0) * 100)}%."
        )
    lines.append(
        "Estos valores justifican el componente predictivo; la mejora operativa se evalua con los experimentos pareados de Fase 8."
    )
    return "\n".join(lines)


def _simulation_answer(context: dict[str, Any]) -> str:
    runtime_context = context.get("runtime", {})
    if not runtime_context.get("state_loaded"):
        return (
            "No hay una corrida activa o persistida cargada. Primero se debe crear una simulacion historica desde el frontend "
            "o desde `/api/simulations`; despues el asistente podra interpretar sus metricas reales."
        )
    metrics = runtime_context.get("metrics", {})
    simulation = runtime_context.get("simulation", {})
    top = runtime_context.get("top_predictions", [])
    busiest = runtime_context.get("busiest_zones", [])
    demand_text = "historica" if simulation.get("demand_source") == "historical" else "generada por pronostico"
    answer = [
        f"La corrida activa es `{runtime_context.get('run_id')}` con politica `{runtime_context.get('policy')}`, "
        f"modelo `{runtime_context.get('model_id')}` y demanda {demand_text}.",
        "",
        "Lectura operativa actual:",
        f"- Llamadas recibidas en la simulacion: {_fmt_number(metrics.get('incidentes_totales'), 0)}.",
        f"- Llegadas a escena simuladas: {_fmt_number(metrics.get('incidentes_atendidos'), 0)}.",
        f"- En espera: {_fmt_number(metrics.get('incidentes_pendientes'), 0)}.",
        f"- Servicios completados: {_fmt_number(simulation.get('completed'), 0)}.",
        f"- Servicios no finalizados al corte: {_fmt_number(simulation.get('unfinished'), 0)}.",
        f"- Respuesta media simulada: {_fmt_number(metrics.get('tiempo_promedio_respuesta'))} min.",
        f"- P90 simulado: {_fmt_number(metrics.get('p90_respuesta'))} min.",
        f"- Referencia observada acumulada: {_fmt_number(simulation.get('observed_response_mean'))} min "
        f"con {_fmt_number(simulation.get('observed_response_count'), 0)} casos validos.",
    ]
    if top:
        answer.append("")
        answer.append(
            "Mayor demanda pronosticada ahora: "
            + ", ".join(f"{item['zona_nombre']} {_fmt_number(item.get('demanda_predicha_ml'))}/h" for item in top)
            + "."
        )
    if busiest:
        answer.append(
            "Mayor carga observada en la corrida: "
            + ", ".join(f"zona {item['zone_id']} con {item.get('arrived')} llamadas" for item in busiest)
            + "."
        )
    answer.append(
        "\nImportante: estos resultados son de una simulacion con supuestos de flota y tiempos. La comparacion formal contra "
        "otra politica debe leerse desde la pestana Experimentos, donde Fase 8 ejecuta condiciones pareadas."
    )
    return "\n".join(answer)


def _comparison_answer(context: dict[str, Any]) -> str:
    runtime_context = context.get("runtime", {})
    if not runtime_context.get("state_loaded"):
        return (
            "Todavia no hay una corrida activa para interpretar. Para comparar de verdad se necesitan al menos dos politicas "
            "ejecutadas bajo la misma ventana, flota, semilla y fuente de demanda."
        )
    return (
        "Fase 8 ya puede ejecutar comparaciones simuladas pareadas entre politica tradicional y predictiva. "
        "La lectura correcta es: misma ventana historica, misma flota, mismas semillas/componentes de servicio, varias replicas "
        "y deltas calculados como tradicional - predictivo.\n\n"
        "El resultado principal es la diferencia pareada en tiempo medio de respuesta. Los secundarios son P90, cumplimiento "
        "menor a 8 minutos, servicios no finalizados y trazabilidad de incidentes pareados. Aun no debe interpretarse como "
        "mejora operativa real en campo; es evidencia de simulacion para el articulo."
    )


def _instruments_answer() -> str:
    return (
        "Aiken, Cronbach y KR-20 no se calculan con las filas EMS. Se calculan con instrumentos humanos.\n\n"
        "Aiken: expertos califican claridad, pertinencia y relevancia de items. Cronbach: participantes responden una escala "
        "Likert, por ejemplo utilidad percibida del sistema. KR-20: participantes responden un test dicotomico de interpretacion "
        "de resultados, por ejemplo elegir correctamente que significa P90, demanda historica o politica predictiva."
    )


def compose_answer(question: str, intent: str, status: str, evidence: list[dict[str, str]], context: dict[str, Any]) -> str:
    if not question.strip():
        return "Escribe una pregunta sobre fases, dataset, modelos, simulacion, comparaciones o instrumentos."
    if intent == "estado_proyecto":
        return _project_answer()
    if intent == "datos_historicos":
        return _data_answer(context)
    if intent == "prediccion":
        return _prediction_answer(context)
    if intent == "simulacion":
        return _simulation_answer(context)
    if intent == "comparacion":
        return _comparison_answer(context)
    if intent == "instrumentos":
        return _instruments_answer()
    if intent == "metodologia_articulo":
        return (
            "La metodologia debe contar tres capas: datos historicos NYC EMS, modelos de demanda por borough-hora y simulacion "
            "contrafactual de despacho. Luego, de forma separada, describe instrumentos humanos para utilidad e interpretacion "
            "si vas a aplicar Aiken, Cronbach y KR-20."
        )
    return (
        "Puedo ayudarte a interpretar el proyecto desde sus artefactos reales: snapshot, modelos, corrida activa, predicciones, "
        "simulacion y limites metodologicos. Preguntame, por ejemplo, por la corrida actual, por los modelos o por que falta "
        "para comparar politicas."
    )


def _run_deterministic_graph(request: dict[str, Any]) -> AssistantState:
    question = request.get("message", "")
    normalized = normalize_text(question)
    intent = classify_intent(normalized)
    documents = read_documents()
    context = collect_system_context(intent)
    evidence = collect_evidence(documents, question, intent) + collect_context_evidence(context, intent)
    status = determine_status(intent, context, question)
    answer = compose_answer(question, intent, status, evidence, context)
    return {
        "request": request,
        "normalized_question": normalized,
        "intent": intent,
        "documents": documents,
        "context": context,
        "evidence": evidence,
        "status": status,
        "answer": answer,
        "trace": [
            "normalize_question",
            "classify_intent",
            "load_documents",
            "collect_system_context",
            "collect_evidence",
            "check_readiness",
            "compose_response",
        ],
    }


def _run_langgraph(request: dict[str, Any]) -> AssistantState | None:
    if StateGraph is None or START is None or END is None:
        return None

    def normalize_node(state: AssistantState) -> AssistantState:
        question = state["request"].get("message", "")
        return {
            "normalized_question": normalize_text(question),
            "trace": state.get("trace", []) + ["normalize_question"],
        }

    def classify_node(state: AssistantState) -> AssistantState:
        return {
            "intent": classify_intent(state.get("normalized_question", "")),
            "trace": state.get("trace", []) + ["classify_intent"],
        }

    def documents_node(state: AssistantState) -> AssistantState:
        return {
            "documents": read_documents(),
            "trace": state.get("trace", []) + ["load_documents"],
        }

    def context_node(state: AssistantState) -> AssistantState:
        return {
            "context": collect_system_context(state.get("intent", "general")),
            "trace": state.get("trace", []) + ["collect_system_context"],
        }

    def evidence_node(state: AssistantState) -> AssistantState:
        context = state.get("context", {})
        intent = state.get("intent", "general")
        return {
            "evidence": collect_evidence(state.get("documents", []), state["request"].get("message", ""), intent)
            + collect_context_evidence(context, intent),
            "trace": state.get("trace", []) + ["collect_evidence"],
        }

    def readiness_node(state: AssistantState) -> AssistantState:
        return {
            "status": determine_status(
                state.get("intent", "general"),
                state.get("context", {}),
                state["request"].get("message", ""),
            ),
            "trace": state.get("trace", []) + ["check_readiness"],
        }

    def response_node(state: AssistantState) -> AssistantState:
        return {
            "answer": compose_answer(
                state["request"].get("message", ""),
                state.get("intent", "general"),
                state.get("status", "needs_more_context"),
                state.get("evidence", []),
                state.get("context", {}),
            ),
            "trace": state.get("trace", []) + ["compose_response"],
        }

    workflow = StateGraph(AssistantState)
    workflow.add_node("normalize_question", normalize_node)
    workflow.add_node("classify_intent", classify_node)
    workflow.add_node("load_documents", documents_node)
    workflow.add_node("collect_system_context", context_node)
    workflow.add_node("collect_evidence", evidence_node)
    workflow.add_node("check_readiness", readiness_node)
    workflow.add_node("compose_response", response_node)
    workflow.add_edge(START, "normalize_question")
    workflow.add_edge("normalize_question", "classify_intent")
    workflow.add_edge("classify_intent", "load_documents")
    workflow.add_edge("load_documents", "collect_system_context")
    workflow.add_edge("collect_system_context", "collect_evidence")
    workflow.add_edge("collect_evidence", "check_readiness")
    workflow.add_edge("check_readiness", "compose_response")
    workflow.add_edge("compose_response", END)
    graph = workflow.compile()
    return graph.invoke(
        {
            "request": request,
            "normalized_question": "",
            "intent": "general",
            "documents": [],
            "evidence": [],
            "context": {},
            "status": "needs_more_context",
            "answer": "",
            "trace": [],
        }
    )


def run_assistant_query(request: dict[str, Any]) -> dict[str, Any]:
    result = _run_langgraph(request) or _run_deterministic_graph(request)
    return {
        "answer": result["answer"],
        "intent": result["intent"],
        "status": result["status"],
        "available_capabilities": AVAILABLE_CAPABILITIES,
        "pending_capabilities": PENDING_CAPABILITIES,
        "evidence": result["evidence"],
        "graph_trace": result["trace"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
