import React from 'react';
import { Ambulance, Hospital, Incident, SimulationMetrics } from '../types';
import { Clock, CheckCircle2, AlertTriangle, Scale, Building2, Truck } from 'lucide-react';

interface LiveKPIHeaderProps {
  metrics: SimulationMetrics;
  ambulances: Ambulance[];
  hospitals: Hospital[];
  incidents: Incident[];
}

export const LiveKPIHeader: React.FC<LiveKPIHeaderProps> = ({
  metrics,
  ambulances,
  hospitals,
  incidents,
}) => {
  const availableCount = ambulances.filter((a) => a.estado === 'disponible').length;
  const activeIncidents = incidents.filter((i) => i.estado === 'en_atencion' || i.estado === 'despachado' || i.estado === 'trasladando').length;
  const pendingIncidents = incidents.filter((i) => i.estado === 'pendiente').length;

  // Find most crowded hospital
  const sortedHospitals = [...hospitals].sort((a, b) => (b.ocupacion / b.capacidad) - (a.ocupacion / a.capacidad));
  const mostCrowdedHospital = sortedHospitals[0] || hospitals[0];
  const maxOccupancyPct = mostCrowdedHospital
    ? Math.round((mostCrowdedHospital.ocupacion / mostCrowdedHospital.capacidad) * 100)
    : 0;

  // Disparity ratio interpretation
  const disparityRatio = metrics.razon_disparidad || 1.0;
  const isHighDisparity = disparityRatio > 1.35;

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4" id="live-kpi-cards-grid">
      {/* 1. Ambulancias Disponibles */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-ambulances">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium">Ambulancias</span>
          <Truck className="w-4 h-4 text-sky-600" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-bold text-slate-900">{availableCount}</span>
          <span className="text-xs text-slate-500">/ {ambulances.length} disp.</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Utilización:</span>
          <span className="font-semibold text-slate-700">{Math.round(metrics.utilizacion_ambulancias * 100)}%</span>
        </div>
      </div>

      {/* 2. Incidentes Activos */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-incidents">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium">Llamadas Activas</span>
          <AlertTriangle className="w-4 h-4 text-amber-500" />
        </div>
        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-bold text-slate-900">{activeIncidents}</span>
          <span className="text-xs text-slate-500">en curso</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Cola pendientes:</span>
          <span className={`font-semibold ${pendingIncidents > 0 ? 'text-rose-600' : 'text-slate-700'}`}>
            {pendingIncidents}
          </span>
        </div>
      </div>

      {/* 3. Tiempo Promedio de Respuesta */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-response-time">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium">Tiempo Respuesta</span>
          <Clock className="w-4 h-4 text-indigo-600" />
        </div>
        <div className="flex items-baseline space-x-1.5">
          <span className="text-2xl font-bold text-slate-900">{metrics.tiempo_promedio_respuesta.toFixed(1)}</span>
          <span className="text-xs font-medium text-slate-500">min prom.</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Percentil 90:</span>
          <span className="font-semibold text-slate-700">{metrics.p90_respuesta.toFixed(1)} min</span>
        </div>
      </div>

      {/* 4. Atención < 8 minutos */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-compliance-8min">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium">Meta &lt; 8 min</span>
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
        </div>
        <div className="flex items-baseline space-x-1.5">
          <span className="text-2xl font-bold text-slate-900">{metrics.porcentaje_menor_8min.toFixed(1)}%</span>
          <span className="text-xs text-slate-500">alcanzado</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Atendidos:</span>
          <span className="font-semibold text-slate-700">{metrics.incidentes_atendidos}</span>
        </div>
      </div>

      {/* 5. Razón de Disparidad */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-disparity">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium">Razón Disparidad</span>
          <Scale className={`w-4 h-4 ${isHighDisparity ? 'text-rose-500' : 'text-emerald-500'}`} />
        </div>
        <div className="flex items-baseline space-x-1.5">
          <span className={`text-2xl font-bold ${isHighDisparity ? 'text-rose-700' : 'text-slate-900'}`}>
            {disparityRatio.toFixed(2)}
          </span>
          <span className="text-xs text-slate-500">(1.0 = equidad)</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Delta Q1 vs Q5:</span>
          <span className="font-semibold text-slate-700">{metrics.diferencia_max_min_quintiles.toFixed(1)} min</span>
        </div>
      </div>

      {/* 6. Hospital con Mayor Ocupación */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between" id="kpi-hospital-occupancy">
        <div className="flex items-center justify-between text-slate-500 mb-1">
          <span className="text-xs font-medium truncate">Ocupación Hosp.</span>
          <Building2 className="w-4 h-4 text-violet-600" />
        </div>
        <div className="flex items-baseline space-x-1.5">
          <span className={`text-2xl font-bold ${maxOccupancyPct > 80 ? 'text-amber-600' : 'text-slate-900'}`}>
            {maxOccupancyPct}%
          </span>
          <span className="text-xs text-slate-500">máx</span>
        </div>
        <div className="mt-1 text-[11px] text-slate-500 truncate" title={mostCrowdedHospital?.nombre}>
          <span className="font-medium text-slate-700">{mostCrowdedHospital?.codigo || 'N/A'}</span>
          <span> ({mostCrowdedHospital?.ocupacion}/{mostCrowdedHospital?.capacidad} camas)</span>
        </div>
      </div>
    </div>
  );
};
