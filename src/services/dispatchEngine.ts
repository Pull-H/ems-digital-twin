import {
  Ambulance,
  DemandPrediction,
  DispatchPolicy,
  DispatchScoreCandidate,
  DispatchWeights,
  Hospital,
  Incident,
  RelocationRecommendation,
  Zone,
} from '../types';
import { calculateUrbanTravelTimeMin, getZoneForCoordinates, INITIAL_BASES, INITIAL_HOSPITALS, INITIAL_ZONES } from './cityData';

export const DEFAULT_DISPATCH_WEIGHTS: DispatchWeights = {
  peso_tiempo: 0.45,
  peso_demanda: 0.25,
  peso_cobertura: 0.15,
  peso_equidad: 0.15,
};

// 1. Traditional Dispatch Policy: Nearest Available Ambulance
export function selectAmbulanceTraditional(
  incident: Incident,
  ambulances: Ambulance[],
  trafficFactor = 1.0,
  weatherFactor = 1.0
): { selected: Ambulance | null; candidates: DispatchScoreCandidate[]; rationale: string } {
  const available = ambulances.filter((a) => a.estado === 'disponible');
  if (available.length === 0) {
    return {
      selected: null,
      candidates: [],
      rationale: 'No hay ambulancias disponibles en la red EMS para despacho inmediato.',
    };
  }

  const candidates: DispatchScoreCandidate[] = available.map((amb) => {
    const timeMin = calculateUrbanTravelTimeMin(
      amb.latitud,
      amb.longitud,
      incident.latitud,
      incident.longitud,
      amb.velocidad_kmh,
      trafficFactor,
      weatherFactor
    );

    return {
      ambulancia: amb,
      tiempo_estimado_min: Number(timeMin.toFixed(2)),
      demanda_futura_origen: 0,
      perdida_cobertura: 0,
      penalizacion_equidad: 0,
      puntaje_total: Number(timeMin.toFixed(2)),
      explicacion: `Distancia directa: ETA ${timeMin.toFixed(1)} min`,
    };
  });

  candidates.sort((a, b) => a.tiempo_estimado_min - b.tiempo_estimado_min);
  const best = candidates[0];

  const rationale = `[Despacho Tradicional] Se asignó ${best.ambulancia.codigo} por ser la unidad disponible con menor tiempo de arribo estimado (${best.tiempo_estimado_min.toFixed(1)} min).`;

  return {
    selected: best.ambulancia,
    candidates,
    rationale,
  };
}

