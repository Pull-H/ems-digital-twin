import fs from 'node:fs';
import path from 'node:path';
import { Annotation, END, START, StateGraph } from '@langchain/langgraph';
import {
  AssistantEvidence,
  AssistantIntent,
  AssistantQueryRequest,
  AssistantQueryResponse,
} from '../types';

type AssistantDocument = {
  title: string;
  source: string;
  content: string;
};

const DOCS_TO_INDEX = [
  { title: 'Plan de implementacion NYC EMS 2026', source: 'docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md' },
  { title: 'Reporte de extraccion completa NYC EMS', source: 'docs/NYC_EMS_FULL_EXTRACTION_REPORT.md' },
  { title: 'Contrato historico de datos NYC EMS', source: 'docs/NYC_EMS_HISTORICAL_DATA_CONTRACT.md' },
  { title: 'Protocolo de investigacion NYC EMS', source: 'docs/NYC_EMS_RESEARCH_PROTOCOL.md' },
  { title: 'Articulo de investigacion', source: 'docs/Artículo de Investigación.md' },
];

const AVAILABLE_CAPABILITIES = [
  'Consultar estado del plan de implementacion.',
  'Explicar el alcance del dataset NYC EMS usado por el proyecto.',
  'Resumir limitaciones actuales antes de prediccion y simulacion calibrada.',
  'Orientar sobre metodologia, instrumentos y evidencias documentales existentes.',
];

const PENDING_CAPABILITIES = [
  'Consultar metricas reales de modelos predictivos entrenados.',
  'Interpretar simulaciones historicas calibradas contra el trimestre NYC EMS.',
  'Comparar politicas con resultados experimentales finales.',
  'Generar conclusiones finales del articulo basadas en fase 8.',
];

const AssistantState = Annotation.Root({
  request: Annotation<AssistantQueryRequest>,
  normalizedQuestion: Annotation<string>,
  intent: Annotation<AssistantIntent>,
  documents: Annotation<AssistantDocument[]>({
    reducer: (_left, right) => right,
    default: () => [],
  }),
  evidence: Annotation<AssistantEvidence[]>({
    reducer: (_left, right) => right,
    default: () => [],
  }),
  status: Annotation<'answered' | 'not_ready' | 'needs_more_context'>,
  answer: Annotation<string>,
  trace: Annotation<string[]>({
    reducer: (left, right) => left.concat(right),
    default: () => [],
  }),
});

function readDocuments(): AssistantDocument[] {
  return DOCS_TO_INDEX.flatMap((doc) => {
    const absolutePath = path.join(process.cwd(), doc.source);
    if (!fs.existsSync(absolutePath)) return [];
    return [{
      ...doc,
      content: fs.readFileSync(absolutePath, 'utf8'),
    }];
  });
}

