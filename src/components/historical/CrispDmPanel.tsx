import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, BookOpenCheck, CheckCircle2, Database, GitBranch, Loader2, Table2 } from 'lucide-react';
import type { CrispDmReport, HistoricalDatasetProfile } from '../../types';
import { crispDmApi } from '../../services/apiClient';

interface Props {
  profile: HistoricalDatasetProfile;
}

const preferredTables = [
  'crisp_dm_traceability',
  'eda_quality_summary',
  'temporal_cv_metrics',
  'hyperparameter_search',
  'model_statistical_tests',
  'interpretability_feature_importance',
];

const short = (value: string | undefined, max = 68) => {
  if (!value) return 'N/D';
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
};

export function CrispDmPanel({ profile }: Props) {
  const [report, setReport] = useState<CrispDmReport | null>(null);
  const [selectedFigure, setSelectedFigure] = useState<string>('crisp_dm_flow');
  const [selectedTable, setSelectedTable] = useState<string>('crisp_dm_traceability');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    crispDmApi
      .getReport(profile.id)
      .then((data) => {
        if (!active) return;
        setReport(data);
        setSelectedFigure(data.figures[0]?.id || 'crisp_dm_flow');
        setSelectedTable(preferredTables.find((key) => data.tables[key]) || Object.keys(data.tables)[0] || 'crisp_dm_traceability');
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'No se pudo cargar CRISP-DM.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [profile.id]);

  const figure = report?.figures.find((item) => item.id === selectedFigure) || report?.figures[0];
  const table = report?.tables[selectedTable];
  const tableKeys = useMemo(() => (table?.rows[0] ? Object.keys(table.rows[0]) : []), [table]);
  const interpretationRows = report?.tables.artifact_interpretation?.rows || [];
  const figureInterpretation = interpretationRows.find((row) =>
    row.artifact_id === figure?.id || Boolean(figure?.id && row.artifact_id?.endsWith(figure.id))
  );

  if (loading) {
    return (
      <section className="grid min-h-[320px] place-content-center rounded-lg border border-slate-200 bg-white text-sm text-slate-600">
        <span className="inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando evidencia CRISP-DM...
        </span>
      </section>
    );
  }

  if (error || !report) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">
        <div className="flex items-center gap-2 font-semibold">
          <AlertCircle className="h-4 w-4" />
          No se pudo cargar la metodologia CRISP-DM
        </div>
        <p className="mt-2">{error}</p>
      </section>
    );
  }

  return (
    <section className="space-y-4" id="crisp-dm-panel">
      <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-teal-200 bg-teal-50 text-teal-700">
            <BookOpenCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Metodologia CRISP-DM del proyecto</h2>
            <p className="text-xs text-slate-500">
              Snapshot {report.dataset_id} · {report.methodology}
            </p>
          </div>
        </div>
        <span className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700">
          {report.report_path || 'Reporte CRISP-DM local'}
        </span>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {Object.entries(report.key_findings).map(([key, value]) => (
          <div key={key} className="rounded-lg border border-slate-200 bg-white p-4">
            <span className="text-xs font-semibold uppercase text-slate-500">{key}</span>
            <p className="mt-1 text-xs leading-5 text-slate-700">{value}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
            <GitBranch className="h-4 w-4 text-slate-600" />
            <h3 className="text-sm font-semibold text-slate-900">6 graficos metodologicos</h3>
          </div>
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
              <div
                className="overflow-x-auto rounded-md border border-slate-100 bg-white [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
                dangerouslySetInnerHTML={{ __html: figure.svg }}
              />
              <div className="mt-3 rounded-md border border-indigo-100 bg-indigo-50 p-3 text-xs text-indigo-950">
                <p className="font-semibold">Interpretabilidad</p>
                <p>{figureInterpretation?.interpretability || 'Grafico metodologico con lectura documentada en artifact_interpretation.csv.'}</p>
                <p className="mt-1 font-semibold">Explicabilidad</p>
                <p>{figureInterpretation?.explainability_note || 'El grafico separa evidencia descriptiva de inferencia causal.'}</p>
              </div>
            </>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-semibold text-slate-900">Fases CRISP-DM cubiertas</h3>
          </div>
          <div className="space-y-2">
            {(report.tables.crisp_dm_traceability?.rows || []).map((row) => (
              <div key={row.crisp_dm_phase} className="rounded-md border border-slate-100 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-slate-900">{row.crisp_dm_phase}</p>
                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
                    {row.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-600">{row.software_evidence}</p>
                <p className="mt-1 font-mono text-[10px] text-slate-500">{row.artifact}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <div className="mb-3 flex items-center gap-2 border-b border-slate-100 pb-2">
          <Table2 className="h-4 w-4 text-slate-600" />
          <h3 className="text-sm font-semibold text-slate-900">6 tablas principales y tabla de interpretacion</h3>
        </div>
        <div className="mb-3 flex flex-wrap gap-2">
          {preferredTables.filter((key) => report.tables[key]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setSelectedTable(key)}
              className={`rounded-md px-3 py-2 text-xs font-semibold ${
                selectedTable === key ? 'bg-slate-900 text-white' : 'border border-slate-200 bg-slate-50 text-slate-700'
              }`}
            >
              {report.tables[key].title}
            </button>
          ))}
        </div>
        {table && (
          <>
            <div className="mb-2 flex items-center gap-2 text-xs text-slate-500">
              <Database className="h-4 w-4" />
              <span>{table.path}</span>
            </div>
            <div className="max-h-[420px] overflow-auto rounded-md border border-slate-100">
              <table className="w-full min-w-[760px] text-left text-xs">
                <thead className="sticky top-0 bg-slate-50 text-slate-500">
                  <tr>
                    {tableKeys.map((key) => (
                      <th key={key} className="p-2 font-semibold">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {table.rows.slice(0, 80).map((row, index) => (
                    <tr key={`${selectedTable}-${index}`}>
                      {tableKeys.map((key) => (
                        <td key={key} className="p-2 align-top text-slate-700">{short(row[key])}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
