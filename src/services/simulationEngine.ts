import {
  Ambulance,
  AmbulanceStatus,
  DemandPrediction,
  DispatchPolicy,
  DispatchWeights,
  Hospital,
  Incident,
  IncidentPriority,
  IncidentType,
  RelocationRecommendation,
  SimulationMetrics,
  SimulationScenario,
  Zone,
} from '../types';
import {
  calculateDistanceKm,
  calculateUrbanTravelTimeMin,
  getZoneForCoordinates,
  INITIAL_BASES,
  INITIAL_HOSPITALS,
  INITIAL_ZONES,
  INITIAL_AMBULANCES,
} from './cityData';
import {
  DEFAULT_DISPATCH_WEIGHTS,
  evaluateDynamicRelocations,
  selectAmbulancePredictive,
  selectAmbulanceTraditional,
  selectDestinationHospital,
} from './dispatchEngine';
import { generateZoneDemandPredictions } from './predictionEngine';
import { computeSimulationMetrics } from './statsEngine';

// Pseudo-Random Number Generator with Seed for Reproducibility
export class SeededPRNG {
  private seed: number;

  constructor(seed: number = 42) {
    this.seed = seed % 2147483647;
    if (this.seed <= 0) this.seed += 2147483646;
  }

  // Returns pseudo-random float [0, 1)
  next(): number {
    this.seed = (this.seed * 16807) % 2147483647;
    return (this.seed - 1) / 2147483646;
  }

  // Returns integer in [min, max]
  nextInt(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min;
  }

  // Poisson distribution random variate
  nextPoisson(lambda: number): number {
    if (lambda <= 0) return 0;
    const L = Math.exp(-lambda);
    let k = 0;
    let p = 1;
    do {
      k++;
      p *= this.next();
    } while (p > L);
    return k - 1;
  }
}

// 1. Generate Synthetic Incident Dataset
export function generateSyntheticIncidents(
  durationMinutes: number = 1440, // 24 hours by default
  scenario: SimulationScenario = 'dia_normal',
  seed: number = 12345,
  zones: Zone[] = INITIAL_ZONES
): Incident[] {
  const prng = new SeededPRNG(seed);
  const incidents: Incident[] = [];

  const types: IncidentType[] = [
    'accidente de tránsito',
    'emergencia cardíaca',
    'caída',
    'emergencia respiratoria',
    'trauma',
    'otro',
  ];

  const hourlyCircadian = [
    0.35, 0.25, 0.2, 0.18, 0.22, 0.35, 0.6, 0.85, 1.1, 1.25, 1.35, 1.45, 1.5, 1.4, 1.3, 1.35, 1.45, 1.6, 1.7, 1.65,
    1.4, 1.1, 0.75, 0.5,
  ];

  let idCounter = 1;

  // Step every 10 minutes to generate Poisson distributed incidents per zone
  for (let t = 0; t < durationMinutes; t += 10) {
    const hour = Math.floor((t / 60) % 24);
    const circadian = hourlyCircadian[hour] || 1.0;

    for (const zone of zones) {
      const baseHourly = zone.demanda_historica_diaria / 24;
      let lambdaInterval = (baseHourly * circadian * (10 / 60)); // expected calls in 10-min slot

      // Apply Scenario multipliers
      if (scenario === 'evento_masivo' && (zone.id === 9 || zone.id === 10 || zone.id === 13)) {
        if (hour >= 18 && hour <= 23) lambdaInterval *= 3.4; // Concert / match crowd
      } else if (scenario === 'tormenta') {
        lambdaInterval *= 1.4; // More accidents during storm
      } else if (scenario === 'brote_respiratorio' && zone.quintil_socioeconomico <= 2) {
        lambdaInterval *= 2.2; // Vulnerable sectors suffer more respiratory distress
      }

      const count = prng.nextPoisson(lambdaInterval);

      for (let i = 0; i < count; i++) {
        const exactMinute = t + Math.floor(prng.next() * 10);
        if (exactMinute >= durationMinutes) continue;

        // Random coordinate within zone centroid with jitter
        const latJitter = (prng.next() - 0.5) * 0.018;
        const lngJitter = (prng.next() - 0.5) * 0.022;
        const lat = zone.centroide[0] + latJitter;
        const lng = zone.centroide[1] + lngJitter;

        // Priority distribution
        let prioridad: IncidentPriority = 'media';
        const pRoll = prng.next();
        if (pRoll < 0.28) prioridad = 'alta';
        else if (pRoll > 0.75) prioridad = 'baja';

        // Incident Type distribution (influenced by scenario)
        let tipo: IncidentType = types[Math.floor(prng.next() * types.length)];
        if (scenario === 'tormenta' && prng.next() < 0.45) {
          tipo = 'accidente de tránsito';
        } else if (scenario === 'brote_respiratorio' && prng.next() < 0.55) {
          tipo = 'emergencia respiratoria';
        } else if (prioridad === 'alta' && prng.next() < 0.5) {
          tipo = prng.next() < 0.5 ? 'emergencia cardíaca' : 'trauma';
        }

        // On-scene care time
        let careTime = 12.0;
        if (prioridad === 'alta') careTime = 16.0 + prng.next() * 10.0;
        else if (prioridad === 'media') careTime = 10.0 + prng.next() * 8.0;
        else careTime = 6.0 + prng.next() * 6.0;

        if (scenario === 'brote_respiratorio' && tipo === 'emergencia respiratoria') {
          careTime += 8.0; // Stabilizing respiratory patients takes longer
        }

        // Hospital transfer probability
        let transferProb = 0.55;
        if (prioridad === 'alta') transferProb = 0.92;
        else if (prioridad === 'baja') transferProb = 0.25;
        const requiere_traslado = prng.next() < transferProb;

        const dateObj = new Date(2026, 7, 26, 0, 0, 0);
        dateObj.setMinutes(dateObj.getMinutes() + exactMinute);

        incidents.push({
          id: `INC-${String(idCounter++).padStart(4, '0')}`,
          fecha_hora: dateObj.toISOString(),
          sim_time_min: exactMinute,
          latitud: Number(lat.toFixed(5)),
          longitud: Number(lng.toFixed(5)),
          zona_id: zone.id,
          prioridad,
          tipo,
          estado: 'pendiente',
          ambulancia_id: null,
          hospital_id: null,
          tiempo_llamada: exactMinute,
          tiempo_despacho: null,
          tiempo_llegada: null,
          tiempo_respuesta_min: null,
          duracion_atencion_escena_min: Number(careTime.toFixed(1)),
          requiere_traslado,
          tiempo_llegada_hospital: null,
          tiempo_liberacion: null,
        });
      }
    }
  }

  // Sort strictly by simulation appearance minute
  incidents.sort((a, b) => a.sim_time_min - b.sim_time_min);
  return incidents;
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
  bases: typeof INITIAL_BASES;
  hospitals: Hospital[];
  ambulances: Ambulance[];
  incidents: Incident[];
  predictions: DemandPrediction[];
  relocation_recommendations: RelocationRecommendation[];
  event_logs: SimEventLog[];
  metrics: SimulationMetrics;
  weights: DispatchWeights;
}