function normalizeText(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function classifyIntent(question: string): AssistantIntent {
  const q = normalizeText(question);

  if (/\b(fase|estado|avance|quedamos|pendiente|completad|ticket|plan)\b/.test(q)) return 'estado_proyecto';
  if (/\b(dataset|datos|extraccion|snapshot|socrata|nyc|historico|incidentes)\b/.test(q)) return 'datos_historicos';
  if (/\b(metodologia|articulo|investigacion|formula|poblacion|muestra|muestreo)\b/.test(q)) return 'metodologia_articulo';
  if (/\b(prediccion|modelo|entrenamiento|mae|rmse|wape|forecast)\b/.test(q)) return 'prediccion';
  if (/\b(simulacion|gemelo|calibracion|escenario|ambulancia|despacho)\b/.test(q)) return 'simulacion';
  if (/\b(comparacion|politica|reactiva|predictiva|benchmark|resultado|mejor)\b/.test(q)) return 'comparacion';
  if (/\b(aiken|cronbach|kuder|richardson|kr-20|encuesta|instrumento|likert)\b/.test(q)) return 'instrumentos';

  return 'general';
}

function extractUsefulLines(content: string, query: string, maxLines = 3): string[] {
  const queryTerms = normalizeText(query)
    .split(/\W+/)
    .filter((term) => term.length > 4);

  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('|---'));

  const scored = lines
    .map((line) => {
      const normalized = normalizeText(line);
      const score = queryTerms.reduce((total, term) => total + (normalized.includes(term) ? 1 : 0), 0);
      const phaseBoost = normalized.includes('fases 0, 1 y 2 completadas') ? 4 : 0;
      const extractionBoost = normalized.includes('405998') || normalized.includes('405,998') ? 3 : 0;
      return { line, score: score + phaseBoost + extractionBoost };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxLines)
    .map((item) => item.line);

  return scored.length > 0 ? scored : lines.slice(0, maxLines);
}

function collectEvidence(documents: AssistantDocument[], query: string, intent: AssistantIntent): AssistantEvidence[] {
  const preferredSources: Partial<Record<AssistantIntent, string[]>> = {
    estado_proyecto: ['docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md'],
    datos_historicos: [
      'docs/NYC_EMS_FULL_EXTRACTION_REPORT.md',
      'docs/NYC_EMS_HISTORICAL_DATA_CONTRACT.md',
      'docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md',
    ],
    metodologia_articulo: ['docs/Artículo de Investigación.md', 'docs/NYC_EMS_RESEARCH_PROTOCOL.md'],
    instrumentos: ['docs/Artículo de Investigación.md', 'docs/NYC_EMS_RESEARCH_PROTOCOL.md'],
    prediccion: ['docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md'],
    simulacion: ['docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md', 'docs/SIMULATION_CONTRACT.md'],
    comparacion: ['docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md', 'docs/Artículo de Investigación.md'],
  };

  const preferred = preferredSources[intent] || DOCS_TO_INDEX.map((doc) => doc.source);
  return documents
    .filter((doc) => preferred.includes(doc.source))
    .slice(0, 3)
    .map((doc) => ({
      title: doc.title,
      source: doc.source,
      excerpt: extractUsefulLines(doc.content, query).join(' '),
    }));
}

function intentRequiresPendingResults(intent: AssistantIntent): boolean {
  return intent === 'prediccion' || intent === 'simulacion' || intent === 'comparacion';
}

function composeAnswer(
  question: string,
  intent: AssistantIntent,
  status: 'answered' | 'not_ready' | 'needs_more_context',
  evidence: AssistantEvidence[]
): string {
  if (!question.trim()) {
    return 'Escribe una pregunta sobre el estado del proyecto, el dataset NYC EMS, la metodologia o los modulos pendientes. Por ahora trabajo con la documentacion local del proyecto.';
  }

  if (status === 'not_ready') {
    const topic =
      intent === 'prediccion'
        ? 'los modelos predictivos'
        : intent === 'simulacion'
          ? 'la simulacion calibrada'
          : 'la comparacion experimental de politicas';

    return [
      `Todavia no puedo responder con resultados finales sobre ${topic}, porque esa parte depende de fases pendientes del plan.`,
      'Con lo disponible ahora, puedo ubicar el estado del proyecto y explicar que la base historica ya fue extraida y versionada, pero faltan perfilado, limpieza, cohortes, variables, entrenamiento, calibracion e integracion final.',
      'Cuando terminemos la fase 7, este modulo podra consultar metricas, escenarios y reportes reales en lugar de responder solo con el estado documental.',
    ].join('\n\n');
  }

  if (intent === 'estado_proyecto') {
    return [
      'El proyecto quedo con las fases 0, 1 y 2 completadas: protocolo/contrato/configuracion, extraccion piloto y extraccion completa versionada.',
      'El siguiente trabajo tecnico es la fase 3: perfilado, limpieza y definicion de cohortes analiticas. A partir de ahi se preparan geografia/features, entrenamiento, calibracion del simulador, integracion y experimentos del articulo.',
      evidence.length > 0 ? `Evidencia usada: ${evidence.map((item) => item.source).join(', ')}.` : '',
    ].filter(Boolean).join('\n\n');
  }

  if (intent === 'datos_historicos') {
    return [
      'La base actual trabaja con el dataset NYC EMS Incident Dispatch Data. Ya existe una extraccion local versionada del trimestre seleccionado para no depender de consultar la API en cada analisis.',
      'Ese material sirve como insumo bruto para la fase 3. Todavia falta transformarlo en cohortes limpias y tablas analiticas antes de entrenar o simular con rigor.',
      evidence.length > 0 ? `Fuentes revisadas: ${evidence.map((item) => item.source).join(', ')}.` : '',
    ].filter(Boolean).join('\n\n');
  }

  if (intent === 'metodologia_articulo') {
    return [
      'La metodologia debe describir el estudio como una evaluacion retrospectiva y simulada: datos historicos publicados, modelos predictivos, simulacion de escenarios y evaluacion de interpretacion/utilidad mediante instrumentos.',
      'El asistente puede explicar esas secciones, pero no debe afirmar resultados que todavia no fueron calculados. Para el articulo, Aiken se asocia con validez de contenido de instrumentos; Cronbach y KR-20 con consistencia interna de respuestas de participantes, no con filas EMS.',
    ].join('\n\n');
  }

  if (intent === 'instrumentos') {
    return [
      'Los instrumentos previstos son: ficha de juicio de expertos, cuestionario de utilidad percibida y prueba de interpretacion de resultados.',
      'Aiken se calcula con valoraciones de expertos; alfa de Cronbach con respuestas tipo Likert del cuestionario; KR-20 con respuestas dicotomicas correctas/incorrectas de la prueba. Esos coeficientes analizan instrumentos humanos, no el dataset de incidentes.',
    ].join('\n\n');
  }

  return [
    'Por ahora soy una base funcional del asistente analitico. Puedo responder sobre documentacion, estado del pipeline, dataset y alcance metodologico.',
    'Las consultas sobre predicciones reales, simulaciones calibradas o resultados comparativos quedaran habilitadas cuando el sistema llegue a las fases correspondientes.',
  ].join('\n\n');
}

const graph = new StateGraph(AssistantState)
  .addNode('normalize_question', (state: typeof AssistantState.State) => ({
    normalizedQuestion: normalizeText(state.request.message || ''),
    trace: ['normalize_question'],
  }))
  .addNode('classify_intent', (state: typeof AssistantState.State) => ({
    intent: classifyIntent(state.normalizedQuestion),
    trace: ['classify_intent'],
  }))
  .addNode('load_documents', () => ({
    documents: readDocuments(),
    trace: ['load_documents'],
  }))
  .addNode('collect_evidence', (state: typeof AssistantState.State) => ({
    evidence: collectEvidence(state.documents, state.request.message, state.intent),
    trace: ['collect_evidence'],
  }))
  .addNode('check_readiness', (state: typeof AssistantState.State) => ({
    status: !state.request.message?.trim()
      ? 'needs_more_context'
      : intentRequiresPendingResults(state.intent)
        ? 'not_ready'
        : 'answered',
    trace: ['check_readiness'],
  }))
  .addNode('compose_response', (state: typeof AssistantState.State) => ({
    answer: composeAnswer(state.request.message, state.intent, state.status, state.evidence),
    trace: ['compose_response'],
  }))
  .addEdge(START, 'normalize_question')
  .addEdge('normalize_question', 'classify_intent')
  .addEdge('classify_intent', 'load_documents')
  .addEdge('load_documents', 'collect_evidence')
  .addEdge('collect_evidence', 'check_readiness')
  .addEdge('check_readiness', 'compose_response')
  .addEdge('compose_response', END)
  .compile();

export async function runAssistantQuery(request: AssistantQueryRequest): Promise<AssistantQueryResponse> {
  const result = await graph.invoke({
    request,
    normalizedQuestion: '',
    intent: 'general',
    documents: [],
    evidence: [],
    status: 'needs_more_context',
    answer: '',
    trace: [],
  });

  return {
    answer: result.answer,
    intent: result.intent,
    status: result.status,
    available_capabilities: AVAILABLE_CAPABILITIES,
    pending_capabilities: PENDING_CAPABILITIES,
    evidence: result.evidence,
    graph_trace: result.trace,
    generated_at: new Date().toISOString(),
  };
}
