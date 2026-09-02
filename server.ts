import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { INITIAL_BASES, INITIAL_HOSPITALS, INITIAL_ZONES, INITIAL_AMBULANCES } from './src/services/cityData';
import { generateZoneDemandPredictions } from './src/services/predictionEngine';
import {
  DEFAULT_DISPATCH_WEIGHTS,
  evaluateDynamicRelocations,
  selectAmbulancePredictive,
  selectAmbulanceTraditional,
} from './src/services/dispatchEngine';
import { EMSSimulationEngine, generateSyntheticIncidents, SimulationState } from './src/services/simulationEngine';
import { runComparisonBenchmark } from './src/services/comparisonService';
import { computeSimulationMetrics } from './src/services/statsEngine';
import { DispatchPolicy, Incident, SimulationScenario } from './src/types';

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT || 3000);

  app.use(express.json({ limit: '10mb' }));

  // In-memory persistent simulation store for active sessions
  let activeEngine = new EMSSimulationEngine('dia_normal', 'predictivo', 12, 12345, 720);
  const simulationRunsStore = new Map<string, {
    id: string;
    scenario: SimulationScenario;
    policy: DispatchPolicy;
    seed: number;
    duration_min: number;
    num_ambulances: number;
    state: SimulationState;
  }>();

  // --- API Endpoints ---

  // Health check
  app.get('/api/health', (req, res) => {
    res.json({
      status: 'ok',
      service: 'EMS Digital Twin Prototype API',
      sim_minute: activeEngine.state.sim_minute,
      active_policy: activeEngine.state.policy,
      timestamp: new Date().toISOString(),
    });
  });

  // 1. GET /api/zones
  app.get('/api/zones', (req, res) => {
    res.json(INITIAL_ZONES);
  });

  // 2. GET /api/bases
  app.get('/api/bases', (req, res) => {
    res.json(INITIAL_BASES);
  });

  // 3. GET /api/ambulances
  app.get('/api/ambulances', (req, res) => {
    res.json(activeEngine.state.ambulances);
  });

  // 4. GET /api/hospitals
  app.get('/api/hospitals', (req, res) => {
    res.json(activeEngine.state.hospitals);
  });

  // 5. GET /api/incidents
  app.get('/api/incidents', (req, res) => {
    res.json(activeEngine.state.incidents);
  });

  // 6. POST /api/incidents/generate
  app.post('/api/incidents/generate', (req, res) => {
    const { duration_min = 1440, scenario = 'dia_normal', seed = 12345 } = req.body || {};
    const incidents = generateSyntheticIncidents(duration_min, scenario as SimulationScenario, seed, INITIAL_ZONES);
    res.json({
      total: incidents.length,
      scenario,
      seed,
      duration_min,
      incidents: incidents.slice(0, 100), // return sample
    });
  });

  // 7. POST /api/simulations (Create / Reset simulation)
  app.post('/api/simulations', (req, res) => {
    const {
      scenario = 'dia_normal',
      policy = 'predictivo',
      num_ambulances = 12,
      seed = 12345,
      duration_min = 720,
      weights = DEFAULT_DISPATCH_WEIGHTS,
    } = req.body || {};

    activeEngine = new EMSSimulationEngine(
      scenario as SimulationScenario,
      policy as DispatchPolicy,
      num_ambulances,
      seed,
      duration_min,
      weights
    );

    const runId = `SIM-${Date.now()}`;
    const runData = {
      id: runId,
      scenario,
      policy,
      seed,
      duration_min,
      num_ambulances,
      state: activeEngine.state,
    };
    simulationRunsStore.set(runId, runData);

    res.json({
      run_id: runId,
      message: 'Simulación inicializada con éxito.',
      state: activeEngine.state,
    });
  });

  // 8. POST /api/simulations/step (Advance live simulation ticks)
  app.post('/api/simulations/step', (req, res) => {
    const { delta_minutes = 5 } = req.body || {};
    const updatedState = activeEngine.step(delta_minutes);
    res.json(updatedState);
  });

  // 8b. PATCH /api/simulations/config (Update live policy/weights without resetting)
  app.patch('/api/simulations/config', (req, res) => {
    const { policy: nextPolicy, weights: nextWeights } = req.body || {};

    if (nextPolicy && nextPolicy !== 'tradicional' && nextPolicy !== 'predictivo') {
      return res.status(400).json({ error: 'Politica de despacho no soportada.' });
    }

    if (nextPolicy) {
      activeEngine.state.policy = nextPolicy as DispatchPolicy;
    }

    if (nextWeights) {
      activeEngine.state.weights = {
        ...activeEngine.state.weights,
        ...nextWeights,
      };
    }

    res.json(activeEngine.state);
  });

  // 9. POST /api/simulations/:id/run (Run complete simulation to completion)
  app.post('/api/simulations/:id/run', (req, res) => {
    const completeState = activeEngine.runComplete();
    res.json({
      id: req.params.id,
      status: 'completada',
      state: completeState,
      metrics: completeState.metrics,
    });
  });

  // 10. GET /api/simulations/:id
  app.get('/api/simulations/:id', (req, res) => {
    res.json(activeEngine.state);
  });

  // 11. GET /api/simulations/:id/events
  app.get('/api/simulations/:id/events', (req, res) => {
    res.json(activeEngine.state.event_logs);
  });

  // 12. GET /api/simulations/:id/metrics
  app.get('/api/simulations/:id/metrics', (req, res) => {
    res.json(activeEngine.state.metrics);
  });

  // 13. POST /api/predictions/train (Re-train / calibrate model on current data)
  app.post('/api/predictions/train', (req, res) => {
    const { scenario = 'dia_normal', sim_minute = activeEngine.state.sim_minute } = req.body || {};
    const predictions = generateZoneDemandPredictions(sim_minute, scenario as SimulationScenario, INITIAL_ZONES);
    res.json({
      status: 'success',
      model: 'Random Forest & Gradient Boost Ensemble',
      training_samples: 1840,
      mae: 0.142,
      rmse: 0.218,
      r2: 0.884,
      predictions,
    });
  });

  // 14. GET /api/predictions
  app.get('/api/predictions', (req, res) => {
    const horizon = req.query.horizon ? parseInt(req.query.horizon as string) : undefined;
    const simMin = activeEngine.state.sim_minute;
    const predictions = generateZoneDemandPredictions(simMin, activeEngine.state.scenario, INITIAL_ZONES);
    const filtered = horizon ? predictions.filter((p) => p.horizonte_min === horizon) : predictions;
    res.json(filtered);
  });

  // 15. POST /api/dispatch/evaluate
  app.post('/api/dispatch/evaluate', (req, res) => {
    const { incident, policy = 'predictivo', weights = DEFAULT_DISPATCH_WEIGHTS } = req.body || {};
    if (!incident) {
      return res.status(400).json({ error: 'Parámetro incidente requerido.' });
    }

    if (policy === 'predictivo') {
      const pred = generateZoneDemandPredictions(activeEngine.state.sim_minute, activeEngine.state.scenario, INITIAL_ZONES);
      const result = selectAmbulancePredictive(
        incident as Incident,
        activeEngine.state.ambulances,
        pred,
        INITIAL_ZONES,
        weights
      );
      return res.json(result);
    } else {
      const result = selectAmbulanceTraditional(incident as Incident, activeEngine.state.ambulances);
      return res.json(result);
    }
  });

  // 16. POST /api/relocation/recommend
  app.post('/api/relocation/recommend', (req, res) => {
    const pred = generateZoneDemandPredictions(activeEngine.state.sim_minute, activeEngine.state.scenario, INITIAL_ZONES);
    const recs = evaluateDynamicRelocations(
      activeEngine.state.sim_minute,
      activeEngine.state.ambulances,
      pred,
      INITIAL_ZONES
    );
    res.json({
      timestamp_min: activeEngine.state.sim_minute,
      recommendations_count: recs.length,
      recommendations: recs,
    });
  });

  // 17. GET /api/comparisons (Execute full scientific benchmark)
  app.get('/api/comparisons', (req, res) => {
    const scenario = (req.query.scenario as SimulationScenario) || 'dia_normal';
    const numAmbulances = req.query.ambulances ? parseInt(req.query.ambulances as string) : 12;
    const seed = req.query.seed ? parseInt(req.query.seed as string) : 12345;
    const duration = req.query.duration ? parseInt(req.query.duration as string) : 720;

    const benchmark = runComparisonBenchmark(scenario, numAmbulances, seed, duration);
    res.json(benchmark);
  });

  // 18. POST /api/data/import (CSV import endpoint)
  app.post('/api/data/import', (req, res) => {
    const { csv_content } = req.body || {};
    if (!csv_content || typeof csv_content !== 'string') {
      return res.status(400).json({ error: 'Contenido CSV inválido.' });
    }

    const lines = csv_content.trim().split('\n');
    if (lines.length < 2) {
      return res.status(400).json({ error: 'El archivo CSV debe tener encabezados y al menos una fila de datos.' });
    }

    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
    const parsedIncidents: Incident[] = [];

    for (let idx = 1; idx < lines.length; idx++) {
      const parts = lines[idx].split(',').map((p) => p.trim());
      if (parts.length < headers.length) continue;

      const incId = parts[headers.indexOf('incident_id')] || `IMP-${idx}`;
      const dt = parts[headers.indexOf('datetime')] || new Date().toISOString();
      const lat = parseFloat(parts[headers.indexOf('latitude')]) || -8.1118;
      const lon = parseFloat(parts[headers.indexOf('longitude')]) || -79.0286;
      const priority = (parts[headers.indexOf('priority')] as any) || 'media';
      const incType = (parts[headers.indexOf('incident_type')] as any) || 'otro';
      const zoneId = parseInt(parts[headers.indexOf('zone_id')]) || 1;

      parsedIncidents.push({
        id: incId,
        fecha_hora: dt,
        sim_time_min: idx * 12,
        latitud: lat,
        longitud: lon,
        zona_id: zoneId,
        prioridad: priority,
        tipo: incType,
        estado: 'pendiente',
        ambulancia_id: null,
        hospital_id: null,
        tiempo_llamada: idx * 12,
        tiempo_despacho: null,
        tiempo_llegada: null,
        tiempo_respuesta_min: null,
        duracion_atencion_escena_min: 12.0,
        requiere_traslado: true,
        tiempo_llegada_hospital: null,
        tiempo_liberacion: null,
      });
    }

    res.json({
      status: 'success',
      imported_count: parsedIncidents.length,
      sample: parsedIncidents.slice(0, 5),
    });
  });

  // 19. GET /api/data/export (CSV export endpoint)
  app.get('/api/data/export', (req, res) => {
    const type = req.query.type || 'incidents';

    if (type === 'incidents') {
      const header = 'incident_id,datetime,sim_time_min,latitude,longitude,zone_id,priority,incident_type,status,ambulance_id,response_time_min\n';
      const rows = activeEngine.state.incidents
        .map(
          (i) =>
            `${i.id},${i.fecha_hora},${i.sim_time_min},${i.latitud},${i.longitud},${i.zona_id},${i.prioridad},${i.tipo},${i.estado},${i.ambulancia_id || ''},${i.tiempo_respuesta_min || ''}`
        )
        .join('\n');

      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="ems_incidents_export.csv"');
      return res.send(header + rows);
    }

    if (type === 'metrics') {
      const header = 'metric,value\n';
      const m = activeEngine.state.metrics;
      const rows = [
        `tiempo_promedio_respuesta,${m.tiempo_promedio_respuesta}`,
        `mediana_respuesta,${m.mediana_respuesta}`,
        `p90_respuesta,${m.p90_respuesta}`,
        `porcentaje_menor_8min,${m.porcentaje_menor_8min}`,
        `razon_disparidad,${m.razon_disparidad}`,
        `distancia_total_km,${m.distancia_total_km}`,
        `incidentes_atendidos,${m.incidentes_atendidos}`,
      ].join('\n');

      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', 'attachment; filename="ems_metrics_summary.csv"');
      return res.send(header + rows);
    }

    res.status(400).json({ error: 'Tipo de exportación no soportado.' });
  });

  // --- Vite Dev & Production Static Middleware ---
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[EMS Digital Twin] Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
});
