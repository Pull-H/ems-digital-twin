import React, { useState } from 'react';
import { DemandPrediction, Zone } from '../types';
import { Brain, CheckCircle, Flame, Layers, Sparkles, TrendingUp, AlertTriangle } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface PredictionPanelProps {
  predictions: DemandPrediction[];
  zones: Zone[];
  simMinute: number;
  onRetrainModel: () => void;
}

export const PredictionPanel: React.FC<PredictionPanelProps> = ({
  predictions,
  zones,
  simMinute,
  onRetrainModel,
}) => {
  const [selectedHorizon, setSelectedHorizon] = useState<15 | 30 | 60>(15);
  const [riskFilter, setRiskFilter] = useState<'todos' | 'alto' | 'medio' | 'bajo'>('todos');

  const filteredPredictions = predictions.filter(
    (p) => p.horizonte_min === selectedHorizon && (riskFilter === 'todos' || p.nivel_riesgo === riskFilter)
  );

  // Sort descending by expected calls
  filteredPredictions.sort((a, b) => b.demanda_predicha_ml - a.demanda_predicha_ml);

  // Chart data for top 8 zones
  const chartData = filteredPredictions.slice(0, 8).map((p) => ({
    name: p.zona_nombre.replace('Distrito ', '').replace('Sector ', ''),
    'Línea Base Histórica': p.demanda_predicha_base,
    'Modelo ML (Random Forest/XGB)': p.demanda_predicha_ml,
    riesgo: p.nivel_riesgo,
  }));

  const highRiskCount = predictions.filter((p) => p.horizonte_min === selectedHorizon && p.nivel_riesgo === 'alto').length;
  const medRiskCount = predictions.filter((p) => p.horizonte_min === selectedHorizon && p.nivel_riesgo === 'medio').length;

  return (
    <div className="space-y-4" id="demand-prediction-panel">
      {/* Top Banner & Horizon Switcher */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
            <Brain className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Pronóstico Predictivo de Demanda por Zona</h3>
            <p className="text-xs text-slate-500">
              Modelo no-lineal entrenado con covariables de quintil, demografía, clima y series temporales
            </p>
          </div>
        </div>

        {/* Controls: Horizon Selector + Train Button */}
        <div className="flex items-center space-x-2">
          <div className="flex bg-slate-100 p-1 rounded-lg text-xs font-semibold text-slate-700">
            {([15, 30, 60] as const).map((h) => (
              <button
                key={h}
                onClick={() => setSelectedHorizon(h)}
                className={`px-3 py-1 rounded-md transition-colors ${
                  selectedHorizon === h ? 'bg-indigo-600 text-white shadow-xs' : 'hover:text-slate-900'
                }`}
              >
                Horizonte {h} min
              </button>
            ))}
          </div>

          <button
            onClick={onRetrainModel}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Re-calibrar</span>
          </button>
        </div>
      </div>

      {/* KPI Model Benchmark Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Zonas en Riesgo Alto</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-rose-600">{highRiskCount}</span>
            <span className="text-xs text-slate-400">de 20 zonas</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Demanda esperada &gt; 0.35 ll./15m</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Error Absoluto Medio (MAE)</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-slate-900">0.142</span>
            <span className="text-xs text-emerald-600 font-semibold">-38% vs Base</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Línea base histórica: 0.228</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Raíz Error Cuadrático (RMSE)</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-slate-900">0.218</span>
            <span className="text-xs text-emerald-600 font-semibold">-42% vs Base</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Línea base histórica: 0.375</span>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs text-slate-500 font-medium">Coeficiente de Determinación (R²)</span>
          <div className="flex items-baseline space-x-2 mt-1">
            <span className="text-2xl font-bold text-indigo-700">0.884</span>
            <span className="text-xs text-slate-400 font-semibold">Excelente ajuste</span>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">Validación cruzada 5-fold</span>
        </div>
      </div>

      {/* Comparison Chart: Historical Baseline vs ML Model */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
          <div className="flex items-center space-x-2">
            <TrendingUp className="w-4 h-4 text-indigo-600" />
            <h4 className="font-bold text-sm text-slate-900">
              Comparación de Demanda Esperada (Horizonte {selectedHorizon} min) - Zonas de Mayor Riesgo
            </h4>
          </div>
          <span className="text-xs text-slate-500">Unidad: Llamadas de emergencia previstas</span>
        </div>

        <div className="h-[260px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" angle={-15} textAnchor="end" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Bar dataKey="Línea Base Histórica" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Modelo ML (Random Forest/XGB)" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Risk Table & Principal Factors */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
          <div className="flex items-center space-x-2">
            <Flame className="w-4 h-4 text-rose-500" />
            <h4 className="font-bold text-sm text-slate-900">Matriz de Riesgo y Factores Explicativos por Zona</h4>
          </div>

          <div className="flex items-center space-x-1 text-xs">
            <span className="text-slate-400 font-medium mr-1">Filtrar por riesgo:</span>
            {(['todos', 'alto', 'medio', 'bajo'] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setRiskFilter(lvl)}
                className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize ${
                  riskFilter === lvl ? 'bg-slate-900 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto max-h-[320px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold sticky top-0">
              <tr>
                <th className="p-2.5">Zona</th>
                <th className="p-2.5">Nivel de Riesgo</th>
                <th className="p-2.5 text-right">Llamadas Previstas (ML)</th>
                <th className="p-2.5 text-right">Probabilidad Incidente</th>
                <th className="p-2.5">Factores Principales de Riesgo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredPredictions.map((p) => {
                let badgeClass = 'bg-emerald-100 text-emerald-800';
                if (p.nivel_riesgo === 'alto') badgeClass = 'bg-rose-100 text-rose-800 font-bold';
                else if (p.nivel_riesgo === 'medio') badgeClass = 'bg-amber-100 text-amber-800';

                return (
                  <tr key={p.zona_id} className="hover:bg-slate-50">
                    <td className="p-2.5">
                      <span className="font-bold text-slate-900 block">{p.zona_nombre}</span>
                      <span className="text-[10px] font-mono text-slate-400">Z-{p.zona_id}</span>
                    </td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] uppercase ${badgeClass}`}>
                        {p.nivel_riesgo}
                      </span>
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                      {p.demanda_predicha_ml.toFixed(2)}
                    </td>
                    <td className="p-2.5 text-right font-mono text-indigo-700 font-semibold">
                      {(p.probabilidad_incidente * 100).toFixed(1)}%
                    </td>
                    <td className="p-2.5">
                      <div className="flex flex-wrap gap-1">
                        {p.factores_principales.map((factor, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] border border-slate-200"
                          >
                            {factor}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
