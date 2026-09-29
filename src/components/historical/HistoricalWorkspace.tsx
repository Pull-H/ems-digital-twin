import { useEffect, useState } from 'react';
import { Box, Map, Columns2, Play, Pause, RotateCcw, StepForward, Download, LoaderCircle } from 'lucide-react';
import type { CreateSimulationRequest, HistoricalDatasetProfile, SimulationState } from '../../types';
import { HistoricalScene } from './HistoricalScene';
import { HistoricalMap } from './HistoricalMap';
import { BoroughGeometry, statusColors, zoneColors } from './geography';

interface Props {
  state: SimulationState; profile: HistoricalDatasetProfile; running: boolean; busy: boolean;
  speed: number; onSpeed: (speed: number) => void; onToggle: () => void;
  onStep: (minutes: number) => void; onCreate: (options: Partial<CreateSimulationRequest>) => Promise<void>;
}

export function HistoricalWorkspace({ state, profile, running, busy, speed, onSpeed, onToggle, onStep, onCreate }: Props) {
  const info = state.simulation!;
  const [geography, setGeography] = useState<BoroughGeometry | null>(null);
  const [geoError, setGeoError] = useState(false);
  const [view, setView] = useState<'3d' | '2d' | 'split'>('3d');
  const [selectedZone, setSelectedZone] = useState<number | null>(null);
  const [source, setSource] = useState(info.demand_source);
  const [fleet, setFleet] = useState(state.ambulances.length);
  const [policy, setPolicy] = useState(state.policy);
  const [seed, setSeed] = useState(state.seed);
  const [model, setModel] = useState(state.model_id!);
  const [start, setStart] = useState(info.clock.slice(0, 16));
  const [duration, setDuration] = useState(state.total_duration_min - state.start_minute!);
  useEffect(() => {
    const controller = new AbortController();
    fetch('/data/nyc-boroughs.geojson', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error('Geografia no disponible'); return r.json();
    }).then(setGeography).catch(e => { if (e.name !== 'AbortError') setGeoError(true); });
    return () => controller.abort();
  }, []);
  const finished = info.status === 'finished';
  const elapsed = state.sim_minute - state.start_minute!;
  const pending = info.zone_summary.reduce((n, z) => n + z.pending, 0);
  const active = info.zone_summary.reduce((n, z) => n + z.active, 0);
  const inputStyle = 'w-full rounded border border-slate-300 bg-white px-2 py-2 text-xs text-slate-900 disabled:opacity-50';
  const exportRun = () => {
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), dataset: profile.id, state }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = `nyc-${info.demand_source}-${state.seed}-${Math.floor(elapsed)}min.json`; link.click(); URL.revokeObjectURL(url);
  };
  return <section className="space-y-4 min-w-0" data-testid="historical-workspace">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 pb-3">
      <div><h1 className="text-xl font-semibold">NYC EMS · Escenario de simulacion</h1>
        <p className="text-xs text-slate-600 mt-1">{info.demand_source === 'historical' ? 'Llegadas historicas observadas' : 'Llegadas sinteticas desde pronosticos'} · Atencion y recursos simulados</p></div>
      <div className="text-right text-xs"><p className="font-mono font-semibold" data-testid="simulation-clock">{info.clock.replace('T', ' ').slice(0, 19)}</p>
        <p className="text-slate-500">Hora de Nueva York · {finished ? 'Finalizada' : running ? 'En ejecucion' : 'Pausada'}</p></div>
    </div>
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-x-4 gap-y-3 border-b border-slate-200 pb-4">
      {[
        ['Llamadas recibidas', state.metrics.incidentes_totales.toLocaleString(), `${info.completed} servicios completados`],
        ['En espera / activas', `${pending} / ${active}`, `${info.unfinished} sin completar`],
        ['Flota disponible', `${state.ambulances.filter(a => a.estado === 'disponible').length} / ${state.ambulances.length}`, 'Recursos del escenario'],
        ['Respuesta simulada', state.metrics.incidentes_atendidos ? `${state.metrics.tiempo_promedio_respuesta.toFixed(1)} min` : 'Sin llegadas', `${state.metrics.incidentes_atendidos} llegadas a escena`],
        ['P90 simulado', state.metrics.incidentes_atendidos ? `${state.metrics.p90_respuesta.toFixed(1)} min` : 'Sin llegadas', `${Math.round(state.metrics.utilizacion_ambulancias * 100)}% utilizacion temporal`],
        ['Referencia observada', info.observed_response_mean === null ? 'No disponible' : `${info.observed_response_mean.toFixed(1)} min`, `${info.observed_response_count} respuestas conocidas al corte`],
      ].map(([name, value, detail]) => <div key={name} className="min-w-0"><p className="text-xs text-slate-500">{name}</p><p className="text-xl font-semibold my-1 break-words">{value}</p><p className="text-[11px] text-slate-500">{detail}</p></div>)}
    </div>
    <form className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3 items-end" onSubmit={e => {
      e.preventDefault();
      const minute = Math.round((Date.parse(start + ':00Z') - Date.parse(profile.window.start_inclusive + 'Z')) / 60000);
      void onCreate({ demand_source: source, num_ambulances: fleet, policy, seed, model_id: model, start_minute: minute, duration_min: duration });
    }}>
      <label className="text-xs">Entrada de demanda<select aria-label="Entrada de demanda" className={inputStyle} value={source} onChange={e => setSource(e.target.value as typeof source)}><option value="historical">Historica</option><option value="forecast">Pronosticada</option></select></label>
      <label className="text-xs">Politica<select aria-label="Politica NYC" className={inputStyle} value={policy} onChange={e => setPolicy(e.target.value as typeof policy)}><option value="tradicional">Tradicional</option><option value="predictivo">Predictiva</option></select></label>
      <label className="text-xs">Flota asumida<input aria-label="Flota asumida" className={inputStyle} type="number" min="1" max="1500" required value={fleet} onChange={e => setFleet(Number(e.target.value))} /></label>
      <label className="text-xs">Semilla<input aria-label="Semilla NYC" className={inputStyle} type="number" min="0" max="2147483647" required value={seed} onChange={e => setSeed(Number(e.target.value))} /></label>
      <label className="text-xs col-span-2">Inicio (Nueva York)<input className={inputStyle} aria-label="Inicio NYC" type="datetime-local" required min={info.training_end.slice(0, 16)} max={profile.window.end_exclusive.slice(0, 16)} value={start} onChange={e => setStart(e.target.value)} /></label>
      <label className="text-xs">Duracion<select aria-label="Duracion NYC" className={inputStyle} value={duration} onChange={e => setDuration(Number(e.target.value))}><option value="60">1 hora</option><option value="360">6 horas</option><option value="720">12 horas</option><option value="1440">24 horas</option></select></label>
      <button type="submit" disabled={busy} className="h-9 rounded bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-50"><RotateCcw size={15} />Nueva corrida</button>
      <label className="text-xs col-span-2 md:col-span-3">Modelo<select aria-label="Modelo NYC" className={inputStyle} value={model} onChange={e => setModel(e.target.value)}>{profile.available_models.map(m => <option key={m} value={m}>{m}</option>)}</select></label>
      <p className="text-xs text-slate-500 col-span-2 md:col-span-4 xl:col-span-5 pb-2">Corrida activa: {state.policy} · {state.model_id} · semilla {state.seed}</p>
    </form>
    <div className="flex flex-wrap items-center justify-between gap-3 border-y border-slate-200 py-2">
      <div className="flex gap-1" role="group" aria-label="Vista territorial">{([['3d', Box, '3D'], ['2d', Map, '2D'], ['split', Columns2, 'Dividida']] as const).map(([id, Icon, title]) => <button key={id} onClick={() => setView(id)} aria-pressed={view === id} className={`flex items-center gap-2 rounded px-3 py-2 text-xs ${view === id ? 'bg-slate-800 text-white' : 'bg-white text-slate-700'}`}><Icon size={15} />{title}</button>)}</div>
      <div className="flex flex-wrap items-center gap-2">
        <button aria-label={running ? 'Pausar' : 'Reproducir'} title={running ? 'Pausar' : 'Reproducir'} onClick={onToggle} disabled={busy || finished} className="p-2 rounded bg-teal-700 text-white disabled:opacity-40">{running ? <Pause size={17} /> : <Play size={17} />}</button>
        <button title="Avanzar 5 minutos" aria-label="Avanzar 5 minutos" onClick={() => onStep(5)} disabled={busy || running || finished} className="p-2 rounded border border-slate-300 disabled:opacity-40"><StepForward size={17} /></button>
        <select aria-label="Velocidad" className="text-xs border border-slate-300 rounded p-2" value={speed} onChange={e => onSpeed(Number(e.target.value))}><option value="1">1 min/s</option><option value="5">5 min/s</option><option value="15">15 min/s</option><option value="60">60 min/s</option></select>
        <span className="text-xs font-mono">{Math.floor(elapsed)} / {state.total_duration_min - state.start_minute!} min</span>
        <button title="Exportar estado de corrida" aria-label="Exportar estado de corrida" onClick={exportRun} className="p-2 rounded border border-slate-300"><Download size={17} /></button>
      </div>
    </div>
    <progress className="w-full h-1 accent-teal-600 block" value={elapsed} max={state.total_duration_min - state.start_minute!} aria-label="Progreso de corrida" />
    {geography ? <div className={view === 'split' ? 'grid grid-cols-1 lg:grid-cols-2 gap-2' : ''}>
      {view !== '2d' && <HistoricalScene state={state} geography={geography} onSelect={setSelectedZone} />}
      {view !== '3d' && <HistoricalMap state={state} geography={geography} onSelect={setSelectedZone} />}
    </div> : <div className="h-64 grid place-content-center text-sm text-slate-500">{geoError ? 'No se pudieron cargar los limites de NYC.' : <span className="flex gap-2"><LoaderCircle className="animate-spin" />Cargando territorio NYC</span>}</div>}
    <div className="flex flex-wrap gap-x-4 gap-y-2 text-[11px] text-slate-600">{Object.entries(statusColors).filter(([s]) => s !== 'asignada').map(([s, color]) => <span key={s} className="flex items-center gap-1"><span style={{ background: color }} className="inline-block w-2 h-2 rounded-sm" />{s}</span>)}<span>Barras: pronostico de la hora en curso · Libres agrupadas por borough</span></div>
    <div className="overflow-x-auto"><table className="w-full text-xs text-left"><caption className="text-left font-semibold text-sm py-3">Demanda y atencion por borough</caption><thead className="text-slate-500 border-b border-slate-200"><tr>{['Borough', 'Recibidas', 'En espera', 'Activas', 'Completadas', 'Disponibles', 'Pronostico / hora'].map(h => <th key={h} className="p-2 whitespace-nowrap font-medium">{h}</th>)}</tr></thead><tbody>{state.zones.map(z => {
      const summary = info.zone_summary.find(s => s.zone_id === z.id)!;
      const prediction = state.predictions.find(p => p.zona_id === z.id);
      return <tr key={z.id} onClick={() => setSelectedZone(z.id)} className={`border-b border-slate-100 cursor-pointer ${selectedZone === z.id ? 'bg-teal-50' : 'hover:bg-white'}`}><th scope="row" className="p-2 font-medium whitespace-nowrap"><span className="inline-block w-2 h-2 mr-2 rounded-sm" style={{ background: zoneColors[z.id] }} />{z.nombre}</th>{[summary.arrived, summary.pending, summary.active, summary.completed, summary.available, prediction?.demanda_predicha_ml.toFixed(1) ?? 'Sin pronostico'].map((v, i) => <td key={i} className="p-2 tabular-nums">{v}</td>)}</tr>;
    })}</tbody></table></div>
    <details className="border-t border-slate-200 pt-3 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">Procedencia y supuestos de la corrida</summary><p className="break-all mt-2">Snapshot: {profile.id} · {profile.expected_rows.toLocaleString()} registros · {profile.window.start_inclusive.slice(0, 10)} a {profile.window.end_exclusive.slice(0, 10)} (fin exclusivo).</p><ul className="list-disc pl-5 mt-2 space-y-1">{info.assumptions.map(a => <li key={a}>{a}</li>)}<li>Preparacion de despacho: 0.5 min. Entre zonas: distancia entre centroides a 38 km/h, sin red vial.</li><li>Politica predictiva: tiempo estimado + 2 × demanda horaria de la zona de origen / unidades libres en esa zona.</li><li>{info.excluded_unknown_zone} llegadas excluidas por zona desconocida. Se exportan hasta 1000 incidentes; los indicadores incluyen todos los recibidos.</li><li>Referencia observada y respuesta simulada pueden tener distintos denominadores; no representan una mejora causal.</li></ul></details>
    <details className="border-t border-slate-200 pt-3 text-xs"><summary className="cursor-pointer font-semibold">Eventos recientes ({state.event_logs.length})</summary><div className="max-h-52 overflow-auto mt-2">{state.event_logs.slice().reverse().map(e => <p key={e.id} className="font-mono border-b border-slate-100 py-1 break-all">+{(e.sim_time_min - state.start_minute!).toFixed(1)} min · {e.descripcion}</p>)}</div></details>
  </section>;
}
