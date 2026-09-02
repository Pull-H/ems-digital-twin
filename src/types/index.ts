export type SocioeconomicQuintile = 1 | 2 | 3 | 4 | 5;

export type AmbulanceStatus =
  | 'disponible'
  | 'asignada'
  | 'en ruta'
  | 'en escena'
  | 'trasladando'
  | 'en hospital'
  | 'reubicándose';

export type IncidentPriority = 'alta' | 'media' | 'baja';

export type IncidentType =
  | 'accidente de tránsito'
  | 'emergencia cardíaca'
  | 'caída'
  | 'emergencia respiratoria'
  | 'trauma'
  | 'otro';

export type IncidentStatus = 'pendiente' | 'despachado' | 'en_atencion' | 'trasladando' | 'completado' | 'cancelado';

export type DispatchPolicy = 'tradicional' | 'predictivo';

export type SimulationScenario = 'dia_normal' | 'evento_masivo' | 'tormenta' | 'brote_respiratorio';

export interface Zone {
  id: number;
  nombre: string;
  codigo: string;
  centroide: [number, number]; // [lat, lng]
  poligono: [number, number][]; // Array of lat/lng coordinates
  poblacion: number;
  ingreso_promedio: number; // in USD or local currency
  quintil_socioeconomico: SocioeconomicQuintile; // 1 = most vulnerable / poorest, 5 = wealthiest
  nivel_vulnerabilidad: number; // 0.0 - 1.0 (1.0 = highest vulnerability)
  demanda_historica_diaria: number; // average daily incidents
  area_km2: number;
}

export interface EMSBase {
  id: number;
  nombre: string;
  codigo: string;
  latitud: number;
  longitud: number;
  capacidad: number;
  zona_id: number;
  descripcion: string;
}

export interface Hospital {
  id: number;
  nombre: string;
  codigo: string;
  latitud: number;
  longitud: number;
  capacidad: number; // total ER beds
  ocupacion: number; // current active occupied beds
  nivel_trauma: 1 | 2 | 3; // 1 = highest trauma specialty
  tiempo_espera_min: number; // triage/handover delay in minutes
  zona_id: number;
}

export interface Ambulance {
  id: number;
  codigo: string;
  latitud: number;
  longitud: number;
  base_id: number;
  zona_actual_id: number;
  estado: AmbulanceStatus;
  velocidad_kmh: number;
  incidente_asignado_id: string | null;
  disponible_desde_min: number;
  kilometraje_total: number;
  incidentes_atendidos: number;
  target_lat?: number;
  target_lng?: number;
}

export interface Incident {
  id: string;
  fecha_hora: string; // ISO string
  sim_time_min: number; // Simulation minute
  latitud: number;
  longitud: number;
  zona_id: number;
  quintil_socioeconomico: SocioeconomicQuintile;
  prioridad: IncidentPriority;
  tipo: IncidentType;
  estado: IncidentStatus;
  ambulancia_id: number | null;
  hospital_id: number | null;
  tiempo_llamada: number; // sim_time when generated
  tiempo_despacho: number | null;
  tiempo_llegada_escena: number | null;
  tiempo_respuesta_min: number | null; // tiempo_llegada_escena - tiempo_llamada
  duracion_atencion_escena_min: number;
  requiere_traslado: boolean;
  tiempo_llegada_hospital: number | null;
  tiempo_liberacion: number | null;
  explicacion_despacho?: string;
  politica_usada?: DispatchPolicy;
}

export interface DemandPrediction {
  zona_id: number;
  zona_nombre: string;
  horizonte_min: 15 | 30 | 60;
  demanda_predicha_base: number;
  demanda_predicha_ml: number;
  nivel_riesgo: 'bajo' | 'medio' | 'alto';
  probabilidad_incidente: number;
  factores_principales: string[];
  fecha_generacion: string;
}

export interface QuintileMetric {
  quintil: SocioeconomicQuintile;
  nombre_quintil: string;
  total_incidentes: number;
  tiempo_promedio_respuesta: number;
  mediana_respuesta: number;
  p90_respuesta: number;
  tiempo_maximo: number;
  porcentaje_menor_8min: number;
  vulnerabilidad_promedio: number;
}