// Full Discrete Event Simulator Engine
export class EMSSimulationEngine {
  public state: SimulationState;
  private allIncidentsQueue: Incident[] = [];

  constructor(
    scenario: SimulationScenario = 'dia_normal',
    policy: DispatchPolicy = 'predictivo',
    numAmbulances: number = 12,
    seed: number = 12345,
    durationMin: number = 720, // 12 hours
    weights: DispatchWeights = DEFAULT_DISPATCH_WEIGHTS
  ) {
    const zones = JSON.parse(JSON.stringify(INITIAL_ZONES)) as Zone[];
    const bases = JSON.parse(JSON.stringify(INITIAL_BASES)) as typeof INITIAL_BASES;
    const hospitals = JSON.parse(JSON.stringify(INITIAL_HOSPITALS)) as Hospital[];

    // Initialize requested number of ambulances
    const baseAmbulances = JSON.parse(JSON.stringify(INITIAL_AMBULANCES.slice(0, numAmbulances))) as Ambulance[];

    let traffic_factor = 1.0;
    let weather_factor = 1.0;
    if (scenario === 'tormenta') {
      traffic_factor = 1.4;
      weather_factor = 1.5;
    } else if (scenario === 'evento_masivo') {
      traffic_factor = 1.35;
    }

    const generatedIncidents = generateSyntheticIncidents(durationMin, scenario, seed, zones);
    this.allIncidentsQueue = JSON.parse(JSON.stringify(generatedIncidents));

    const initialPredictions = generateZoneDemandPredictions(0, scenario, zones);

    this.state = {
      sim_minute: 0,
      is_running: false,
      scenario,
      policy,
      seed,
      speed_multiplier: 1,
      total_duration_min: durationMin,
      traffic_factor,
      weather_factor,
      zones,
      bases,
      hospitals,
      ambulances: baseAmbulances,
      incidents: [],
      predictions: initialPredictions,
      relocation_recommendations: [],
      event_logs: [],
      metrics: computeSimulationMetrics([], 0, 0, zones),
      weights,
    };
  }

