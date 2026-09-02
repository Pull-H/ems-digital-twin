import { DispatchPolicy, DispatchWeights, SimulationScenario } from '../types';
import { ComparisonBenchmarkResult } from './comparisonService';
import { SimulationState } from './simulationEngine';

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
    durationMin = 720
  ): Promise<ComparisonBenchmarkResult> {
    const params = new URLSearchParams({
      scenario,
      ambulances: String(numAmbulances),
      seed: String(seed),
      duration: String(durationMin),
    });

    return requestJson<ComparisonBenchmarkResult>(`/api/comparisons?${params.toString()}`);
  },
};
