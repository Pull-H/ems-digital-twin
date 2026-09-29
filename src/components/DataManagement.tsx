import React, { useEffect, useState } from 'react';
import { HistoricalDatasetProfile, HistoricalDatasetSummary, Incident, SimulationMetrics } from '../types';
import { Download, Upload, Database, FileSpreadsheet, Search, CheckCircle2, PlayCircle } from 'lucide-react';
import { datasetApi } from '../services/apiClient';

interface DataManagementProps {
  incidents: Incident[];
  metrics: SimulationMetrics;
  datasetProfile: HistoricalDatasetProfile | null;
  onLoadHistoricalDataset: (datasetId: string) => Promise<void>;
  onImportIncidents: (newIncidents: Incident[]) => void;
}

export const DataManagement: React.FC<DataManagementProps> = ({
  incidents,
  metrics,
  datasetProfile,
  onLoadHistoricalDataset,
  onImportIncidents,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterQuintile, setFilterQuintile] = useState<string>('todos');
  const [filterPriority, setFilterPriority] = useState<string>('todos');
  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<HistoricalDatasetSummary[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [isLoadingHistorical, setIsLoadingHistorical] = useState(false);

  useEffect(() => {
    void datasetApi
      .listDatasets()
      .then((result) => {
        setDatasets(result.datasets);
        const ready = result.datasets.find((dataset) => dataset.historical_ready);
        if (ready) setSelectedDatasetId(ready.id);
      })
      .catch((err) => {
        console.warn('No se pudo listar datasets historicos:', err);
      });
  }, []);

  // Filter incidents for data table
  const filteredIncidents = incidents.filter((inc) => {
    const matchesSearch =
      inc.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      inc.tipo.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (inc.ambulancia_id && String(inc.ambulancia_id).includes(searchTerm));

    const matchesQuintile =
      filterQuintile === 'todos' || inc.quintil_socioeconomico === parseInt(filterQuintile);

    const matchesPriority = filterPriority === 'todos' || inc.prioridad === filterPriority;

    return matchesSearch && matchesQuintile && matchesPriority;
  });

  // Export Incidents CSV
  const handleExportIncidentsCSV = () => {
    const headers = [
      'id',
      'tiempo_llamada_min',
      'zona_id',
      'quintil_socioeconomico',
      'tipo_emergencia',
      'prioridad',
      'latitud',
      'longitud',
      'estado',
      'ambulancia_id',
      'tiempo_despacho_min',
      'tiempo_llegada_escena_min',
      'tiempo_respuesta_min',
      'duracion_atencion_escena_min',
      'hospital_id',
      'cumple_meta_8min',
    ];

    const rows = incidents.map((inc) => [
      inc.id,
      inc.tiempo_llamada,
      inc.zona_id,
      inc.quintil_socioeconomico,
      `"${inc.tipo}"`,
      inc.prioridad,
      inc.latitud.toFixed(5),
      inc.longitud.toFixed(5),
      inc.estado,
      inc.ambulancia_id || '',
      inc.tiempo_despacho ?? '',
      inc.tiempo_llegada_escena ?? '',
      inc.tiempo_respuesta_min ?? '',
      inc.duracion_atencion_escena_min,
      inc.hospital_id || '',
      inc.tiempo_respuesta_min ? (inc.tiempo_respuesta_min <= 8 ? 1 : 0) : '',
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `ems_incidents_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Export Metrics Summary CSV
  const handleExportMetricsCSV = () => {
    const headers = ['metrica', 'valor', 'unidad'];
    const rows = [
      ['incidentes_totales', metrics.incidentes_totales, 'llamadas'],
      ['incidentes_atendidos', metrics.incidentes_atendidos, 'llamadas'],
      ['incidentes_pendientes', metrics.incidentes_pendientes, 'llamadas'],
      ['tiempo_promedio_respuesta', metrics.tiempo_promedio_respuesta.toFixed(2), 'minutos'],
      ['mediana_respuesta', metrics.mediana_respuesta.toFixed(2), 'minutos'],
      ['p90_respuesta', metrics.p90_respuesta.toFixed(2), 'minutos'],
      ['porcentaje_menor_8min', metrics.porcentaje_menor_8min.toFixed(1), '%'],
      ['razon_disparidad_q1_q5', metrics.razon_disparidad?.toFixed(3) ?? 'no_disponible', 'ratio'],
      ['diferencia_max_min_quintiles', metrics.diferencia_max_min_quintiles?.toFixed(2) ?? 'no_disponible', 'minutos'],
      ['distancia_total_km', metrics.distancia_total_km.toFixed(1), 'km'],
      ['utilizacion_ambulancias', (metrics.utilizacion_ambulancias * 100).toFixed(1), '%'],
    ];

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `ems_metrics_summary_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // File Upload Handler (CSV Parser)
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const lines = text.split('\n').filter((l) => l.trim().length > 0);
        if (lines.length <= 1) {
          setImportStatus('El archivo CSV está vacío o solo contiene encabezados.');
          return;
        }

        const headers = lines[0].split(',').map((h) => h.trim().toLowerCase());
        const parsed: Incident[] = [];

        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',');
          if (values.length >= 6) {
            const inc: Incident = {
              id: values[0]?.trim() || `IMP-${i}`,
              fecha_hora: new Date().toISOString(),
              sim_time_min: parseFloat(values[1]) || 0,
              tiempo_llamada: parseFloat(values[1]) || 0,
              zona_id: parseInt(values[2]) || 1,
              quintil_socioeconomico: (parseInt(values[3]) || 3) as any,
              tipo: (values[4]?.replace(/"/g, '').trim() || 'otro') as any,
              prioridad: (values[5]?.trim() as any) || 'media',
              latitud: parseFloat(values[6]) || -8.11,
              longitud: parseFloat(values[7]) || -79.03,
              estado: 'completado',
              ambulancia_id: parseInt(values[9]) || null,
              hospital_id: parseInt(values[14]) || null,
              tiempo_despacho: parseFloat(values[10]) || null,
              tiempo_llegada_escena: parseFloat(values[11]) || null,
              duracion_atencion_escena_min: parseFloat(values[13]) || 15,
              requiere_traslado: true,
              tiempo_llegada_hospital: null,
              tiempo_liberacion: null,
              tiempo_respuesta_min: parseFloat(values[12]) || 7.5,
            };
            parsed.push(inc);
          }
        }

        if (parsed.length > 0) {
          onImportIncidents(parsed);
          setImportStatus(`Se importaron exitosamente ${parsed.length} llamadas históricas.`);
        }
      } catch (err: any) {
        setImportStatus(`Error al procesar el archivo CSV: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  const handleLoadHistorical = async () => {
    if (!selectedDatasetId) return;
    setIsLoadingHistorical(true);
    try {
      await onLoadHistoricalDataset(selectedDatasetId);
      setImportStatus('Dataset historico cargado en el simulador.');
    } finally {
      setIsLoadingHistorical(false);
    }
  };

  return (
    <div className="space-y-4" id="data-management-view">
      {/* Top Banner & Export Action Buttons */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm">Gestor de Datos, Registro de Llamadas & Exportación CSV</h3>
            <p className="text-xs text-slate-500">
              {datasetProfile ? 'Muestra visible de la corrida simulada' : 'Registros cargados'}: {incidents.length} llamadas. Total de la corrida: {metrics.incidentes_totales}.
            </p>
          </div>
        </div>

        {/* Action Buttons: Export & Import */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleExportIncidentsCSV}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Exportar Llamadas (.CSV)</span>
          </button>

          <button
            onClick={handleExportMetricsCSV}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-xs transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" />
            <span>Exportar Métricas</span>
          </button>

          <label className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold border border-indigo-200 cursor-pointer transition-colors">
            <Upload className="w-3.5 h-3.5" />
            <span>Importar CSV</span>
            <input type="file" accept=".csv" onChange={handleFileUpload} disabled={Boolean(datasetProfile)} className="hidden" />
          </label>
        </div>
      </div>

      {/* Import Status Alert */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-bold text-slate-900 text-sm">Dataset historico NYC EMS</h4>
              <p className="text-xs text-slate-500">
                Snapshot preparado por fases 1-6 para reproduccion historica y predicciones retrospectivas.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <select
              value={selectedDatasetId}
              onChange={(event) => setSelectedDatasetId(event.target.value)}
              className="bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800"
            >
              <option value="">Sin snapshot listo</option>
              {datasets.map((dataset) => (
                <option key={dataset.id} value={dataset.id} disabled={!dataset.historical_ready}>
                  {dataset.id} {dataset.historical_ready ? '' : '(pendiente)'}
                </option>
              ))}
            </select>

            <button
              onClick={handleLoadHistorical}
              disabled={!selectedDatasetId || isLoadingHistorical}
              className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:text-slate-500 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <PlayCircle className="w-3.5 h-3.5" />
              <span>{isLoadingHistorical ? 'Cargando...' : 'Cargar histórico'}</span>
            </button>
          </div>
        </div>

        {datasetProfile && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-xs">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="block text-slate-500">Incidentes</span>
              <strong className="text-slate-900 text-lg">{datasetProfile.expected_rows.toLocaleString()}</strong>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="block text-slate-500">Respuestas válidas</span>
              <strong className="text-slate-900 text-lg">
                {(datasetProfile.phase6.observed_response_rows || 0).toLocaleString()}
              </strong>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="block text-slate-500">Mediana respuesta</span>
              <strong className="text-slate-900 text-lg">
                {datasetProfile.calibration_global.response_min?.median?.toFixed(2) || '0.00'} min
              </strong>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <span className="block text-slate-500">Modelo seleccionado</span>
              <strong className="text-slate-900 text-sm">{datasetProfile.model_selection.best_model_id || 'N/D'}</strong>
            </div>
          </div>
        )}
      </div>

      {importStatus && (
        <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl flex items-center justify-between text-xs text-indigo-900">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-indigo-600" />
            <span>{importStatus}</span>
          </div>
          <button onClick={() => setImportStatus(null)} className="font-bold text-slate-500 hover:text-slate-700">
            ✕
          </button>
        </div>
      )}

      {/* Interactive Incidents Data Table */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        {/* Table Search & Filters */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Buscar por ID, tipo o unidad..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            />
          </div>

          <div className="flex items-center space-x-2 text-xs">
            {/* Quintile Filter */}
            <div className="flex items-center space-x-1">
              <span className="text-slate-500 font-medium">Quintil:</span>
              <select
                value={filterQuintile}
                disabled={Boolean(datasetProfile)}
                onChange={(e) => setFilterQuintile(e.target.value)}
                className="bg-slate-50 border border-slate-300 rounded p-1 text-xs"
              >
                <option value="todos">Todos (Q1-Q5)</option>
                <option value="1">Q1 (Mayor Vuln.)</option>
                <option value="2">Q2</option>
                <option value="3">Q3</option>
                <option value="4">Q4</option>
                <option value="5">Q5 (Menor Vuln.)</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div className="flex items-center space-x-1">
              <span className="text-slate-500 font-medium">Prioridad:</span>
              <select
                value={filterPriority}
                onChange={(e) => setFilterPriority(e.target.value)}
                className="bg-slate-50 border border-slate-300 rounded p-1 text-xs"
              >
                <option value="todos">Todas</option>
                <option value="alta">🚨 Alta</option>
                <option value="media">⚠️ Media</option>
                <option value="baja">ℹ️ Baja</option>
              </select>
            </div>
          </div>
        </div>

        {/* Incidents Table */}
        <div className="overflow-x-auto max-h-[420px] overflow-y-auto scrollbar-thin">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-semibold sticky top-0">
              <tr>
                <th className="p-2.5">ID Llamada</th>
                <th className="p-2.5">Hora (Min)</th>
                <th className="p-2.5">{datasetProfile ? 'Zona' : 'Zona / Quintil'}</th>
                <th className="p-2.5">Tipo de Emergencia</th>
                <th className="p-2.5">Prioridad</th>
                <th className="p-2.5">Estado</th>
                <th className="p-2.5">Unidad</th>
                <th className="p-2.5 text-right">Tiempo Respuesta</th>
                <th className="p-2.5 text-center">&lt; 8 min</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-400 italic">
                    No se encontraron llamadas que coincidan con los filtros aplicados.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((inc) => {
                  const priorityColor =
                    inc.prioridad === 'alta'
                      ? 'bg-rose-100 text-rose-800'
                      : inc.prioridad === 'media'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-slate-100 text-slate-700';

                  const isUnder8 = inc.tiempo_respuesta_min !== null && inc.tiempo_respuesta_min <= 8;

                  return (
                    <tr key={inc.id} className="hover:bg-slate-50">
                      <td className="p-2.5 font-mono font-bold text-slate-900">{inc.id}</td>
                      <td className="p-2.5 font-mono text-slate-600">T+{inc.tiempo_llamada}m</td>
                      <td className="p-2.5">
                        <span className="font-semibold text-slate-800">Z-{inc.zona_id}</span>
                        {!datasetProfile && <span className="text-[10px] text-rose-600 font-bold ml-1.5">Q{inc.quintil_socioeconomico}</span>}
                      </td>
                      <td className="p-2.5 text-slate-700">{inc.tipo}</td>
                      <td className="p-2.5">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${priorityColor}`}>
                          {inc.prioridad}
                        </span>
                      </td>
                      <td className="p-2.5 uppercase text-[10px] font-bold text-slate-600">{inc.estado}</td>
                      <td className="p-2.5 font-mono font-bold text-indigo-700">
                        {inc.ambulancia_id ? `AMB-${String(inc.ambulancia_id).padStart(2, '0')}` : '—'}
                      </td>
                      <td className="p-2.5 text-right font-mono font-bold text-slate-900">
                        {inc.tiempo_respuesta_min ? `${inc.tiempo_respuesta_min.toFixed(1)} min` : '—'}
                      </td>
                      <td className="p-2.5 text-center">
                        {inc.tiempo_respuesta_min ? (
                          isUnder8 ? (
                            <span className="text-emerald-600 font-bold text-xs">✓ Sí</span>
                          ) : (
                            <span className="text-rose-600 font-bold text-xs">✕ No</span>
                          )
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
