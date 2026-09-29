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
import { AssistantPanel } from './components/AssistantPanel';
import { HistoricalWorkspace } from './components/historical/HistoricalWorkspace';
import { ModelPerformancePanel } from './components/historical/ModelPerformancePanel';
import { CrispDmPanel } from './components/historical/CrispDmPanel';

import {
  Ambulance,
  CreateSimulationRequest,
  DemandPrediction,
  DispatchPolicy,
  DispatchWeights,
  EMSBase,
  HistoricalDatasetProfile,
  Hospital,
  Incident,
  RelocationRecommendation,
  SimulationMetrics,
  SimulationScenario,
  SimEventLog,
  SimulationState,
  StatisticalTestResult,
  Zone,
} from './types';
import { datasetApi, simulationApi } from './services/apiClient';
import { ZONES_DATA, EMS_BASES, HOSPITALS } from './services/cityData';
import { EMSSimulationEngine } from './services/simulationEngine';
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
  const [zones, setZones] = useState<Zone[]>(ZONES_DATA);
  const [bases, setBases] = useState<EMSBase[]>(EMS_BASES);
  const [hospitals, setHospitals] = useState<Hospital[]>(HOSPITALS);
  const [ambulances, setAmbulances] = useState<Ambulance[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [metrics, setMetrics] = useState<SimulationMetrics>(() => createEmptySimulationMetrics());
  const [predictions, setPredictions] = useState<DemandPrediction[]>([]);
  const [relocations, setRelocations] = useState<RelocationRecommendation[]>([]);
  const [eventLogs, setEventLogs] = useState<SimEventLog[]>([]);
  const [runtimeMode, setRuntimeMode] = useState<RuntimeMode>('local');
  const [apiWarning, setApiWarning] = useState<string | null>(null);
  const [datasetProfile, setDatasetProfile] = useState<HistoricalDatasetProfile | null>(null);
  const [historicalState, setHistoricalState] = useState<SimulationState | null>(null);
  const [historicalBusy, setHistoricalBusy] = useState(true);
  const initializationStarted = useRef(false);

  // Selection state
  const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
  const [selectedAmbulance, setSelectedAmbulance] = useState<Ambulance | null>(null);

  // Comparison & Statistical benchmarks
  const [benchmarkResult, setBenchmarkResult] = useState<ComparisonBenchmarkResult | null>(null);
  const [isBenchmarkLoading, setIsBenchmarkLoading] = useState<boolean>(false);

  const applySimulationState = useCallback((state: SimulationState) => {
    setHistoricalState(state.simulation ? state : null);
    if (state.simulation?.status === 'finished') setIsRunning(false);
    setSimMinute(state.sim_minute);
    setZones([...state.zones]);
    setBases([...state.bases]);
    setAmbulances([...state.ambulances]);
    setIncidents([...state.incidents]);
    setHospitals([...state.hospitals]);
    setMetrics({ ...state.metrics });
    setPredictions([...state.predictions]);
    setRelocations([...state.relocation_recommendations]);
    setEventLogs([...state.event_logs]);
  }, []);

  const handleLoadHistoricalDataset = useCallback(
    async (datasetId: string, options: Partial<CreateSimulationRequest> = {}) => {
      setIsRunning(false);
      if (stepInFlightRef.current) {
        setApiWarning('Espera a que termine el avance actual antes de crear otra corrida.');
        return;
      }
      stepInFlightRef.current = true;
      setHistoricalBusy(true);
      try {
        const profile = await datasetApi.getProfile(datasetId);
        const visualFleetSize = options.num_ambulances ?? profile.resource_assumptions.recommended_starting_point?.fleet_size_proxy ?? 691;
        const modelId = profile.model_selection.best_model_id || profile.available_models[0] || 'hist_gradient_boosting_v1';
        const response = await simulationApi.createSimulation({
          scenario: 'dia_normal',
          policy,
          num_ambulances: visualFleetSize,
          seed,
          duration_min: 720,
          weights,
          data_mode: 'historical',
          dataset_id: datasetId,
          model_id: modelId,
          ...options,
        });
        engineRef.current = null;
        setRuntimeMode('api');
        setDatasetProfile(profile);
        setNumAmbulances(visualFleetSize);
        setScenario('dia_normal');
        setPolicy(response.state.policy);
        setSeed(response.state.seed);
        setSelectedZone(null);
        setSelectedAmbulance(null);
        setBenchmarkResult(null);
        setApiWarning(null);
        applySimulationState(response.state);
        setActiveTab('map');
      } catch (err) {
        setApiWarning(`No se pudo crear la corrida NYC: ${err instanceof Error ? err.message : 'error de conexion'}`);
        console.warn('Historical dataset load failed:', err);
      } finally {
        stepInFlightRef.current = false;
        setHistoricalBusy(false);
      }
    },
    [applySimulationState, policy, seed, weights]
  );

  const createHistoricalRun = useCallback(async (options: Partial<CreateSimulationRequest> = {}) => {
    if (!datasetProfile || !historicalState) return;
    await handleLoadHistoricalDataset(datasetProfile.id, {
      demand_source: historicalState.simulation!.demand_source,
      policy: historicalState.policy, seed: historicalState.seed,
      model_id: historicalState.model_id, num_ambulances: historicalState.ambulances.length,
      start_minute: historicalState.start_minute,
      duration_min: historicalState.total_duration_min - historicalState.start_minute!,
      ...options,
    });
  }, [datasetProfile, historicalState, handleLoadHistoricalDataset]);

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
      const result = await simulationApi.runComparisonBenchmark(
        scenario,
        datasetProfile ? historicalState?.ambulances.length || numAmbulances : numAmbulances,
        historicalState?.seed ?? seed,
        datasetProfile && historicalState ? historicalState.total_duration_min - (historicalState.start_minute ?? 0) : 720,
        datasetProfile
          ? {
              datasetId: datasetProfile.id,
              modelId: historicalState?.model_id || datasetProfile.model_selection.best_model_id,
              startMinute: historicalState?.start_minute,
              repetitions: 10,
              demandSource: historicalState?.simulation?.demand_source || 'historical',
            }
          : {}
      );
      setBenchmarkResult(result);
      setApiWarning(null);
    } catch (err) {
      if (!datasetProfile) {
        const result = runComparisonBenchmark(scenario, numAmbulances, seed, 720, weights);
        setBenchmarkResult(result);
        setApiWarning('Benchmark ejecutado localmente porque la API no respondio.');
      } else {
        setApiWarning(`No se pudo ejecutar el experimento NYC: ${err instanceof Error ? err.message : 'error de conexion'}`);
      }
      console.warn('API benchmark unavailable, using local benchmark:', err);
    } finally {
      setIsBenchmarkLoading(false);
    }
  }, [scenario, seed, numAmbulances, weights, datasetProfile, historicalState]);

  // Initial mount
  useEffect(() => {
    if (initializationStarted.current) return;
    initializationStarted.current = true;
    void datasetApi.listDatasets().then(async ({ datasets }) => {
      const ready = datasets.find(d => d.historical_ready);
      if (ready) await handleLoadHistoricalDataset(ready.id);
      else { await initEngine(); setHistoricalBusy(false); setApiWarning('Modo demostracion: no hay un snapshot NYC preparado.'); }
    }).catch(() => { setHistoricalBusy(false); setApiWarning('No se pudo conectar con FastAPI. Inicia el backend y recarga la pagina.'); });
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
        if (datasetProfile) {
          setIsRunning(false);
          setApiWarning('La corrida NYC se ha pausado por un error de conexion. No se ha sustituido por datos demo.');
          return;
        }
        setApiWarning('Se perdio conexion con la API; la simulacion continua en modo local.');
        initializeLocalEngine(scenario, policy, numAmbulances, seed, weights, simMinute);
        engineRef.current?.step(deltaMin);
        syncStateFromEngine();
        console.warn('API step failed, switched to local engine:', err);
      } finally {
        stepInFlightRef.current = false;
      }
    },
    [applySimulationState, initializeLocalEngine, numAmbulances, policy, runtimeMode, scenario, seed, simMinute, syncStateFromEngine, weights, datasetProfile]
  );

  // Play/Pause ticker
  useEffect(() => {
    if (!isRunning) return;

    const intervalMs = datasetProfile ? 1000 : Math.max(100, Math.floor(1000 / speedMultiplier));
    const timer = setInterval(() => {
      void handleStep(datasetProfile ? speedMultiplier : 1);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isRunning, speedMultiplier, handleStep, datasetProfile]);

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
    if (datasetProfile) { void createHistoricalRun(); return; }
    void initEngine();
  };

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 font-sans flex flex-col" id="ems-app-root">
      <Navbar
        historicalClock={historicalState?.simulation?.clock}
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
        {!datasetProfile && !historicalBusy && <LiveKPIHeader
          metrics={metrics}
          ambulances={ambulances}
          hospitals={hospitals}
          incidents={incidents}
        />}

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
        {historicalBusy && <p role="status" className="text-sm py-3">Preparando corrida NYC...</p>}
        {historicalState && datasetProfile && ['map', 'simulation'].includes(activeTab) && (
          <HistoricalWorkspace
            key={`${historicalState.dataset_id}-${historicalState.start_minute}-${historicalState.seed}-${historicalState.simulation!.demand_source}-${historicalState.policy}-${historicalState.ambulances.length}-${historicalState.model_id}-${historicalState.total_duration_min}`}
            state={historicalState} profile={datasetProfile} running={isRunning} busy={historicalBusy}
            speed={speedMultiplier} onSpeed={setSpeedMultiplier} onToggle={() => setIsRunning(v => !v)}
            onStep={handleStep} onCreate={createHistoricalRun}
          />
        )}
        {historicalState && datasetProfile && activeTab === 'prediction' && (
          <ModelPerformancePanel profile={datasetProfile} state={historicalState} />
        )}
        {datasetProfile && activeTab === 'comparison' && (
          <ComparisonView
            benchmark={benchmarkResult}
            onRerunBenchmark={handleRunBenchmark}
            isLoading={isBenchmarkLoading}
          />
        )}

        {datasetProfile && activeTab === 'stats' && (
          <StatisticalPanel
            stats={benchmarkResult?.statistical_tests || null}
            totalIncidentsCount={benchmarkResult?.replications?.length || 0}
          />
        )}

        {datasetProfile && activeTab === 'crispdm' && (
          <CrispDmPanel profile={datasetProfile} />
        )}
        {!datasetProfile && !historicalBusy && activeTab === 'map' && (
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

        {!datasetProfile && activeTab === 'simulation' && (
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

        {!datasetProfile && activeTab === 'prediction' && (
          <PredictionPanel
            predictions={predictions}
            zones={zones}
            simMinute={simMinute}
            onRetrainModel={() => {
              void handleStep(1);
            }}
          />
        )}

        {!datasetProfile && activeTab === 'comparison' && (
          <ComparisonView
            benchmark={benchmarkResult}
            onRerunBenchmark={handleRunBenchmark}
            isLoading={isBenchmarkLoading}
          />
        )}

        {!datasetProfile && activeTab === 'stats' && (
          <StatisticalPanel
            stats={benchmarkResult?.statistical_tests || null}
            totalIncidentsCount={benchmarkResult?.traditional_run.incidents.length || 0}
          />
        )}

        {!datasetProfile && activeTab === 'crispdm' && (
          <section className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-700">
            La metodología CRISP-DM completa está disponible al cargar el dataset histórico NYC EMS.
          </section>
        )}

        {activeTab === 'data' && (
          <DataManagement
            incidents={incidents}
            metrics={metrics}
            datasetProfile={datasetProfile}
            onLoadHistoricalDataset={handleLoadHistoricalDataset}
            onImportIncidents={(newIncidents) => {
              setIncidents((prev) => [...newIncidents, ...prev]);
            }}
          />
        )}

        {activeTab === 'assistant' && <AssistantPanel />}

        {activeTab === 'code' && <PythonArchitectureViewer />}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 text-center text-xs text-slate-500">
        {datasetProfile ? 'NYC EMS · Simulacion por zonas con datos historicos y recursos asumidos' : 'EMS Digital Twin · Demostracion academica'}
      </footer>
    </div>
  );
};

export default App;