  // Step simulation forward by `deltaMinutes` (e.g. 1 minute per tick)
  public step(deltaMinutes: number = 1): SimulationState {
    const targetMin = this.state.sim_minute + deltaMinutes;

    while (this.state.sim_minute < targetMin && this.state.sim_minute < this.state.total_duration_min) {
      this.state.sim_minute += 1;
      const currentMin = this.state.sim_minute;

      // 1. Check for newly arriving incidents
      const newArriving = this.allIncidentsQueue.filter((inc) => inc.sim_time_min === currentMin);
      for (const inc of newArriving) {
        this.state.incidents.push(inc);
        this.addEventLog({
          id: `EV-${currentMin}-${inc.id}-CALL`,
          sim_time_min: currentMin,
          tipo_evento: 'incidente_creado',
          descripcion: `Nueva llamada: ${inc.tipo.toUpperCase()} en ${this.getZoneName(inc.zona_id)} (Prioridad: ${inc.prioridad.toUpperCase()}).`,
          incidente_id: inc.id,
          zona_nombre: this.getZoneName(inc.zona_id),
        });
      }

      // 2. Update Demand Predictions every 15 minutes
      if (currentMin % 15 === 0) {
        this.state.predictions = generateZoneDemandPredictions(currentMin, this.state.scenario, this.state.zones);

        // Evaluate Dynamic Relocations in Predictive Mode
        if (this.state.policy === 'predictivo') {
          const recs = evaluateDynamicRelocations(
            currentMin,
            this.state.ambulances,
            this.state.predictions,
            this.state.zones
          );
          this.state.relocation_recommendations = recs;

          // Auto-dispatch relocation for top urgent recommendation
          if (recs.length > 0) {
            const topReloc = recs[0];
            const amb = this.state.ambulances.find((a) => a.id === topReloc.ambulancia_id && a.estado === 'disponible');
            if (amb) {
              amb.estado = 'reubicándose';
              amb.target_lat = topReloc.lat_destino;
              amb.target_lng = topReloc.lng_destino;
              this.addEventLog({
                id: `EV-${currentMin}-RELOC-${amb.codigo}`,
                sim_time_min: currentMin,
                tipo_evento: 'reubicacion_iniciada',
                descripcion: `Reubicación preventiva: ${amb.codigo} transferida de ${topReloc.zona_origen_nombre} a ${topReloc.zona_destino_nombre}. Motivo: alto riesgo y déficit de cobertura.`,
                ambulancia_codigo: amb.codigo,
                zona_nombre: topReloc.zona_destino_nombre,
              });
            }
          }
        }
      }

      // 3. Dispatch pending incidents
      const pendingIncidents = this.state.incidents.filter((i) => i.estado === 'pendiente');
      for (const inc of pendingIncidents) {
        let dispatchResult;
        if (this.state.policy === 'predictivo') {
          dispatchResult = selectAmbulancePredictive(
            inc,
            this.state.ambulances,
            this.state.predictions,
            this.state.zones,
            this.state.weights,
            this.state.traffic_factor,
            this.state.weather_factor
          );
        } else {
          dispatchResult = selectAmbulanceTraditional(
            inc,
            this.state.ambulances,
            this.state.traffic_factor,
            this.state.weather_factor
          );
        }

        if (dispatchResult.selected) {
          const amb = this.state.ambulances.find((a) => a.id === dispatchResult.selected!.id)!;
          amb.estado = 'en ruta';
          amb.incidente_asignado_id = inc.id;
          amb.target_lat = inc.latitud;
          amb.target_lng = inc.longitud;

          const travelTime = calculateUrbanTravelTimeMin(
            amb.latitud,
            amb.longitud,
            inc.latitud,
            inc.longitud,
            amb.velocidad_kmh,
            this.state.traffic_factor,
            this.state.weather_factor
          );

          inc.estado = 'despachado';
          inc.ambulancia_id = amb.id;
          inc.tiempo_despacho = currentMin;
          inc.tiempo_llegada = currentMin + Number(travelTime.toFixed(1));
          inc.tiempo_respuesta_min = Number((inc.tiempo_llegada - inc.tiempo_llamada).toFixed(2));
          inc.explicacion_despacho = dispatchResult.rationale;
          inc.politica_usada = this.state.policy;

          const distKm = calculateDistanceKm(amb.latitud, amb.longitud, inc.latitud, inc.longitud) * 1.28;
          amb.kilometraje_total += distKm;

          this.addEventLog({
            id: `EV-${currentMin}-${inc.id}-DISP`,
            sim_time_min: currentMin,
            tipo_evento: 'ambulancia_despachada',
            descripcion: `${amb.codigo} despachada a ${inc.id} (${this.getZoneName(inc.zona_id)}). ETA: ${travelTime.toFixed(1)} min.`,
            ambulancia_codigo: amb.codigo,
            incidente_id: inc.id,
            zona_nombre: this.getZoneName(inc.zona_id),
          });
        }
      }

      // 4. Update ongoing ambulance lifecycles & positions
      for (const amb of this.state.ambulances) {
        // A) Ambulance reallocating
        if (amb.estado === 'reubicándose' && amb.target_lat && amb.target_lng) {
          const d = calculateDistanceKm(amb.latitud, amb.longitud, amb.target_lat, amb.target_lng);
          if (d < 0.25) {
            amb.latitud = amb.target_lat;
            amb.longitud = amb.target_lng;
            amb.estado = 'disponible';
            amb.zona_actual_id = getZoneForCoordinates(amb.latitud, amb.longitud, this.state.zones).id;
            amb.target_lat = undefined;
            amb.target_lng = undefined;
            this.addEventLog({
              id: `EV-${currentMin}-RELOC-END-${amb.codigo}`,
              sim_time_min: currentMin,
              tipo_evento: 'reubicacion_completada',
              descripcion: `${amb.codigo} completó reubicación y se encuentra DISPONIBLE en ${this.getZoneName(amb.zona_actual_id)}.`,
              ambulancia_codigo: amb.codigo,
            });
          } else {
            // Move interpolated step towards destination
            const stepRatio = 0.2;
            amb.latitud += (amb.target_lat - amb.latitud) * stepRatio;
            amb.longitud += (amb.target_lng - amb.longitud) * stepRatio;
          }
          continue;
        }

        if (!amb.incidente_asignado_id) continue;
        const inc = this.state.incidents.find((i) => i.id === amb.incidente_asignado_id);
        if (!inc) continue;

        // B) In transit to scene
        if (amb.estado === 'en ruta') {
          if (inc.tiempo_llegada !== null && currentMin >= inc.tiempo_llegada) {
            amb.estado = 'en escena';
            amb.latitud = inc.latitud;
            amb.longitud = inc.longitud;
            amb.zona_actual_id = inc.zona_id;
            inc.estado = 'en_atencion';

            this.addEventLog({
              id: `EV-${currentMin}-${inc.id}-SCENE`,
              sim_time_min: currentMin,
              tipo_evento: 'llegada_escena',
              descripcion: `${amb.codigo} arribó a la escena de ${inc.id} en ${inc.tiempo_respuesta_min?.toFixed(1)} min. Iniciando atención médica in-situ.`,
              ambulancia_codigo: amb.codigo,
              incidente_id: inc.id,
              zona_nombre: this.getZoneName(inc.zona_id),
            });
          } else if (inc.tiempo_llegada !== null) {
            // Smooth vehicle interpolation on map
            const totalTravelTime = (inc.tiempo_llegada - (inc.tiempo_despacho || currentMin)) || 1;
            const elapsed = currentMin - (inc.tiempo_despacho || currentMin);
            const frac = Math.min(0.95, Math.max(0.05, elapsed / totalTravelTime));
            amb.latitud += (inc.latitud - amb.latitud) * frac;
            amb.longitud += (inc.longitud - amb.longitud) * frac;
          }
        }
        // C) On scene care
        else if (amb.estado === 'en escena') {
          const sceneEndMin = (inc.tiempo_llegada || currentMin) + inc.duracion_atencion_escena_min;
          if (currentMin >= sceneEndMin) {
            if (inc.requiere_traslado) {
              const hospChoice = selectDestinationHospital(inc, this.state.hospitals, 'menor_costo_combinado', this.state.traffic_factor);
              inc.hospital_id = hospChoice.hospital.id;
              hospChoice.hospital.ocupacion = Math.min(hospChoice.hospital.capacidad, hospChoice.hospital.ocupacion + 1);

              const transportTime = calculateUrbanTravelTimeMin(
                inc.latitud,
                inc.longitud,
                hospChoice.hospital.latitud,
                hospChoice.hospital.longitud,
                amb.velocidad_kmh,
                this.state.traffic_factor,
                this.state.weather_factor
              );

              amb.estado = 'trasladando';
              amb.target_lat = hospChoice.hospital.latitud;
              amb.target_lng = hospChoice.hospital.longitud;
              inc.estado = 'trasladando';
              inc.tiempo_llegada_hospital = currentMin + Number(transportTime.toFixed(1));

              const distKm = calculateDistanceKm(inc.latitud, inc.longitud, hospChoice.hospital.latitud, hospChoice.hospital.longitud) * 1.28;
              amb.kilometraje_total += distKm;

              this.addEventLog({
                id: `EV-${currentMin}-${inc.id}-TRANS`,
                sim_time_min: currentMin,
                tipo_evento: 'inicio_traslado',
                descripcion: `${amb.codigo} traslada paciente a ${hospChoice.hospital.nombre}. ETA hospital: ${transportTime.toFixed(1)} min.`,
                ambulancia_codigo: amb.codigo,
                incidente_id: inc.id,
              });
            } else {
              // Resolved on scene without hospital transport
              this.freeAmbulance(amb, inc, currentMin);
            }
          }
        }
        // D) Patient transfer to Hospital
        else if (amb.estado === 'trasladando') {
          if (inc.tiempo_llegada_hospital !== null && currentMin >= inc.tiempo_llegada_hospital) {
            const hosp = this.state.hospitals.find((h) => h.id === inc.hospital_id) || this.state.hospitals[0];
            amb.estado = 'en hospital';
            amb.latitud = hosp.latitud;
            amb.longitud = hosp.longitud;
            amb.zona_actual_id = hosp.zona_id;

            this.addEventLog({
              id: `EV-${currentMin}-${inc.id}-HOSP`,
              sim_time_min: currentMin,
              tipo_evento: 'llegada_hospital',
              descripcion: `${amb.codigo} ingresó a emergencia de ${hosp.nombre}. Iniciando triage y entrega de guardia (${hosp.tiempo_espera_min.toFixed(0)} min).`,
              ambulancia_codigo: amb.codigo,
              incidente_id: inc.id,
            });
          }
        }
        // E) Handover in Hospital
        else if (amb.estado === 'en hospital') {
          const hosp = this.state.hospitals.find((h) => h.id === inc.hospital_id) || this.state.hospitals[0];
          const handoverCompleteMin = (inc.tiempo_llegada_hospital || currentMin) + hosp.tiempo_espera_min;
          if (currentMin >= handoverCompleteMin) {
            hosp.ocupacion = Math.max(0, hosp.ocupacion - 1);
            this.freeAmbulance(amb, inc, currentMin);
          }
        }
      }

      // 5. Update Aggregate Real-Time Metrics
      const totalDist = this.state.ambulances.reduce((acc, a) => acc + a.kilometraje_total, 0);
      const busyAmbulances = this.state.ambulances.filter((a) => a.estado !== 'disponible').length;
      const busyRatio = this.state.ambulances.length > 0 ? busyAmbulances / this.state.ambulances.length : 0;
      this.state.metrics = computeSimulationMetrics(this.state.incidents, totalDist, busyRatio, this.state.zones);
    }

    return this.state;
  }

