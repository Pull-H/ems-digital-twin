import React, { useState } from 'react';
import {
  Ambulance,
  DispatchPolicy,
  DispatchWeights,
  Incident,
  SimulationScenario,
} from '../types';
import { SimEventLog } from '../services/simulationEngine';
import {
  FastForward,
  Pause,
  Play,
  RotateCcw,
  Sliders,
  Sparkles,
  StepForward,
  Truck,
  Activity,
  Filter,
} from 'lucide-react';

interface SimulationControlsProps {
  isRunning: boolean;
  onTogglePlay: () => void;
  onStep: (deltaMin: number) => void;
  onReset: () => void;
  speedMultiplier: number;
  onChangeSpeed: (speed: number) => void;
  scenario: SimulationScenario;
  onChangeScenario: (scenario: SimulationScenario) => void;
  policy: DispatchPolicy;
  onChangePolicy: (policy: DispatchPolicy) => void;
  numAmbulances: number;
  onChangeNumAmbulances: (num: number) => void;
  seed: number;
  onChangeSeed: (seed: number) => void;
  weights: DispatchWeights;
  onChangeWeights: (weights: DispatchWeights) => void;
  ambulances: Ambulance[];
  eventLogs: SimEventLog[];
  activeIncidents: Incident[];
  onSelectAmbulance: (ambulance: Ambulance | null) => void;
  selectedAmbulance: Ambulance | null;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({
  isRunning,
  onTogglePlay,
  onStep,
  onReset,
  speedMultiplier,
  onChangeSpeed,
  scenario,
  onChangeScenario,
  policy,
  onChangePolicy,
  numAmbulances,
  onChangeNumAmbulances,
  seed,
  onChangeSeed,
  weights,
  onChangeWeights,
  ambulances,
  eventLogs,
  activeIncidents,
  onSelectAmbulance,
  selectedAmbulance,
}) => {
  const [showWeightsConfig, setShowWeightsConfig] = useState(false);
  const [logFilter, setLogFilter] = useState<'todos' | 'despacho' | 'reubicacion' | 'hospital'>('todos');

  const speedOptions = [1, 2, 5, 10, 30];

  const filteredLogs = eventLogs.filter((log) => {
    if (logFilter === 'despacho') return log.tipo_evento === 'ambulancia_despachada' || log.tipo_evento === 'llegada_escena';
    if (logFilter === 'reubicacion') return log.tipo_evento === 'reubicacion_iniciada' || log.tipo_evento === 'reubicacion_completada';
    if (logFilter === 'hospital') return log.tipo_evento === 'inicio_traslado' || log.tipo_evento === 'llegada_hospital';
    return true;
  });

  const getStatusBadge = (status: Ambulance['estado']) => {
    switch (status) {
      case 'disponible':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">DISPONIBLE</span>;
      case 'en ruta':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 animate-pulse">EN RUTA</span>;
      case 'en escena':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">EN ESCENA</span>;
      case 'trasladando':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800">TRASLADANDO</span>;
      case 'en hospital':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-pink-100 text-pink-800">EN HOSPITAL</span>;
      case 'reubicándose':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-100 text-cyan-800 animate-pulse">REUBICÁNDOSE</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800">{status}</span>;
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4" id="simulation-controls-container">
      {/* Left Panel: Primary Engine Parameters & Controls */}
      <div className="lg:col-span-5 space-y-4">
        {/* Main Run Control Box */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-indigo-600" />
              <h3 className="font-bold text-sm text-slate-900">Panel de Control de Simulación</h3>
            </div>
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
              Semilla: {seed}
            </span>
          </div>

          {/* Primary Buttons: Play, Step, Reset */}
          <div className="flex items-center space-x-2">
            <button
              id="btn-toggle-play"
              onClick={onTogglePlay}
              className={`flex-1 py-2.5 px-4 rounded-lg font-bold text-sm flex items-center justify-center space-x-2 shadow-xs transition-colors ${
                isRunning
                  ? 'bg-amber-500 hover:bg-amber-600 text-white'
                  : 'bg-emerald-600 hover:bg-emerald-700 text-white'
              }`}
            >
              {isRunning ? (
                <>
                  <Pause className="w-4 h-4" />
                  <span>Pausar</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Iniciar Simulación</span>
                </>
              )}
            </button>

            <button
              id="btn-step-5m"
              onClick={() => onStep(5)}
              className="p-2.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold flex items-center space-x-1"
              title="Avanzar 5 minutos"
            >
              <StepForward className="w-4 h-4" />
              <span>+5m</span>
            </button>

            <button
              id="btn-step-15m"
              onClick={() => onStep(15)}
              className="p-2.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold flex items-center space-x-1"
              title="Avanzar 15 minutos (ejecuta reubicaciones y pronósticos)"
            >
              <FastForward className="w-4 h-4" />
              <span>+15m</span>
            </button>

            <button
              id="btn-reset-sim"
              onClick={onReset}
              className="p-2.5 rounded-lg bg-slate-100 hover:bg-rose-50 hover:text-rose-600 text-slate-700 transition-colors"
              title="Reiniciar simulación"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Speed Multiplier Buttons */}
          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-500 font-medium">Velocidad del reloj:</span>
            <div className="flex items-center space-x-1">
              {speedOptions.map((spd) => (
                <button
                  key={spd}
                  onClick={() => onChangeSpeed(spd)}
                  className={`px-2 py-1 rounded font-mono text-xs font-semibold transition-colors ${
                    speedMultiplier === spd
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>

          {/* Scenario Selector */}
          <div className="space-y-1.5 pt-2 border-t border-slate-100">
            <label className="text-xs font-semibold text-slate-700">Escenario Operativo:</label>
            <select
              value={scenario}
              onChange={(e) => onChangeScenario(e.target.value as SimulationScenario)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg p-2 text-xs font-medium text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            >
              <option value="dia_normal">☀️ Día Normal (Tráfico y demanda base habitual)</option>
              <option value="evento_masivo">🏟️ Evento Masivo (Concentración masiva en sector centro/estadio)</option>
              <option value="tormenta">⛈️ Tormenta Severa (Velocidad reducida 40%, mayor accidentalidad)</option>
              <option value="brote_respiratorio">😷 Brote Respiratorio (Pico de demanda en sectores vulnerables)</option>
            </select>
          </div>

          {/* Policy Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">Política de Despacho Activa:</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => onChangePolicy('tradicional')}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  policy === 'tradicional'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-semibold ring-1 ring-indigo-500'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <div className="text-xs font-bold">🚑 Tradicional</div>
                <div className="text-[10px] text-slate-500 mt-0.5 leading-snug">Unidad más cercana (Línea base)</div>
              </button>

              <button
                onClick={() => onChangePolicy('predictivo')}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  policy === 'predictivo'
                    ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-semibold ring-1 ring-indigo-500'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <div className="text-xs font-bold text-indigo-700">🔮 Predictivo + Equidad</div>
                <div className="text-[10px] text-slate-500 mt-0.5 leading-snug">Cobertura futura y equidad Q1-Q5</div>
              </button>
            </div>
          </div>

          {/* Fleet Size & Seed Controls */}
          <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">
                Flota: {numAmbulances} ambulancias
              </label>
              <input
                type="range"
                min={10}
                max={15}
                value={numAmbulances}
                onChange={(e) => onChangeNumAmbulances(parseInt(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>
            <div>
              <label className="text-[11px] font-semibold text-slate-600 block mb-1">Semilla PRNG:</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => onChangeSeed(parseInt(e.target.value) || 12345)}
                className="w-full bg-slate-50 border border-slate-300 rounded p-1 text-xs font-mono"
              />
            </div>
          </div>

          {/* Weights Config Collapsible */}
          {policy === 'predictivo' && (
            <div className="pt-2 border-t border-slate-100">
              <button
                onClick={() => setShowWeightsConfig(!showWeightsConfig)}
                className="w-full text-left text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center justify-between"
              >
                <span>⚙️ Ajustar Ponderaciones de Puntuación</span>
                <span>{showWeightsConfig ? '▲ Ocultar' : '▼ Expandir'}</span>
              </button>

              {showWeightsConfig && (
                <div className="mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Peso Tiempo ($w_t$):</span>
                    <span className="font-mono font-bold">{weights.peso_tiempo}</span>
                  </div>
                  <input
                    type="range"
                    min={0.1}
                    max={0.8}
                    step={0.05}
                    value={weights.peso_tiempo}
                    onChange={(e) => onChangeWeights({ ...weights, peso_tiempo: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-600"
                  />

                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Peso Demanda Futura ($w_d$):</span>
                    <span className="font-mono font-bold">{weights.peso_demanda}</span>
                  </div>
                  <input
                    type="range"
                    min={0.05}
                    max={0.5}
                    step={0.05}
                    value={weights.peso_demanda}
                    onChange={(e) => onChangeWeights({ ...weights, peso_demanda: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-600"
                  />

                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Peso Cobertura Origen ($w_c$):</span>
                    <span className="font-mono font-bold">{weights.peso_cobertura}</span>
                  </div>
                  <input
                    type="range"
                    min={0.05}
                    max={0.4}
                    step={0.05}
                    value={weights.peso_cobertura}
                    onChange={(e) => onChangeWeights({ ...weights, peso_cobertura: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-600"
                  />

                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Peso Equidad Quintiles ($w_e$):</span>
                    <span className="font-mono font-bold">{weights.peso_equidad}</span>
                  </div>
                  <input
                    type="range"
                    min={0.05}
                    max={0.4}
                    step={0.05}
                    value={weights.peso_equidad}
                    onChange={(e) => onChangeWeights({ ...weights, peso_equidad: parseFloat(e.target.value) })}
                    className="w-full accent-indigo-600"
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel: Live Ambulance Fleet Matrix & Real-time Event Feed */}
      <div className="lg:col-span-7 space-y-4">
        {/* Fleet Matrix Table */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
            <div className="flex items-center space-x-2">
              <Truck className="w-4 h-4 text-sky-600" />
              <h3 className="font-bold text-sm text-slate-900">Estado de Flota de Ambulancias</h3>
            </div>
            <span className="text-xs text-slate-500 font-medium">
              {ambulances.filter((a) => a.estado === 'disponible').length} de {ambulances.length} disponibles
            </span>
          </div>

          <div className="overflow-x-auto max-h-[210px] overflow-y-auto scrollbar-thin">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold sticky top-0">
                <tr>
                  <th className="p-2">Unidad</th>
                  <th className="p-2">Estado</th>
                  <th className="p-2">Base / Zona</th>
                  <th className="p-2">Velocidad</th>
                  <th className="p-2">Llamada Asignada</th>
                  <th className="p-2 text-right">Atenciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ambulances.map((amb) => {
                  const isSelected = selectedAmbulance?.id === amb.id;
                  return (
                    <tr
                      key={amb.id}
                      onClick={() => onSelectAmbulance(isSelected ? null : amb)}
                      className={`hover:bg-slate-50 cursor-pointer transition-colors ${
                        isSelected ? 'bg-indigo-50/80 font-semibold' : ''
                      }`}
                    >
                      <td className="p-2 font-mono font-bold text-slate-900">{amb.codigo}</td>
                      <td className="p-2">{getStatusBadge(amb.estado)}</td>
                      <td className="p-2 text-slate-600">Base {amb.base_id} (Z-{amb.zona_actual_id})</td>
                      <td className="p-2 font-mono text-slate-700">{amb.velocidad_kmh} km/h</td>
                      <td className="p-2 font-mono text-indigo-700">
                        {amb.incidente_asignado_id || <span className="text-slate-400 font-sans">—</span>}
                      </td>
                      <td className="p-2 text-right font-mono font-semibold text-slate-800">{amb.incidentes_atendidos}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Real-time Event Feed Stream */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-2">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-emerald-600" />
              <h3 className="font-bold text-sm text-slate-900">Registro de Eventos en Tiempo Real</h3>
            </div>
            <div className="flex items-center space-x-1 text-xs">
              <span className="text-slate-400 font-medium mr-1">Filtro:</span>
              {(['todos', 'despacho', 'reubicacion', 'hospital'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setLogFilter(f)}
                  className={`px-2 py-0.5 rounded text-[11px] font-medium capitalize ${
                    logFilter === f ? 'bg-slate-900 text-white font-bold' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="h-[210px] overflow-y-auto space-y-1.5 pr-1 scrollbar-thin text-xs">
            {filteredLogs.length === 0 ? (
              <div className="text-center text-slate-400 py-12 italic">
                Inicie o avance la simulación para registrar eventos operativos...
              </div>
            ) : (
              filteredLogs.map((log) => {
                const hours = Math.floor(log.sim_time_min / 60);
                const mins = log.sim_time_min % 60;
                const timeStr = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;

                let badgeColor = 'bg-slate-100 text-slate-700';
                if (log.tipo_evento === 'ambulancia_despachada') badgeColor = 'bg-sky-100 text-sky-800';
                if (log.tipo_evento === 'reubicacion_iniciada') badgeColor = 'bg-cyan-100 text-cyan-800 font-bold';
                if (log.tipo_evento === 'llegada_escena') badgeColor = 'bg-amber-100 text-amber-800';
                if (log.tipo_evento === 'inicio_traslado') badgeColor = 'bg-purple-100 text-purple-800';
                if (log.tipo_evento === 'ambulancia_liberada') badgeColor = 'bg-emerald-100 text-emerald-800';

                return (
                  <div
                    key={log.id}
                    className="p-2 rounded-lg bg-slate-50 border border-slate-100 hover:border-slate-200 transition-colors flex items-start space-x-2"
                  >
                    <span className="font-mono text-[10px] text-slate-400 shrink-0 mt-0.5">{timeStr}</span>
                    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded shrink-0 ${badgeColor}`}>
                      {log.tipo_evento.replace('_', ' ')}
                    </span>
                    <p className="text-slate-800 leading-snug">{log.descripcion}</p>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
