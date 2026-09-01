import { DemandPrediction, SimulationScenario, Zone } from '../types';
import { INITIAL_ZONES } from './cityData';

export interface PredictionFeatureVector {
  zone_id: number;
  hour: number;
  day_of_week: number;
  population: number;
  vulnerability: number;
  quintil: number;
  historical_base_rate: number;
  rolling_traffic: number;
  weather_rain_factor: number;
  scenario_boost: number;
}

// Generate realistic simulated demand predictions for each zone across 15m, 30m, and 60m horizons
export function generateZoneDemandPredictions(
  simMinute: number,
  scenario: SimulationScenario = 'dia_normal',
  zones: Zone[] = INITIAL_ZONES
): DemandPrediction[] {
  const predictions: DemandPrediction[] = [];
  const hourOfDay = Math.floor((simMinute / 60) % 24);
  const dayOfWeek = Math.floor((simMinute / (60 * 24)) % 7); // 0 = Monday

  // Hourly circadian rhythm curve (peaks around 12:00-14:00 and 19:00-21:00)
  const hourlyFactors = [
    0.35, 0.25, 0.2, 0.18, 0.22, 0.35, 0.6, 0.85, 1.1, 1.25, 1.35, 1.45, 1.5, 1.4, 1.3, 1.35, 1.45, 1.6, 1.7, 1.65,
    1.4, 1.1, 0.75, 0.5,
  ];
  const circadianFactor = hourlyFactors[hourOfDay] || 1.0;

  // Scenario specific multipliers
  let scenarioFactor = 1.0;
  let weatherFactor = 1.0;
  let trafficFactor = 1.0;

  if (scenario === 'evento_masivo') {
    scenarioFactor = 1.65; // Massive concert / football match in central & stadium zones
    trafficFactor = 1.4;
  } else if (scenario === 'tormenta') {
    weatherFactor = 1.8; // Slick roads, accidents
    trafficFactor = 1.5;
  } else if (scenario === 'brote_respiratorio') {
    scenarioFactor = 1.75; // Heavy respiratory calls in vulnerable dense sectors
  }

  const horizons: (15 | 30 | 60)[] = [15, 30, 60];

  for (const horizon of horizons) {
    const horizonHourFraction = horizon / 60;

    for (const zone of zones) {
      // Base historical demand in events/hour
      const hourlyBaseRate = zone.demanda_historica_diaria / 24;

      // Vulnerability and population weight
      const popDensityWeight = zone.poblacion / 60000;
      const vulnWeight = 1.0 + zone.nivel_vulnerabilidad * 0.45;

      // Zone specific scenario sensitivity
      let zoneScenarioBoost = scenarioFactor;
      if (scenario === 'evento_masivo' && (zone.id === 9 || zone.id === 10 || zone.id === 13)) {
        zoneScenarioBoost = 2.8; // Specific high-density event zone
      } else if (scenario === 'brote_respiratorio' && zone.quintil_socioeconomico <= 2) {
        zoneScenarioBoost = 2.4; // Highly vulnerable periurban communities
      }

      // 1. Historical Moving Average Baseline
      const expectedBaselineHourly = hourlyBaseRate * circadianFactor;
      const demanda_predicha_base = Number((expectedBaselineHourly * horizonHourFraction).toFixed(2));

      // 2. Machine Learning Ensemble Forecast (Random Forest / Gradient Boost simulated regression)
      // Captures non-linear interactions between weather, vulnerability, density, and sudden scenario shocks
      const mlFeaturesInteractions =
        expectedBaselineHourly *
        popDensityWeight *
        vulnWeight *
        zoneScenarioBoost *
        (1 + (weatherFactor - 1) * 0.7) *
        (1 + (trafficFactor - 1) * 0.35);

      // Add slight deterministic pseudo-random variation based on zone.id and simMinute
      const noise = 1.0 + Math.sin(zone.id * 13.7 + simMinute * 0.05) * 0.08;
      const expectedMlHourly = mlFeaturesInteractions * noise;
      const demanda_predicha_ml = Number((expectedMlHourly * horizonHourFraction).toFixed(2));

      // Risk classification
      const hourlyExpectedRate = expectedMlHourly;
      let nivel_riesgo: 'bajo' | 'medio' | 'alto' = 'bajo';
      if (hourlyExpectedRate > 0.95 || (horizon === 15 && demanda_predicha_ml > 0.35)) {
        nivel_riesgo = 'alto';
      } else if (hourlyExpectedRate > 0.45 || (horizon === 15 && demanda_predicha_ml > 0.15)) {
        nivel_riesgo = 'medio';
      }

      // Probability of at least 1 incident in this horizon (Poisson model: 1 - e^(-lambda))
      const lambda = demanda_predicha_ml;
      const prob = Number((1 - Math.exp(-lambda)).toFixed(3));

      // Top contributing explainable factors
      const factors: string[] = [];
      if (zone.nivel_vulnerabilidad > 0.7) factors.push('Alta vulnerabilidad socioeconómica (Q' + zone.quintil_socioeconomico + ')');
      if (circadianFactor > 1.3) factors.push('Pico de demanda horaria (' + hourOfDay + ':00 hrs)');
      if (scenario === 'evento_masivo' && (zone.id === 9 || zone.id === 10 || zone.id === 13)) {
        factors.push('Aglomeración por evento masivo en sector céntrico');
      }
      if (scenario === 'tormenta') factors.push('Condición climática adversa (precipitación/calzada mojada)');
      if (scenario === 'brote_respiratorio' && zone.quintil_socioeconomico <= 2) {
        factors.push('Brote epidémico respiratorio en sector vulnerable');
      }
      if (factors.length === 0) factors.push('Demanda demográfica habitual');

      predictions.push({
        zona_id: zone.id,
        zona_nombre: zone.nombre,
        horizonte_min: horizon,
        demanda_predicha_base,
        demanda_predicha_ml,
        nivel_riesgo,
        probabilidad_incidente: prob,
        factores_principales: factors,
        fecha_generacion: new Date().toISOString(),
      });
    }
  }

  return predictions;
}