// 2. Predictive Dispatch with Coverage & Equity
export function selectAmbulancePredictive(
  incident: Incident,
  ambulances: Ambulance[],
  predictions: DemandPrediction[],
  zones: Zone[] = INITIAL_ZONES,
  weights: DispatchWeights = DEFAULT_DISPATCH_WEIGHTS,
  trafficFactor = 1.0,
  weatherFactor = 1.0
): { selected: Ambulance | null; candidates: DispatchScoreCandidate[]; rationale: string } {
  const available = ambulances.filter((a) => a.estado === 'disponible');
  if (available.length === 0) {
    return {
      selected: null,
      candidates: [],
      rationale: 'No hay ambulancias disponibles en la red EMS para despacho inmediato.',
    };
  }

  const zoneMap = new Map<number, Zone>();
  zones.forEach((z) => zoneMap.set(z.id, z));

  const targetZone = zoneMap.get(incident.zona_id) || getZoneForCoordinates(incident.latitud, incident.longitud, zones);

  // Predictions for 15-min horizon
  const pred15Map = new Map<number, DemandPrediction>();
  predictions.filter((p) => p.horizonte_min === 15).forEach((p) => pred15Map.set(p.zona_id, p));

  // Count available ambulances in each zone/base
  const availableInZone = new Map<number, number>();
  zones.forEach((z) => availableInZone.set(z.id, 0));
  available.forEach((amb) => {
    const count = availableInZone.get(amb.zona_actual_id) || 0;
    availableInZone.set(amb.zona_actual_id, count + 1);
  });

  const candidates: DispatchScoreCandidate[] = available.map((amb) => {
    const originZone = zoneMap.get(amb.zona_actual_id) || zones[0];
    const timeMin = calculateUrbanTravelTimeMin(
      amb.latitud,
      amb.longitud,
      incident.latitud,
      incident.longitud,
      amb.velocidad_kmh,
      trafficFactor,
      weatherFactor
    );

    // 1. Expected future demand in origin zone (0 - 2.0 scaled)
    const originPred = pred15Map.get(originZone.id)?.demanda_predicha_ml || 0.2;
    const demanda_futura_origen = originPred * 10; // scaled

    // 2. Loss of coverage penalty: how many ambulances left in origin zone if this one leaves?
    const ambCountOrigin = availableInZone.get(originZone.id) || 1;
    // If ambCountOrigin === 1, sending this ambulance leaves origin zone with 0 coverage!
    const perdida_cobertura = ambCountOrigin <= 1 ? 8.0 * (originZone.nivel_vulnerabilidad + 0.5) : 1.0;

    // 3. Equity penalty: prioritizing underserved / high vulnerability zones (Q1, Q2)
    // If target zone is high vulnerability (Q1) and origin zone is Q5, equity penalty is low (favorable).
    // If incident is high priority (alta), time weight dominates.
    const priorityWeight = incident.prioridad === 'alta' ? 1.4 : incident.prioridad === 'media' ? 1.0 : 0.8;
    const vulnDifference = originZone.nivel_vulnerabilidad - targetZone.nivel_vulnerabilidad;
    // Lower score is better: if target is vulnerable, we reward dispatching from wealthy zones with surplus
    const penalizacion_equidad = Math.max(0, 5.0 * (1 - targetZone.nivel_vulnerabilidad) + vulnDifference * 3.0);

    // Multi-objective score function
    const puntaje_total =
      weights.peso_tiempo * (timeMin * priorityWeight) +
      weights.peso_demanda * demanda_futura_origen +
      weights.peso_cobertura * perdida_cobertura +
      weights.peso_equidad * penalizacion_equidad;

    let explicacion = `ETA: ${timeMin.toFixed(1)}m`;
    if (ambCountOrigin <= 1 && originZone.id !== targetZone.id) {
      explicacion += ` | Alerta: Deja ${originZone.codigo} con 0 unidades`;
    } else {
      explicacion += ` | Cobertura origen preservada (${ambCountOrigin - 1} restantes)`;
    }

    return {
      ambulancia: amb,
      tiempo_estimado_min: Number(timeMin.toFixed(2)),
      demanda_futura_origen: Number(demanda_futura_origen.toFixed(2)),
      perdida_cobertura: Number(perdida_cobertura.toFixed(2)),
      penalizacion_equidad: Number(penalizacion_equidad.toFixed(2)),
      puntaje_total: Number(puntaje_total.toFixed(2)),
      explicacion,
    };
  });

  candidates.sort((a, b) => a.puntaje_total - b.puntaje_total);
  const best = candidates[0];
  const originBestZone = zoneMap.get(best.ambulancia.zona_actual_id);

  const rationale = `[Despacho Predictivo] Se seleccionó la ambulancia ${best.ambulancia.codigo} (Score: ${best.puntaje_total.toFixed(1)}, ETA: ${best.tiempo_estimado_min.toFixed(1)} min). Razón: equilibra proximidad con preservación de cobertura en ${originBestZone?.nombre || 'origen'} y equidad en ${targetZone.nombre} (Q${targetZone.quintil_socioeconomico}).`;

  return {
    selected: best.ambulancia,
    candidates,
    rationale,
  };
}

