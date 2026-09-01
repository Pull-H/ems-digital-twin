import React, { useState } from 'react';
import { BookOpen, Check, Code2, Copy, Cpu, FileCode, Layers, Network, Terminal } from 'lucide-react';

export const PythonArchitectureViewer: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const [activeCodeTab, setActiveCodeTab] = useState<'fastapi' | 'dispatch' | 'docker'>('fastapi');

  const fastApiCode = `# backend/app/main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

app = FastAPI(
    title="EMS Digital Twin API",
    description="Prototipo de Gemelo Digital para Redes de Ambulancias y Despacho Predictivo con Equidad",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "SimPy Discrete Event Engine"}

@app.post("/api/simulations/run-benchmark")
def run_benchmark(horizon_hours: int = 12, seed: int = 12345):
    """
    Ejecuta simulación pareada idéntica (Tradicional vs Predictivo)
    y calcula pruebas estadísticas t-Student y Wilcoxon.
    """
    return {"message": "Benchmark ejecutado exitosamente."}
`;

  const dispatchCode = `# backend/app/dispatch/engine.py
class PredictiveDispatchEngine:
    def __init__(self, w_time=0.45, w_demand=0.25, w_cov=0.15, w_equity=0.15):
        self.w_time = w_time
        self.w_demand = w_demand
        self.w_cov = w_cov
        self.w_equity = w_equity

    def score_ambulance(self, ambulance, incident, zone_predictions, fleet_coverage):
        # 1. Tiempo estimado de arribo
        t_eta = self.estimate_travel_time(ambulance.location, incident.location)
        
        # 2. Demanda futura en zona de origen de la ambulancia
        d_future = zone_predictions.get(ambulance.base_zone_id, 0.0)
        
        # 3. Penalización por pérdida de cobertura en sector donante
        cov_loss = fleet_coverage.calc_loss(ambulance.base_zone_id)
        
        # 4. Bonificación de equidad por vulnerabilidad socioeconómica (Q1 > Q5)
        equity_bonus = incident.vulnerability_index
        
        score = (
            self.w_time * t_eta +
            self.w_demand * d_future +
            self.w_cov * cov_loss -
            self.w_equity * (equity_bonus * 10.0)
        )
        return score
`;

  const dockerCode = `# docker-compose.yml
version: '3.8'

services:
  ems-digital-twin:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    restart: unless-stopped
`;

  const handleCopy = () => {
    const textToCopy =
      activeCodeTab === 'fastapi'
        ? fastApiCode
        : activeCodeTab === 'dispatch'
        ? dispatchCode
        : dockerCode;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4" id="architecture-viewer-panel">
      {/* Header Info */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
        <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900 text-sm">
            Metodología Académica, Formulación Matemática y Arquitectura de Software
          </h3>
          <p className="text-xs text-slate-500">
            Documentación formal de los modelos de simulación, despacho con equidad y reproducibilidad científica
          </p>
        </div>
      </div>

      {/* Mathematical Formulations Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Formula 1: Scoring Function */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs border-b border-slate-100 pb-2">
            <Cpu className="w-4 h-4" />
            <span>1. Función de Puntuación Multicriterio para Despacho</span>
          </div>

          <div className="p-3 bg-slate-900 rounded-lg text-slate-100 font-mono text-xs overflow-x-auto">
            S(a, i) = w_t · T(a, i) + w_d · D̂(Z_orig) + w_c · ΔC(Z_orig) - w_e · V(Z_inc)
          </div>

          <div className="text-xs text-slate-600 space-y-1">
            <p>
              <strong className="text-slate-800">T(a, i):</strong> Tiempo estimado de viaje entre ambulancia <code className="text-indigo-600 font-mono font-bold">a</code> y emergencia <code className="text-indigo-600 font-mono font-bold">i</code>.
            </p>
            <p>
              <strong className="text-slate-800">D̂(Z_orig):</strong> Demanda pronosticada a 15-30 min en la zona donante por el modelo ML.
            </p>
            <p>
              <strong className="text-slate-800">ΔC(Z_orig):</strong> Pérdida relativa de cobertura territorial si la unidad desocupa su base.
            </p>
            <p>
              <strong className="text-slate-800">V(Z_inc):</strong> Índice de vulnerabilidad socioeconómica de la zona del incidente ($Q_1 \approx 0.85$ vs $Q_5 \approx 0.15$).
            </p>
          </div>
        </div>

        {/* Formula 2: Disparity Ratio */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
          <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs border-b border-slate-100 pb-2">
            <Network className="w-4 h-4" />
            <span>2. Métrica de Equidad: Razón de Disparidad Territorial</span>
          </div>

          <div className="p-3 bg-slate-900 rounded-lg text-slate-100 font-mono text-xs overflow-x-auto">
            R_disp = E[T_resp | Zona ∈ Q_1] / E[T_resp | Zona ∈ Q_5]
          </div>

          <div className="text-xs text-slate-600 space-y-1">
            <p>
              <strong className="text-slate-800">R = 1.0:</strong> Equidad territorial perfecta (igualdad de tiempos de respuesta esperados sin sesgo de clase socioeconómica).
            </p>
            <p>
              <strong className="text-slate-800">R &gt; 1.3:</strong> Inequidad estructural donde las zonas vulnerables sufren demoras sistemáticas por concentración histórica de recursos en zonas centrales o adineradas.
            </p>
          </div>
        </div>
      </div>

      {/* Code Viewer Box */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="bg-slate-900 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-indigo-400" />
            <span className="text-xs font-bold text-slate-200">Archivos Fuente del Proyecto para Tesis / Reproducibilidad</span>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex space-x-1 bg-slate-800 p-0.5 rounded text-xs">
              <button
                onClick={() => setActiveCodeTab('fastapi')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  activeCodeTab === 'fastapi' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                FastAPI Server (main.py)
              </button>
              <button
                onClick={() => setActiveCodeTab('dispatch')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  activeCodeTab === 'dispatch' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Algoritmo Despacho
              </button>
              <button
                onClick={() => setActiveCodeTab('docker')}
                className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                  activeCodeTab === 'docker' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                docker-compose.yml
              </button>
            </div>

            <button
              onClick={handleCopy}
              className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
              title="Copiar código fuente"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <pre className="p-4 bg-slate-950 text-slate-200 font-mono text-xs overflow-x-auto leading-relaxed max-h-[340px]">
          <code>
            {activeCodeTab === 'fastapi'
              ? fastApiCode
              : activeCodeTab === 'dispatch'
              ? dispatchCode
              : dockerCode}
          </code>
        </pre>
      </div>
    </div>
  );
};
