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
import { simulationApi } from './services/apiClient';
import { ZONES_DATA, EMS_BASES, HOSPITALS } from './services/cityData';
import { EMSSimulationEngine, SimEventLog, SimulationState } from './services/simulationEngine';
import { ComparisonBenchmarkResult, runComparisonBenchmark } from './services/comparisonService';
import { createEmptySimulationMetrics } from './services/statsEngine';

type RuntimeMode = 'api' | 'local';

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
  const stepInFlightRef = useRef(false);

  // Live state
  const [simMinute, setSimMinute] = useState<number>(0);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [zones] = useState<Zone[]>(ZONES_DATA);
  const [bases] = useState<EMSBase[]>(EMS_BASES);
  const [hospitals, setHospitals] = useState<Hospital[]>(HOSPITALS);
  const [ambulances, setAmbulances] = useState<Ambulance[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<SimulationMetrics>(() => createEmptySimulationMetrics());
  const [predictions, setPredictions] = useState<DemandPrediction[]>([]);
  const [relocations, setRelocations] = useState<RelocationRecommendation[]>([]);
  const [eventLogs, setEventLogs] = useState<SimEventLog[]>([]);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>('local');
  const [apiWarning, setApiWarning] = useState<string | null>(null);

  // Selection state
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [selectedAmbulance, setSelectedAmbulance] = useState<Ambulance | null>(null);

  // Comparison & Statistical benchmarks
  const [benchmarkResult, setBenchmarkResult] = useState<ComparisonBenchmarkResult | null>(null);
  const [isBenchmarkLoading, setIsBenchmarkLoading] = useState<boolean>(false);

  const applySimulationState = useCallback((state: SimulationState) => {
    setSimMinute(state.sim_minute);
    setAmbulances([...state.ambulances]);
    setIncidents([...state.incidents]);
    setHospitals([...state.hospitals]);
    setMetrics({ ...state.metrics });
    setPredictions([...state.predictions]);
    setRelocations([...state.relocation_recommendations]);
    setEventLogs([...state.event_logs]);
  }, []);

  // Sync state from engine
  const syncStateFromEngine = useCallback(() => {
    if (!engineRef.current) return;
    applySimulationState(engineRef.current.state);
  }, [applySimulationState]);

  const initializeLocalEngine = useCallback(
    (
      customScenario: SimulationScenario,
      customPolicy: DispatchPolicy,
      customNumAmbs: number,
      customSeed: number,
      customWeights: DispatchWeights,
      warmupMinutes = 45
    ) => {
      const newEngine = new EMSSimulationEngine(
        customScenario,
        customPolicy,
        customNumAmbs,
        customSeed,
        720,
        customWeights
      );

      newEngine.step(warmupMinutes);
      engineRef.current = newEngine;
      setRuntimeMode('local');
      applySimulationState(newEngine.state);
    },
    [applySimulationState]
  );

  // Initialize engine
  const initEngine = useCallback(
    async (
      customScenario = scenario,
      customPolicy = policy,
      customNumAmbs = numAmbulances,
      customSeed = seed,
      customWeights = weights
    ) => {
      setIsRunning(false);

      try {
        await simulationApi.createSimulation({
          scenario: customScenario,
          policy: customPolicy,
          num_ambulances: customNumAmbs,
          seed: customSeed,
          duration_min: 720,
          weights: customWeights,
        });
        const warmedState = await simulationApi.stepSimulation(45);
        engineRef.current = null;
        setRuntimeMode('api');
        setApiWarning(null);
        applySimulationState(warmedState);
      } catch (err) {
        initializeLocalEngine(customScenario, customPolicy, customNumAmbs, customSeed, customWeights);
        setApiWarning('API no disponible; usando motor local en el navegador.');
        console.warn('API simulation unavailable, falling back to local engine:', err);
      }
    },
    [applySimulationState, initializeLocalEngine, scenario, policy, numAmbulances, seed, weights]
  );

  // Run benchmark
  const handleRunBenchmark = useCallback(async () => {
    setIsBenchmarkLoading(true);
    try {
      const result = await simulationApi.runComparisonBenchmark(scenario, numAmbulances, seed, 720);
      setBenchmarkResult(result);
    } catch (err) {
      const result = runComparisonBenchmark(scenario, numAmbulances, seed, 720, weights);
      setBenchmarkResult(result);
      setApiWarning('Benchmark ejecutado localmente porque la API no respondio.');
      console.warn('API benchmark unavailable, using local benchmark:', err);
    } finally {
      setIsBenchmarkLoading(false);
    }
  }, [scenario, seed, numAmbulances, weights]);

  // Initial mount
  useEffect(() => {
    void initEngine();
    void handleRunBenchmark();
  }, []);

  // Step simulation function
  const handleStep = useCallback(
    async (deltaMin: number) => {
      if (stepInFlightRef.current) return;
      stepInFlightRef.current = true;

      try {
        if (runtimeMode === 'api') {
          const updatedState = await simulationApi.stepSimulation(deltaMin);
          applySimulationState(updatedState);
          return;
        }

        if (!engineRef.current) {
          initializeLocalEngine(scenario, policy, numAmbulances, seed, weights, simMinute);
        }
        engineRef.current?.step(deltaMin);
        syncStateFromEngine();
      } catch (err) {
        setApiWarning('Se perdio conexion con la API; la simulacion continua en modo local.');
        initializeLocalEngine(scenario, policy, numAmbulances, seed, weights, simMinute);
        engineRef.current?.step(deltaMin);
        syncStateFromEngine();
        console.warn('API step failed, switched to local engine:', err);
      } finally {
        stepInFlightRef.current = false;
      }
    },
    [applySimulationState, initializeLocalEngine, numAmbulances, policy, runtimeMode, scenario, seed, simMinute, syncStateFromEngine, weights]
  );

  // Play/Pause ticker
  useEffect(() => {
    if (!isRunning) return;

    const intervalMs = Math.max(100, Math.floor(1000 / speedMultiplier));
    const timer = setInterval(() => {
      void handleStep(1);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isRunning, speedMultiplier, handleStep]);

  // Handler for scenario change
  const handleChangeScenario = (newScenario: SimulationScenario) => {
    setScenario(newScenario);
    void initEngine(newScenario, policy, numAmbulances, seed, weights);
  };

  // Handler for policy change
  const handleChangePolicy = (newPolicy: DispatchPolicy) => {
    setPolicy(newPolicy);
    if (engineRef.current) {
      engineRef.current.state.policy = newPolicy;
      syncStateFromEngine();
    }
    if (runtimeMode === 'api') {
      void simulationApi.updateConfig({ policy: newPolicy }).then(applySimulationState).catch((err) => {
        setApiWarning('No se pudo sincronizar la politica con la API.');
        console.warn('API policy update failed:', err);
      });
    }
  };

  // Handler for weights change
  const handleChangeWeights = (newWeights: DispatchWeights) => {
    setWeights(newWeights);
    if (engineRef.current) {
      engineRef.current.state.weights = newWeights;
    }
    if (runtimeMode === 'api') {
      void simulationApi.updateConfig({ weights: newWeights }).then(applySimulationState).catch((err) => {
        setApiWarning('No se pudieron sincronizar los pesos con la API.');
        console.warn('API weights update failed:', err);
      });
    }
  };

  // Reset simulation
  const handleReset = () => {
    void initEngine();
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans flex flex-col" id="ems-app-root">
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

        {apiWarning && (
          <div className="mb-4 flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            <span>
              Modo {runtimeMode === 'api' ? 'API' : 'local'}: {apiWarning}
            </span>
            <button className="font-semibold text-amber-800 hover:text-amber-950" onClick={() => setApiWarning(null)}>
              Cerrar
            </button>
          </div>
        )}

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
              onTogglePlay={() => setIsRunning((current) => !current)}
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
                void initEngine(scenario, policy, n, seed, weights);
              }}
              seed={seed}
              onChangeSeed={(s) => {
                setSeed(s);
                void initEngine(scenario, policy, numAmbulances, s, weights);
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
            onTogglePlay={() => setIsRunning((current) => !current)}
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
              void initEngine(scenario, policy, n, seed, weights);
            }}
            seed={seed}
            onChangeSeed={(s) => {
              setSeed(s);
              void initEngine(scenario, policy, numAmbulances, s, weights);
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
              void handleStep(1);
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
