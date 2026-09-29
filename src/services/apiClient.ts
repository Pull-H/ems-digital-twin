import {
  AssistantQueryRequest,
  AssistantQueryResponse,
  CreateSimulationRequest,
  CreateSimulationResponse,
  CrispDmReport,
  DispatchPolicy,
  DispatchWeights,
  HistoricalDatasetProfile,
  HistoricalDatasetSummary,
  ModelPerformanceReport,
  SimulationScenario,
  SimulationState,
} from '../types';
import { ComparisonBenchmarkResult } from './comparisonService';

const apiBaseUrl =
  ((import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env?.VITE_API_BASE_URL || '').replace(/\/$/, '');

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${response.status}: ${detail || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export const simulationApi = {
  createSimulation(payload: CreateSimulationRequest): Promise<CreateSimulationResponse> {
    return requestJson<CreateSimulationResponse>('/api/simulations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  stepSimulation(deltaMinutes: number): Promise<SimulationState> {
    return requestJson<SimulationState>('/api/simulations/step', {
      method: 'POST',
      body: JSON.stringify({ delta_minutes: deltaMinutes }),
    });
  },

  updateConfig(payload: Partial<Pick<CreateSimulationRequest, 'policy' | 'weights'>>): Promise<SimulationState> {
    return requestJson<SimulationState>('/api/simulations/config', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  runComparisonBenchmark(
    scenario: SimulationScenario,
    numAmbulances: number,
    seed: number,
    durationMin = 720,
    options: {
      datasetId?: string;
      modelId?: string;
      startMinute?: number;
      repetitions?: number;
      demandSource?: 'historical' | 'forecast';
    } = {}
  ): Promise<ComparisonBenchmarkResult> {
    const params = new URLSearchParams({
      scenario,
      ambulances: String(numAmbulances),
      seed: String(seed),
      duration: String(durationMin),
    });
    if (options.datasetId) params.set('dataset_id', options.datasetId);
    if (options.modelId) params.set('model_id', options.modelId);
    if (options.startMinute !== undefined) params.set('start_minute', String(options.startMinute));
    if (options.repetitions !== undefined) params.set('repetitions', String(options.repetitions));
    if (options.demandSource) params.set('demand_source', options.demandSource);

    return requestJson<ComparisonBenchmarkResult>(`/api/comparisons?${params.toString()}`);
  },
};

export const datasetApi = {
  listDatasets(): Promise<{ datasets: HistoricalDatasetSummary[] }> {
    return requestJson<{ datasets: HistoricalDatasetSummary[] }>('/api/datasets');
  },

  getProfile(datasetId: string): Promise<HistoricalDatasetProfile> {
    return requestJson<HistoricalDatasetProfile>(`/api/datasets/${encodeURIComponent(datasetId)}/profile`);
  },
};

export const assistantApi = {
  query(payload: AssistantQueryRequest): Promise<AssistantQueryResponse> {
    return requestJson<AssistantQueryResponse>('/api/assistant/query', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

export const modelPerformanceApi = {
  getReport(datasetId: string): Promise<ModelPerformanceReport> {
    const params = new URLSearchParams({ dataset_id: datasetId });
    return requestJson<ModelPerformanceReport>(`/api/model-performance?${params.toString()}`);
  },
};

export const crispDmApi = {
  getReport(datasetId: string): Promise<CrispDmReport> {
    const params = new URLSearchParams({ dataset_id: datasetId });
    return requestJson<CrispDmReport>(`/api/methodology/crisp-dm?${params.toString()}`);
  },
};
