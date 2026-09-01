import React from 'react';
import { ComparisonBenchmarkResult } from '../services/comparisonService';
import { SocioeconomicQuintile } from '../types';
import {
  GitCompare,
  TrendingDown,
  TrendingUp,
  Scale,
  Award,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

interface ComparisonViewProps {
  benchmark: ComparisonBenchmarkResult | null;
  onRerunBenchmark: () => void;
  isLoading: boolean;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  benchmark,
  onRerunBenchmark,
  isLoading,
}) => {
  if (!benchmark) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 text-center space-y-3" id="comparison-loading">
        <GitCompare className="w-12 h-12 text-indigo-500 mx-auto animate-bounce" />
        <h3 className="font-bold text-lg text-slate-800">Generando Benchmark Pareado...</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Ejecutando simulación idéntica con el mismo conjunto de llamadas para comparar la política tradicional frente a la predictiva.
        </p>
      </div>
    );
  }

  const trad = benchmark.traditional_run.metrics;
  const pred = benchmark.predictive_run.metrics;
  const res = benchmark.resumen_ejecutivo;

  // Prepare chart data for Quintiles Q1-Q5
  const quintiles: SocioeconomicQuintile[] = [1, 2, 3, 4, 5];
  const quintileNames = {
    1: 'Q1 (Muy Vulnerable)',
    2: 'Q2 (Vulnerable)',
    3: 'Q3 (Medio)',
    4: 'Q4 (Medio-Alto)',
    5: 'Q5 (Menor Vuln.)',
  };

  const responseTimeByQuintileData = quintiles.map((q) => ({
    quintil: quintileNames[q],
    'Despacho Tradicional': trad.por_quintil[q]?.tiempo_promedio_respuesta || 0,
    'Despacho Predictivo': pred.por_quintil[q]?.tiempo_promedio_respuesta || 0,
  }));

  const compliance8MinByQuintileData = quintiles.map((q) => ({
    quintil: quintileNames[q],
    'Despacho Tradicional': trad.por_quintil[q]?.porcentaje_menor_8min || 0,
    'Despacho Predictivo': pred.por_quintil[q]?.porcentaje_menor_8min || 0,
  }));

  // Prepare response time histogram comparison
  const bins = [4, 6, 8, 10, 12, 14, 16, 20];
  const histogramData = bins.map((binLimit, idx) => {
    const prevLimit = idx === 0 ? 0 : bins[idx - 1];
    const tradCount = benchmark.traditional_run.incidents.filter(
      (i) => i.tiempo_respuesta_min !== null && i.tiempo_respuesta_min > prevLimit && i.tiempo_respuesta_min <= binLimit
    ).length;
    const predCount = benchmark.predictive_run.incidents.filter(
      (i) => i.tiempo_respuesta_min !== null && i.tiempo_respuesta_min > prevLimit && i.tiempo_respuesta_min <= binLimit
    ).length;

    return {
      rango: `${prevLimit}-${binLimit}m`,
      'Tradicional (Frecuencia)': tradCount,
      'Predictivo (Frecuencia)': predCount,
    };
  });

  return (
    <div className="space-y-4" id="policy-comparison-view">
      {/* Header & Scenario info */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              Comparación Científica Pareada: Tradicional vs Predictivo
            </h3>
            <p className="text-xs text-slate-500">
              Evaluación rigurosa sobre los mismos incidentes sintéticos (Semilla: {benchmark.semilla}, Escenario: {benchmark.scenario})
            </p>
          </div>
        </div>

        <button
          onClick={onRerunBenchmark}
          disabled={isLoading}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50"
        >
          <span>Re-ejecutar Benchmark</span>
        </button>
      </div>

      {/* Comparative Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Metric 1: Mean Response Time */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <span className="text-xs text-slate-500 font-medium">Tiempo Promedio de Respuesta</span>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Tradicional</div>
              <div className="text-lg font-bold text-slate-700">{trad.tiempo_promedio_respuesta.toFixed(1)} min</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400" />
            <div>
              <div className="text-xs text-indigo-600 font-bold">Predictivo</div>
              <div className="text-xl font-extrabold text-indigo-700">{pred.tiempo_promedio_respuesta.toFixed(1)} min</div>
            </div>
          </div>
          <div className="pt-1 text-[11px] text-emerald-600 font-semibold flex items-center space-x-1 border-t border-slate-100">
            <TrendingDown className="w-3.5 h-3.5" />
            <span>Reducción de {res.reduccion_tiempo_promedio_min} min ({((res.reduccion_tiempo_promedio_min / trad.tiempo_promedio_respuesta) * 100).toFixed(1)}%)</span>
          </div>
        </div>

        {/* Metric 2: Compliance < 8 min */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <span className="text-xs text-slate-500 font-medium">Cumplimiento Meta &lt; 8 Minutos</span>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Tradicional</div>
              <div className="text-lg font-bold text-slate-700">{trad.porcentaje_menor_8min.toFixed(1)}%</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400" />
            <div>
              <div className="text-xs text-indigo-600 font-bold">Predictivo</div>
              <div className="text-xl font-extrabold text-emerald-600">{pred.porcentaje_menor_8min.toFixed(1)}%</div>
            </div>
          </div>
          <div className="pt-1 text-[11px] text-emerald-600 font-semibold flex items-center space-x-1 border-t border-slate-100">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Aumento de +{res.aumento_cumplimiento_8min_pct}% puntos porcentuales</span>
          </div>
        </div>

        {/* Metric 3: Disparity Ratio (Equity) */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <span className="text-xs text-slate-500 font-medium">Razón de Disparidad (Equidad)</span>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Tradicional</div>
              <div className="text-lg font-bold text-rose-600">{trad.razon_disparidad.toFixed(2)}</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400" />
            <div>
              <div className="text-xs text-indigo-600 font-bold">Predictivo</div>
              <div className="text-xl font-extrabold text-indigo-700">{pred.razon_disparidad.toFixed(2)}</div>
            </div>
          </div>
          <div className="pt-1 text-[11px] text-emerald-600 font-semibold flex items-center space-x-1 border-t border-slate-100">
            <Scale className="w-3.5 h-3.5" />
            <span>Mejora de equidad hacia 1.0 (Δ -{res.mejora_razon_disparidad.toFixed(2)})</span>
          </div>
        </div>

        {/* Metric 4: Vulnerable Sector Q1 Time */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-2">
          <span className="text-xs text-slate-500 font-medium">Tiempo Respuesta en Q1 (Más Vulnerable)</span>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-slate-400">Tradicional</div>
              <div className="text-lg font-bold text-rose-600">{res.tiempo_promedio_q1_trad.toFixed(1)} min</div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400" />
            <div>
              <div className="text-xs text-indigo-600 font-bold">Predictivo</div>
              <div className="text-xl font-extrabold text-emerald-600">{res.tiempo_promedio_q1_pred.toFixed(1)} min</div>
            </div>
          </div>
          <div className="pt-1 text-[11px] text-emerald-600 font-semibold flex items-center space-x-1 border-t border-slate-100">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Ahorro de {(res.tiempo_promedio_q1_trad - res.tiempo_promedio_q1_pred).toFixed(1)} min en comunidades vulnerables</span>
          </div>
        </div>
      </div>

      {/* Side-by-side Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Chart 1: Mean Response Time by Quintile */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
            <h4 className="font-bold text-xs text-slate-900">
              Tiempo Promedio de Respuesta por Quintil Socioeconómico (Minutos)
            </h4>
            <span className="text-[10px] text-slate-400">Menor es mejor</span>
          </div>

          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={responseTimeByQuintileData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="quintil" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar dataKey="Despacho Tradicional" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Despacho Predictivo" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Compliance < 8 min by Quintile */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
            <h4 className="font-bold text-xs text-slate-900">
              Porcentaje Atendido en Menos de 8 Minutos (% por Quintil)
            </h4>
            <span className="text-[10px] text-slate-400">Mayor es mejor</span>
          </div>

          <div className="h-[250px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={compliance8MinByQuintileData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="quintil" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 100]} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '11px' }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar dataKey="Despacho Tradicional" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Despacho Predictivo" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Response Time Histogram / Distribution */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
          <h4 className="font-bold text-xs text-slate-900">
            Distribución de Frecuencia de Tiempos de Respuesta (Histograma de Emergencias Atendidas)
          </h4>
          <span className="text-[10px] text-slate-400">Intervalos de tiempo</span>
        </div>

        <div className="h-[220px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogramData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="rango" tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '11px' }}
              />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              <Bar dataKey="Tradicional (Frecuencia)" fill="#f87171" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Predictivo (Frecuencia)" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Comprehensive Academic Results Table */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <h4 className="font-bold text-xs text-slate-900 border-b border-slate-100 pb-2 mb-3">
          Tabla Resumen de Indicadores Clave de Desempeño y Equidad
        </h4>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th className="p-2.5">Métrica Operativa / Equidad</th>
                <th className="p-2.5 text-center">Despacho Tradicional</th>
                <th className="p-2.5 text-center">Despacho Predictivo</th>
                <th className="p-2.5 text-center">Diferencia Absoluta</th>
                <th className="p-2.5 text-right">Variación Porcentual</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Tiempo Promedio de Respuesta</td>
                <td className="p-2.5 text-center font-mono">{trad.tiempo_promedio_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono font-bold text-indigo-700">{pred.tiempo_promedio_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono text-emerald-600 font-semibold">-{res.reduccion_tiempo_promedio_min} min</td>
                <td className="p-2.5 text-right font-mono text-emerald-600 font-bold">
                  -{((res.reduccion_tiempo_promedio_min / trad.tiempo_promedio_respuesta) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Mediana de Respuesta</td>
                <td className="p-2.5 text-center font-mono">{trad.mediana_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono font-bold text-indigo-700">{pred.mediana_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono text-emerald-600 font-semibold">
                  -{(trad.mediana_respuesta - pred.mediana_respuesta).toFixed(2)} min
                </td>
                <td className="p-2.5 text-right font-mono text-emerald-600 font-bold">
                  -{(((trad.mediana_respuesta - pred.mediana_respuesta) / trad.mediana_respuesta) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Percentil 90 (P90)</td>
                <td className="p-2.5 text-center font-mono">{trad.p90_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono font-bold text-indigo-700">{pred.p90_respuesta.toFixed(2)} min</td>
                <td className="p-2.5 text-center font-mono text-emerald-600 font-semibold">
                  -{(trad.p90_respuesta - pred.p90_respuesta).toFixed(2)} min
                </td>
                <td className="p-2.5 text-right font-mono text-emerald-600 font-bold">
                  -{(((trad.p90_respuesta - pred.p90_respuesta) / trad.p90_respuesta) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Cumplimiento &lt; 8 min (%)</td>
                <td className="p-2.5 text-center font-mono">{trad.porcentaje_menor_8min.toFixed(1)}%</td>
                <td className="p-2.5 text-center font-mono font-bold text-emerald-600">{pred.porcentaje_menor_8min.toFixed(1)}%</td>
                <td className="p-2.5 text-center font-mono text-emerald-600 font-semibold">+{res.aumento_cumplimiento_8min_pct}%</td>
                <td className="p-2.5 text-right font-mono text-emerald-600 font-bold">
                  +{(((pred.porcentaje_menor_8min - trad.porcentaje_menor_8min) / trad.porcentaje_menor_8min) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Razón de Disparidad (Equidad)</td>
                <td className="p-2.5 text-center font-mono text-rose-600">{trad.razon_disparidad.toFixed(3)}</td>
                <td className="p-2.5 text-center font-mono font-bold text-indigo-700">{pred.razon_disparidad.toFixed(3)}</td>
                <td className="p-2.5 text-center font-mono text-emerald-600 font-semibold">-{res.mejora_razon_disparidad.toFixed(3)}</td>
                <td className="p-2.5 text-right font-mono text-emerald-600 font-bold">
                  -{((res.mejora_razon_disparidad / trad.razon_disparidad) * 100).toFixed(1)}%
                </td>
              </tr>
              <tr>
                <td className="p-2.5 font-medium text-slate-800">Distancia Total Recorrida</td>
                <td className="p-2.5 text-center font-mono">{trad.distancia_total_km.toFixed(1)} km</td>
                <td className="p-2.5 text-center font-mono text-slate-700">{pred.distancia_total_km.toFixed(1)} km</td>
                <td className="p-2.5 text-center font-mono text-slate-600">
                  {(pred.distancia_total_km - trad.distancia_total_km).toFixed(1)} km
                </td>
                <td className="p-2.5 text-right font-mono text-slate-600">
                  {(((pred.distancia_total_km - trad.distancia_total_km) / trad.distancia_total_km) * 100).toFixed(1)}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
