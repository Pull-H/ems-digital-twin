import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, BarChart3, Download, FileSpreadsheet, Loader2, Table2 } from 'lucide-react';
import type { DemandPrediction, HistoricalDatasetProfile, ModelPerformanceReport, SimulationState } from '../../types';
import { modelPerformanceApi } from '../../services/apiClient';

interface Props {
  profile: HistoricalDatasetProfile;
  state: SimulationState;
}

const numberValue = (value: string | number | undefined, digits = 3) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 'N/D';
  return parsed.toFixed(digits);
};

const riskBadge = (risk: DemandPrediction['nivel_riesgo']) => {
  if (risk === 'alto') return 'bg-rose-100 text-rose-800 border-rose-200';
  if (risk === 'medio') return 'bg-amber-100 text-amber-800 border-amber-200';
  return 'bg-emerald-100 text-emerald-800 border-emerald-200';
};

export function ModelPerformancePanel({ profile, state }: Props) {
  const [report, setReport] = useState<ModelPerformanceReport | null>(null);
  const [selectedFigure, setSelectedFigure] = useState<string>('global_test_metrics');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    modelPerformanceApi
      .getReport(profile.id)
      .then((data) => {
        if (!active) return;
        setReport(data);
        setSelectedFigure(data.figures[0]?.id || 'global_test_metrics');
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'No se pudo cargar el reporte de modelos.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [profile.id]);

  const testRows = useMemo(() => {
    const rows = report?.tables.global_model_metrics?.rows || [];
    return rows.filter((row) => row.split === 'test');
  }, [report]);

  const bestByMae = useMemo(() => {
    if (testRows.length === 0) return null;
    return [...testRows].sort((a, b) => Number(a.mae) - Number(b.mae))[0];
  }, [testRows]);

  const figure = report?.figures.find((item) => item.id === selectedFigure) || report?.figures[0];
  const topPredictions = [...state.predictions].sort((a, b) => b.demanda_predicha_ml - a.demanda_predicha_ml);
  const downloadFigure = () => {
    if (!figure) return;
    const blob = new Blob([figure.svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${figure.id}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <section className="grid min-h-[360px] place-content-center rounded-lg border border-slate-200 bg-white text-sm text-slate-600">
        <span className="inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando rendimiento predictivo...
        </span>
      </section>
    );
  }

  if (error || !report) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
        <div className="flex items-center gap-2 font-semibold">
          <AlertCircle className="h-4 w-4" />
          No se pudo cargar el reporte visual
        </div>
        <p className="mt-2">{error}</p>
      </section>
    );
  }

  return (
    <section className="space-y-4" id="model-performance-panel">
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-indigo-200 bg-indigo-50 text-indigo-700">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Rendimiento de modelos predictivos</h2>
            <p className="text-xs text-slate-500">
              Snapshot {profile.id} · modelo activo {state.model_id} · horizonte 60 min
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">
          <Download className="h-4 w-4" />
          {report.report_path || 'Reporte local'}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <span className="text-xs text-slate-500">Seleccionado por validacion</span>
          <p className="mt-1 text-lg font-bold text-slate-900">{profile.model_selection.best_model_id || state.model_id}</p>
          <p className="text-xs text-slate-500">{profile.model_selection.criterion || 'criterio documentado en Fase 5'}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <span className="text-xs text-slate-500">Mejor MAE en prueba</span>
          <p className="mt-1 text-lg font-bold text-emerald-700">{bestByMae?.model_label || 'N/D'}</p>
          <p className="text-xs text-slate-500">MAE {numberValue(bestByMae?.mae)}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <span className="text-xs text-slate-500">WAPE menor</span>
          <p className="mt-1 text-lg font-bold text-indigo-700">
            {testRows.length ? `${numberValue(Math.min(...testRows.map((row) => Number(row.wape_pct))), 2)}%` : 'N/D'}
          </p>
          <p className="text-xs text-slate-500">error porcentual ponderado</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <span className="text-xs text-slate-500">Boroughs evaluados</span>
          <p className="mt-1 text-lg font-bold text-slate-900">{state.zones.length}</p>
          <p className="text-xs text-slate-500">unidad de pronostico actual</p>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex flex-wrap gap-2">
          {report.figures.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedFigure(item.id)}
              className={`rounded-md px-3 py-2 text-xs font-semibold ${
                selectedFigure === item.id ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-slate-50 text-slate-700'
              }`}
            >
              {item.title}
            </button>
          ))}
        </div>
        {figure && (
          <>
            <div className="mb-2 flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">{figure.title}</h3>
                <p className="text-xs text-slate-500">{figure.description}</p>
              </div>
              <button type="button" onClick={downloadFigure} className="text-xs font-semibold text-indigo-700">
                Descargar SVG
              </button>
            </div>
            <div
              className="overflow-x-auto rounded-md border border-slate-100 bg-white [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
              dangerouslySetInnerHTML={{ __html: figure.svg }}
            />
          </>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
            <Table2 className="h-4 w-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900">Tabla global de prueba</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {['Modelo', 'MAE', 'RMSE', 'WAPE %', 'Sesgo'].map((header) => (
                    <th key={header} className="p-2 font-semibold">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {testRows.map((row) => (
                  <tr key={row.model_id}>
                    <td className="p-2 font-medium text-slate-900">{row.model_label}</td>
                    <td className="p-2 font-mono">{numberValue(row.mae)}</td>
                    <td className="p-2 font-mono">{numberValue(row.rmse)}</td>
                    <td className="p-2 font-mono">{numberValue(row.wape_pct, 2)}%</td>
                    <td className="p-2 font-mono">{numberValue(row.bias)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            No se muestra matriz de confusion porque la tarea es regresion de conteos horarios, no clasificacion.
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
            <FileSpreadsheet className="h-4 w-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900">Pronostico activo por borough</h3>
          </div>
          <div className="space-y-2">
            {topPredictions.map((prediction) => (
              <div key={prediction.zona_id} className="flex items-center justify-between rounded-md border border-slate-100 px-3 py-2">
                <div>
                  <p className="text-xs font-semibold text-slate-900">{prediction.zona_nombre}</p>
                  <p className="text-[11px] text-slate-500">Base {prediction.demanda_predicha_base.toFixed(1)}/h</p>
                </div>
                <div className="text-right">
                  <p className="font-mono text-sm font-bold text-slate-900">{prediction.demanda_predicha_ml.toFixed(1)}/h</p>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${riskBadge(prediction.nivel_riesgo)}`}>
                    {prediction.nivel_riesgo}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