  // Free ambulance back to available state and mark incident as completed
  private freeAmbulance(amb: Ambulance, inc: Incident, currentMin: number) {
    amb.estado = 'disponible';
    amb.incidente_asignado_id = null;
    amb.disponible_desde_min = currentMin;
    amb.incidentes_atendidos += 1;
    amb.target_lat = undefined;
    amb.target_lng = undefined;

    inc.estado = 'completado';
    inc.tiempo_liberacion = currentMin;

    this.addEventLog({
      id: `EV-${currentMin}-${inc.id}-FREE`,
      sim_time_min: currentMin,
      tipo_evento: 'ambulancia_liberada',
      descripcion: `${amb.codigo} completó atención de ${inc.id} y quedó DISPONIBLE en ${this.getZoneName(amb.zona_actual_id)}.`,
      ambulancia_codigo: amb.codigo,
      incidente_id: inc.id,
    });
  }

  private addEventLog(log: SimEventLog) {
    this.state.event_logs.unshift(log);
    if (this.state.event_logs.length > 200) {
      this.state.event_logs.pop();
    }
  }

  private getZoneName(zoneId: number): string {
    const z = this.state.zones.find((zone) => zone.id === zoneId);
    return z ? z.nombre : `Zona ${zoneId}`;
  }

  // Synchronous batch run for entire duration (ideal for instant comparative academic benchmark)
  public runComplete(): SimulationState {
    const stepSize = 1;
    while (this.state.sim_minute < this.state.total_duration_min) {
      this.step(stepSize);
    }
    return this.state;
  }
}
