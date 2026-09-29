import React from 'react';
import { ComparisonBenchmarkResult } from '../services/comparisonService';
import { ArrowRight, BarChart3, CheckCircle2, Clock, FileText, GitCompare, Loader2, Play, TrendingDown } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface ComparisonViewProps {
  benchmark: ComparisonBenchmarkResult | null;
  onRerunBenchmark: () => void;
  isLoading: boolean;
}

const format = (value: number | null | undefined, digits = 1) =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : 'N/D';

export const ComparisonView: React.FC<ComparisonViewProps> = ({ benchmark, onRerunBenchmark, isLoading }) => {
  if (!benchmark) {
    return (
      <div className="bg-white p-8 rounded-lg border border-slate-200 text-center space-y-4" id="comparison-empty">
        <GitCompare className="w-12 h-12 text-indigo-500 mx-auto" />
        <div>
          <h3 className="font-bold text-lg text-slate-800">Experimento pareado listo para ejecutar</h3>
          <p className="text-sm text-slate-500 max-w-xl mx-auto mt-2">
            Compara despacho tradicional y predictivo con la misma ventana, flota, modelo y semillas. En NYC genera resultados de Fase 8.
          </p>
        </div>
        <button
          onClick={onRerunBenchmark}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Ejecutar experimento
        </button>
      </div>
    );
  }

  const trad = benchmark.traditional_run.metrics;
  const pred = benchmark.predictive_run.metrics;
  const res = benchmark.resumen_ejecutivo;
  const isHistorical = Boolean(benchmark.experiment);
  const ci = benchmark.statistical_tests.bootstrap_ci;
  const replicationData = (benchmark.replications || []).map((rep) => ({
    replica: `R${rep.replica}`,
    'Delta media': rep.delta.mean_response_min,
    'Delta P90': rep.delta.p90_response_min,
    'Delta <8m': rep.delta.under_8min_pct,
    'Pares': rep.paired_incidents,
  }));

  const metricRows = [
    {
      label: 'Tiempo medio de respuesta',
      traditional: `${format(trad.tiempo_promedio_respuesta)} min`,
      predictive: `${format(pred.tiempo_promedio_respuesta)} min`,
      delta: `${format(res.reduccion_tiempo_promedio_min)} min`,
      positive: res.reduccion_tiempo_promedio_min >= 0,
    },
    {
      label: 'P90 de respuesta',
      traditional: `${format(trad.p90_respuesta)} min`,
      predictive: `${format(pred.p90_respuesta)} min`,
      delta: `${format(res.reduccion_p90_min ?? trad.p90_respuesta - pred.p90_respuesta)} min`,
      positive: (res.reduccion_p90_min ?? trad.p90_respuesta - pred.p90_respuesta) >= 0,
    },
    {
      label: 'Cumplimiento menor a 8 min',
      traditional: `${format(trad.porcentaje_menor_8min)}%`,
      predictive: `${format(pred.porcentaje_menor_8min)}%`,
      delta: `${format(res.aumento_cumplimiento_8min_pct)} pp`,
      positive: res.aumento_cumplimiento_8min_pct >= 0,
    },
    {
      label: 'No finalizados al corte',
      traditional: `${format(benchmark.replications?.[0]?.traditional.unfinished ?? 0, 0)}`,
      predictive: `${format(benchmark.replications?.[0]?.predictive.unfinished ?? 0, 0)}`,
      delta: `${format(res.reduccion_no_finalizados ?? 0, 1)}`,
      positive: (res.reduccion_no_finalizados ?? 0) >= 0,
    },
  ];

  return (
    <div className="space-y-4" id="policy-comparison-view">
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">
              {isHistorical ? 'Fase 8: experimento pareado NYC' : 'Benchmark pareado demo'}
            </h3>
            <p className="text-xs text-slate-500">
              {isHistorical
                ? `${benchmark.experiment?.repetitions} replicas · ${benchmark.duracion_min} min · ${benchmark.num_ambulancias} ambulancias · ${benchmark.model_id}`
                : `Semilla ${benchmark.semilla} · escenario ${benchmark.scenario}`}
            </p>
          </div>
        </div>

        <button
          onClick={onRerunBenchmark}
          disabled={isLoading}
          className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-60"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          Re-ejecutar
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <span className="text-xs text-slate-500">Delta medio</span>
          <p className={`mt-1 text-2xl font-bold ${res.reduccion_tiempo_promedio_min >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
            {format(res.reduccion_tiempo_promedio_min)} min
          </p>
          <p className="text-xs text-slate-500">Tradicional - predictivo</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <span className="text-xs text-slate-500">IC 95% bootstrap</span>
          <p className="mt-1 text-xl font-bold text-slate-900">
            [{format(ci.delta_tiempo_promedio.ci_lower)}, {format(ci.delta_tiempo_promedio.ci_upper)}]
          </p>
          <p className="text-xs text-slate-500">minutos</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <span className="text-xs text-slate-500">Prueba pareada</span>
          <p className="mt-1 text-xl font-bold text-slate-900">p={format(benchmark.statistical_tests.t_test.p_value, 4)}</p>
          <p className="text-xs text-slate-500">{benchmark.statistical_tests.t_test.significant_p05 ? 'Diferencia significativa' : 'No significativa'}</p>
        </div>
        <div className="bg-white p-4 rounded-lg border border-slate-200">
          <span className="text-xs text-slate-500">Pares de incidentes</span>
          <p className="mt-1 text-2xl font-bold text-slate-900">
            {format(benchmark.replications?.reduce((sum, rep) => sum + rep.paired_incidents, 0) || benchmark.traditional_run.incidents.length, 0)}
          </p>
          <p className="text-xs text-slate-500">usados como trazabilidad</p>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg border border-slate-200">
        <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
          <h4 className="font-bold text-xs text-slate-900">Resumen de indicadores</h4>
          <span className="text-[11px] text-slate-500">Delta positivo favorece predictivo</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th className="p-2.5">Metrica</th>
                <th className="p-2.5 text-center">Tradicional</th>
                <th className="p-2.5 text-center">Predictivo</th>
                <th className="p-2.5 text-right">Delta</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {metricRows.map((row) => (
                <tr key={row.label}>
                  <td className="p-2.5 font-medium text-slate-800">{row.label}</td>
                  <td className="p-2.5 text-center font-mono">{row.traditional}</td>
                  <td className="p-2.5 text-center font-mono font-semibold text-indigo-700">{row.predictive}</td>
                  <td className={`p-2.5 text-right font-mono font-bold ${row.positive ? 'text-emerald-700' : 'text-rose-700'}`}>{row.delta}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {replicationData.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="bg-white p-4 rounded-lg border border-slate-200">
            <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
              <TrendingDown className="w-4 h-4 text-emerald-700" />
              <h4 className="font-bold text-xs text-slate-900">Deltas por replica</h4>
            </div>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={replicationData} margin={{ top: 10, right: 20, left: -15, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="replica" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line type="monotone" dataKey="Delta media" stroke="#059669" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Delta P90" stroke="#4f46e5" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border border-slate-200">
            <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
              <BarChart3 className="w-4 h-4 text-indigo-700" />
              <h4 className="font-bold text-xs text-slate-900">Cumplimiento y pares</h4>
            </div>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={replicationData} margin={{ top: 10, right: 20, left: -15, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="replica" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Bar dataKey="Delta <8m" fill="#14b8a6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Pares" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white p-4 rounded-lg border border-slate-200">
        <div className="mb-2 flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-600" />
          <h4 className="text-sm font-semibold text-slate-900">Interpretacion</h4>
        </div>
        <p className="text-sm leading-6 text-slate-700">
          {res.interpretacion ||
            'La comparacion usa la misma demanda y semilla para ambas politicas. Una diferencia positiva en tiempo indica menor respuesta promedio con la politica predictiva.'}
        </p>
        {benchmark.limitations && (
          <ul className="mt-3 space-y-1 text-xs text-slate-500">
            {benchmark.limitations.map((item) => (
              <li key={item} className="flex gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
        {benchmark.artifacts && (
          <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-600">
            <FileText className="h-3.5 w-3.5" />
            Reporte exportado en {benchmark.artifacts.markdown}
          </p>
        )}
      </div>

      {!isHistorical && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Este resultado pertenece al modo demo. Para el articulo usa el experimento NYC de Fase 8.
        </div>
      )}
    </div>
  );
};