// 3. Dynamic Relocation Evaluator (runs every 15 simulation minutes)
export function evaluateDynamicRelocations(
  simMinute: number,
  ambulances: Ambulance[],
  predictions: DemandPrediction[],
  zones: Zone[] = INITIAL_ZONES
): RelocationRecommendation[] {
  const recommendations: RelocationRecommendation[] = [];
  const available = ambulances.filter((a) => a.estado === 'disponible');
  if (available.length < 3) return []; // Don't relocate if network is critically depleted

  const pred15 = predictions.filter((p) => p.horizonte_min === 15);
  const zoneMap = new Map<number, Zone>();
  zones.forEach((z) => zoneMap.set(z.id, z));

  // Count available in each zone
  const ambByZone = new Map<number, Ambulance[]>();
  zones.forEach((z) => ambByZone.set(z.id, []));
  available.forEach((a) => {
    const list = ambByZone.get(a.zona_actual_id) || [];
    list.push(a);
    ambByZone.set(a.zona_actual_id, list);
  });

  // Find surplus zones (zones with >= 2 available ambulances)
  const surplusZones = Array.from(ambByZone.entries())
    .filter(([_, list]) => list.length >= 2)
    .map(([zoneId, list]) => ({ zone: zoneMap.get(zoneId)!, ambulances: list }));

  if (surplusZones.length === 0) return [];

  // Find high risk underserved zones (risk === 'alto' or high expected demand, with 0 available ambulances)
  const highRiskDeficitZones = pred15
    .filter((p) => {
      const ambCount = (ambByZone.get(p.zona_id) || []).length;
      return (p.nivel_riesgo === 'alto' || p.demanda_predicha_ml > 0.3) && ambCount === 0;
    })
    .map((p) => ({
      zone: zoneMap.get(p.zona_id)!,
      prediction: p,
    }));

  // Match surplus ambulances to deficit zones
  for (const deficit of highRiskDeficitZones) {
    if (surplusZones.length === 0) break;

    // Pick closest surplus zone
    surplusZones.sort((a, b) => {
      const distA = calculateUrbanTravelTimeMin(a.zone.centroide[0], a.zone.centroide[1], deficit.zone.centroide[0], deficit.zone.centroide[1]);
      const distB = calculateUrbanTravelTimeMin(b.zone.centroide[0], b.zone.centroide[1], deficit.zone.centroide[0], deficit.zone.centroide[1]);
      return distA - distB;
    });

    const donor = surplusZones[0];
    if (donor.ambulances.length <= 1) {
      surplusZones.shift();
      continue;
    }

    const ambToMove = donor.ambulances.pop()!;
    const travelTime = calculateUrbanTravelTimeMin(
      donor.zone.centroide[0],
      donor.zone.centroide[1],
      deficit.zone.centroide[0],
      deficit.zone.centroide[1]
    );

    recommendations.push({
      id: `RELOC-${simMinute}-${ambToMove.codigo}-${deficit.zone.id}`,
      ambulancia_id: ambToMove.id,
      ambulancia_codigo: ambToMove.codigo,
      zona_origen_id: donor.zone.id,
      zona_origen_nombre: donor.zone.nombre,
      zona_destino_id: deficit.zone.id,
      zona_destino_nombre: deficit.zone.nombre,
      lat_destino: deficit.zone.centroide[0],
      lng_destino: deficit.zone.centroide[1],
      motivo: `Reubicación preventiva: ${deficit.zone.nombre} presenta riesgo alto (${deficit.prediction.demanda_predicha_ml} llamadas esperadas) sin unidades locales. Origen ${donor.zone.codigo} cuenta con excedente (${donor.ambulances.length + 1} unidades).`,
      riesgo_demanda_destino: deficit.prediction.nivel_riesgo,
      prioridad: deficit.zone.quintil_socioeconomico <= 2 ? 'alta' : 'media',
      timestamp_sim_min: simMinute,
    });
  }

  return recommendations;
}

// 4. Optimal Hospital Selection (Nearest vs Multi-Criteria Capacity & Trauma Match)
export function selectDestinationHospital(
  incident: Incident,
  hospitals: Hospital[] = INITIAL_HOSPITALS,
  strategy: 'mas_cercano' | 'menor_costo_combinado' = 'menor_costo_combinado',
  trafficFactor = 1.0
): { hospital: Hospital; explicacion: string } {
  if (strategy === 'mas_cercano') {
    let closest = hospitals[0];
    let minTime = Infinity;
    for (const hosp of hospitals) {
      const t = calculateUrbanTravelTimeMin(incident.latitud, incident.longitud, hosp.latitud, hosp.longitud, 45, trafficFactor);
      if (t < minTime) {
        minTime = t;
        closest = hosp;
      }
    }
    return {
      hospital: closest,
      explicacion: `Hospital más próximo en tiempo de traslado (${minTime.toFixed(1)} min).`,
    };
  }

  // Multi-criteria cost evaluation: Travel Time + Occupancy Penalty + Trauma Incompatibility
  const evaluated = hospitals.map((hosp) => {
    const travelTime = calculateUrbanTravelTimeMin(incident.latitud, incident.longitud, hosp.latitud, hosp.longitud, 45, trafficFactor);
    const occupancyRatio = hosp.capacidad > 0 ? hosp.ocupacion / hosp.capacidad : 1.0;
    // High penalty if hospital is > 85% full
    const occupancyPenalty = occupancyRatio > 0.85 ? (occupancyRatio - 0.85) * 40 + hosp.tiempo_espera_min : hosp.tiempo_espera_min * 0.5;

    // Trauma matching: Severe trauma or cardiac arrests need Level 1 or 2
    let traumaMismatchPenalty = 0;
    if ((incident.tipo === 'trauma' || incident.tipo === 'emergencia cardíaca') && incident.prioridad === 'alta') {
      if (hosp.nivel_trauma === 3) traumaMismatchPenalty = 18.0; // Avoid level 3 for critical trauma
      if (hosp.nivel_trauma === 2) traumaMismatchPenalty = 4.0;
    }

    const totalCost = travelTime + occupancyPenalty + traumaMismatchPenalty;
    return {
      hospital: hosp,
      travelTime,
      occupancyRatio,
      totalCost,
    };
  });

  evaluated.sort((a, b) => a.totalCost - b.totalCost);
  const best = evaluated[0];

  return {
    hospital: best.hospital,
    explicacion: `Hospital óptimo: ${best.hospital.nombre} (Costo: ${best.totalCost.toFixed(1)}, Traslado: ${best.travelTime.toFixed(1)}m, Ocupación: ${(best.occupancyRatio * 100).toFixed(0)}%, Nivel Trauma: ${best.hospital.nivel_trauma}).`,
  };
}
