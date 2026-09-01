import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { LiveKPIHeader } from './components/LiveKPIHeader';
import { MapView } from './components/MapView';
import { SimulationControls } from './components/SimulationControls';
import { PredictionPanel } from './components/PredictionPanel';
import { ComparisonView } from './components/ComparisonView';
import { StatisticalPanel } from './components/StatisticalPanel';
import { DataManagement } from './components/DataManagement';
import { PythonArchitectureViewer } from './components/PythonArchitectureViewer';

import {
  Ambulance,
  DemandPrediction,
  DispatchPolicy,
  DispatchWeights,
  EMSBase,
  Hospital,
  Incident,
  RelocationRecommendation,
  SimulationMetrics,
  SimulationScenario,
  StatisticalTestResult,
  Zone,
} from './types';
import { ZONES_DATA, EMS_BASES, HOSPITALS } from './services/cityData';
import { EMSSimulationEngine, SimEventLog } from './services/simulationEngine';
import { ComparisonBenchmarkResult, runComparisonBenchmark } from './services/comparisonService';

export const App: React.FC = () => {
  // Navigation
  const [activeTab, setActiveTab] = useState<string>('map');

  // Simulation parameters
  const [scenario, setScenario] = useState<SimulationScenario>('dia_normal');
  const [policy, setPolicy] = useState<DispatchPolicy>('predictivo');
  const [numAmbulances, setNumAmbulances] = useState<number>(12);
  const [seed, setSeed] = useState<number>(12345);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(5);
  const [weights, setWeights] = useState<DispatchWeights>({
    peso_tiempo: 0.4,
    peso_demanda: 0.25,
    peso_cobertura: 0.15,
    peso_equidad: 0.2,
  });

  // Simulation engine instance (ref to avoid re-renders)
  const engineRef = useRef<EMSSimulationEngine | null>(null);

  // Live state
  const [simMinute, setSimMinute] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [zones] = useState<Zone[]>(ZONES_DATA);
  const [bases] = useState<EMSBase[]>(EMS_BASES);
  const [hospitals, setHospitals] = useState<Hospital[]>(HOSPITALS);
  const [ambulances, setAmbulances] = useState<Ambulance[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<SimulationMetrics>({
    tiempo_promedio_respuesta: 6.8,
    mediana_respuesta: 6.2,
    p90_respuesta: 11.5,
    porcentaje_menor_8min: 82.5,
    total_incidentes: 0,
    incidentes_atendidos: 0,
    incidentes_pendientes: 0,
    por_quintil: {
      1: { quintil: 1, tiempo_promedio_respuesta: 7.1, porcentaje_menor_8min: 80.0, total_incidentes: 0 },
      2: { quintil: 2, tiempo_promedio_respuesta: 6.9, porcentaje_menor_8min: 81.5, total_incidentes: 0 },
      3: { quintil: 3, tiempo_promedio_respuesta: 6.8, porcentaje_menor_8min: 82.0, total_incidentes: 0 },
      4: { quintil: 4, tiempo_promedio_respuesta: 6.5, porcentaje_menor_8min: 84.0, total_incidentes: 0 },
      5: { quintil: 5, tiempo_promedio_respuesta: 6.2, porcentaje_menor_8min: 86.0, total_incidentes: 0 },
    },
    razon_disparidad: 1.15,
    diferencia_max_min_quintiles: 0.9,
    distancia_total_km: 0,
    utilizacion_ambulancias: 0.35,
  });
  const [predictions, setPredictions] = useState<DemandPrediction[]>([]);
  const [relocations, setRelocations] = useState<RelocationRecommendation[]>([]);
  const [eventLogs, setEventLogs] = useState<SimEventLog[]>([]);

  // Selection state
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [selectedAmbulance, setSelectedAmbulance] = useState<Ambulance | null>(null);

  // Comparison & Statistical benchmarks
  const [benchmarkResult, setBenchmarkResult] = useState<ComparisonBenchmarkResult | null>(null);
  const [isBenchmarkLoading, setIsBenchmarkLoading] = useState<boolean>(false);

  // Sync state from engine
  const syncStateFromEngine = useCallback(() => {
    if (!engineRef.current) return;
    const engine = engineRef.current;
    setSimMinute(engine.state.sim_minute);
    setAmbulances([...engine.state.ambulances]);
    setIncidents([...engine.state.incidents]);
    setHospitals([...engine.state.hospitals]);
    setMetrics({ ...engine.state.metrics });
    setPredictions([...engine.state.predictions]);
    setRelocations([...engine.state.relocation_recommendations]);
    setEventLogs([...engine.state.event_logs]);
  }, []);

  // Initialize engine
  const initEngine = useCallback(
    (customScenario = scenario, customPolicy = policy, customNumAmbs = numAmbulances, customSeed = seed) => {
      const newEngine = new EMSSimulationEngine(
        customScenario,
        customPolicy,
        customNumAmbs,
        customSeed,
        720,
        weights
      );

      // Warm up with 45 minutes of baseline operations
      newEngine.step(45);

      engineRef.current = newEngine;
      syncStateFromEngine();
    },
    [scenario, policy, numAmbulances, seed, weights, syncStateFromEngine]
  );

  // Run benchmark
  const handleRunBenchmark = useCallback(async () => {
    setIsBenchmarkLoading(true);
    try {
      // Run paired benchmark (12 hours = 720 min)
      const result = runComparisonBenchmark(scenario, numAmbulances, seed, 720, weights);
      setBenchmarkResult(result);
    } catch (err) {
      console.error('Error running benchmark:', err);
    } finally {
      setIsBenchmarkLoading(false);
    }
  }, [scenario, seed, numAmbulances, weights]);

  // Initial mount
  useEffect(() => {
    initEngine();
    handleRunBenchmark();
  }, []);

  // Step simulation function
  const handleStep = useCallback(
    (deltaMin: number) => {
      if (!engineRef.current) return;
      engineRef.current.step(deltaMin);
      syncStateFromEngine();
    },
    [syncStateFromEngine]
  );

  // Play/Pause ticker
  useEffect(() => {
    if (!isRunning) return;

    const intervalMs = Math.max(100, Math.floor(1000 / speedMultiplier));
    const timer = setInterval(() => {
      handleStep(1);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isRunning, speedMultiplier, handleStep]);

  // Handler for scenario change
  const handleChangeScenario = (newScenario: SimulationScenario) => {
    setScenario(newScenario);
    initEngine(newScenario, policy, numAmbulances, seed);
  };

  // Handler for policy change
  const handleChangePolicy = (newPolicy: DispatchPolicy) => {
    setPolicy(newPolicy);
    if (engineRef.current) {
      engineRef.current.state.policy = newPolicy;
      syncStateFromEngine();
    }
  };

  // Handler for weights change
  const handleChangeWeights = (newWeights: DispatchWeights) => {
    setWeights(newWeights);
    if (engineRef.current) {
      engineRef.current.state.weights = newWeights;
    }
  };

  // Reset simulation
  const handleReset = () => {
    setIsRunning(false);
    initEngine();
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans flex flex-col" id="ems-app-root">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        simMinute={simMinute}
        isRunning={isRunning}
        scenario={scenario}
        policy={policy}
        seed={seed}
        onReset={handleReset}
        onRunQuickBenchmark={() => {
          setActiveTab('comparison');
          handleRunBenchmark();
        }}
      />

      {/* Main Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5">
        {/* Live Top KPI Banner */}
        <LiveKPIHeader
          metrics={metrics}
          ambulances={ambulances}
          hospitals={hospitals}
          incidents={incidents}
        />

        {/* Tab Content Routing */}
        {activeTab === 'map' && (
          <div className="space-y-4">
            <MapView
              zones={zones}
              bases={bases}
              hospitals={hospitals}
              ambulances={ambulances}
              incidents={incidents}
              predictions={predictions}
              relocations={relocations}
              selectedZone={selectedZone}
              onSelectZone={setSelectedZone}
              selectedAmbulance={selectedAmbulance}
              onSelectAmbulance={setSelectedAmbulance}
            />

            {/* Subordinate live controllers under the map for instant manipulation */}
            <SimulationControls
              isRunning={isRunning}
              onTogglePlay={() => setIsRunning(!isRunning)}
              onStep={handleStep}
              onReset={handleReset}
              speedMultiplier={speedMultiplier}
              onChangeSpeed={setSpeedMultiplier}
              scenario={scenario}
              onChangeScenario={handleChangeScenario}
              policy={policy}
              onChangePolicy={handleChangePolicy}
              numAmbulances={numAmbulances}
              onChangeNumAmbulances={(n) => {
                setNumAmbulances(n);
                initEngine(scenario, policy, n, seed);
              }}
              seed={seed}
              onChangeSeed={(s) => {
                setSeed(s);
                initEngine(scenario, policy, numAmbulances, s);
              }}
              weights={weights}
              onChangeWeights={handleChangeWeights}
              ambulances={ambulances}
              eventLogs={eventLogs}
              activeIncidents={incidents}
              onSelectAmbulance={setSelectedAmbulance}
              selectedAmbulance={selectedAmbulance}
            />
          </div>
        )}

        {activeTab === 'simulation' && (
          <SimulationControls
            isRunning={isRunning}
            onTogglePlay={() => setIsRunning(!isRunning)}
            onStep={handleStep}
            onReset={handleReset}
            speedMultiplier={speedMultiplier}
            onChangeSpeed={setSpeedMultiplier}
            scenario={scenario}
            onChangeScenario={handleChangeScenario}
            policy={policy}
            onChangePolicy={handleChangePolicy}
            numAmbulances={numAmbulances}
            onChangeNumAmbulances={(n) => {
              setNumAmbulances(n);
              initEngine(scenario, policy, n, seed);
            }}
            seed={seed}
            onChangeSeed={(s) => {
              setSeed(s);
              initEngine(scenario, policy, numAmbulances, s);
            }}
            weights={weights}
            onChangeWeights={handleChangeWeights}
            ambulances={ambulances}
            eventLogs={eventLogs}
            activeIncidents={incidents}
            onSelectAmbulance={setSelectedAmbulance}
            selectedAmbulance={selectedAmbulance}
          />
        )}

        {activeTab === 'prediction' && (
          <PredictionPanel
            predictions={predictions}
            zones={zones}
            simMinute={simMinute}
            onRetrainModel={() => {
              handleStep(1);
            }}
          />
        )}

        {activeTab === 'comparison' && (
          <ComparisonView
            benchmark={benchmarkResult}
            onRerunBenchmark={handleRunBenchmark}
            isLoading={isBenchmarkLoading}
          />
        )}

        {activeTab === 'stats' && (
          <StatisticalPanel
            stats={benchmarkResult?.statistical_tests || null}
            totalIncidentsCount={benchmarkResult?.traditional_run.incidents.length || 0}
          />
        )}

        {activeTab === 'data' && (
          <DataManagement
            incidents={incidents}
            metrics={metrics}
            onImportIncidents={(newIncidents) => {
              setIncidents((prev) => [...newIncidents, ...prev]);
            }}
          />
        )}

        {activeTab === 'code' && <PythonArchitectureViewer />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 text-center text-xs text-slate-500">
        EMS Digital Twin Prototype &bull; Simulación Estocástica, Machine Learning & Equidad Socioeconómica
      </footer>
    </div>
  );
};

export default App;