export interface SimulationMetrics {
  tiempo_promedio_respuesta: number;
  mediana_respuesta: number;
  p90_respuesta: number;
  tiempo_maximo_respuesta: number;
  porcentaje_menor_8min: number;
  distancia_total_km: number;
  utilizacion_ambulancias: number; // 0.0 - 1.0 (percentage of time busy)
  incidentes_totales: number;
  incidentes_atendidos: number;
  incidentes_pendientes: number;
  por_quintil: Record<SocioeconomicQuintile, QuintileMetric>;
  diferencia_max_min_quintiles: number; // Worst quintile time - Best quintile time
  razon_disparidad: number; // Worst quintile avg time / Best quintile avg time (1.0 = perfect equity)
}

export interface StatisticalTestResult {
  t_test: {
    t_stat: number;
    p_value: number;
    significant_p05: boolean;
    interpretacion: string;
  };
  wilcoxon: {
    w_stat: number;
    z_score: number;
    p_value: number;
    significant_p05: boolean;
    interpretacion: string;
  };
  bootstrap_ci: {
    delta_tiempo_promedio: { mean: number; ci_lower: number; ci_upper: number }; // min reduced
    delta_cumplimiento_8min: { mean: number; ci_lower: number; ci_upper: number }; // % increased
    delta_razon_disparidad: { mean: number; ci_lower: number; ci_upper: number }; // ratio reduced toward 1.0
  };
  ml_evaluacion: {
    mae: number;
    rmse: number;
    r2: number;
    mae_baseline: number;
    rmse_baseline: number;
  };
}

export interface SimulationRun {
  id: string;
  nombre: string;
  fecha_creacion: string;
  politica_despacho: DispatchPolicy;
  escenario: SimulationScenario;
  semilla: number;
  duracion_min: number;
  num_ambulancias: number;
  estado: 'preparada' | 'en_ejecucion' | 'pausada' | 'completada';
  metricas: SimulationMetrics | null;
  incidentes_muestra?: Incident[];
}

export interface SimEventLog {
  id: string;
  sim_time_min: number;
  tipo_evento:
    | 'incidente_creado'
    | 'ambulancia_despachada'
    | 'llegada_escena'
    | 'inicio_traslado'
    | 'llegada_hospital'
    | 'ambulancia_liberada'
    | 'reubicacion_iniciada'
    | 'reubicacion_completada';
  descripcion: string;
  ambulancia_codigo?: string;
  incidente_id?: string;
  zona_nombre?: string;
}

export interface SimulationState {
  sim_minute: number;
  is_running: boolean;
  scenario: SimulationScenario;
  policy: DispatchPolicy;
  seed: number;
  speed_multiplier: number;
  total_duration_min: number;
  traffic_factor: number;
  weather_factor: number;
  zones: Zone[];
  bases: EMSBase[];
  hospitals: Hospital[];
  ambulances: Ambulance[];
  incidents: Incident[];
  predictions: DemandPrediction[];
  relocation_recommendations: RelocationRecommendation[];
  event_logs: SimEventLog[];
  metrics: SimulationMetrics;
  weights: DispatchWeights;
}

export interface CreateSimulationRequest {
  scenario: SimulationScenario;
  policy: DispatchPolicy;
  num_ambulances: number;
  seed: number;
  duration_min: number;
  weights: DispatchWeights;
}

export interface CreateSimulationResponse {
  run_id: string;
  message: string;
  state: SimulationState;
}

export interface DispatchWeights {
  peso_tiempo: number; // default 0.45
  peso_demanda: number; // default 0.25
  peso_cobertura: number; // default 0.15
  peso_equidad: number; // default 0.15
}

export interface DispatchScoreCandidate {
  ambulancia: Ambulance;
  tiempo_estimado_min: number;
  demanda_futura_origen: number;
  perdida_cobertura: number;
  penalizacion_equidad: number;
  puntaje_total: number;
  explicacion: string;
}

export interface RelocationRecommendation {
  id: string;
  ambulancia_id: number;
  ambulancia_codigo: string;
  zona_origen_id: number;
  zona_origen_nombre: string;
  zona_destino_id: number;
  zona_destino_nombre: string;
  lat_destino: number;
  lng_destino: number;
  motivo: string;
  riesgo_demanda_destino: 'bajo' | 'medio' | 'alto';
  prioridad: 'alta' | 'media';
  timestamp_sim_min: number;
}
