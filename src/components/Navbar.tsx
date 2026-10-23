import React from 'react';
import {
  Activity,
  BarChart3,
  Box,
  Brain,
  Database,
  FileCode,
  GitCompare,
  Layers,
  MapPin,
  MessageCircle,
  Play,
  RotateCcw,
  Sliders,
  Sparkles,
  Workflow,
  Images,
} from 'lucide-react';
import { DispatchPolicy, SimulationScenario } from '../types';

interface NavbarProps {
  historicalClock?: string;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  simMinute: number;
  isRunning: boolean;
  scenario: SimulationScenario;
  policy: DispatchPolicy;
  seed: number;
  onReset: () => void;
  onRunQuickBenchmark: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  historicalClock,
  activeTab,
  setActiveTab,
  simMinute,
  isRunning,
  scenario,
  policy,
  seed,
  onReset,
  onRunQuickBenchmark,
}) => {
  const hours = Math.floor(simMinute / 60);
  const mins = simMinute % 60;
  const timeFormatted = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;

  const scenarioLabels: Record<SimulationScenario, { name: string; color: string }> = {
    dia_normal: { name: 'Día Normal', color: 'bg-emerald-500/10 text-emerald-700 border-emerald-300' },
    evento_masivo: { name: 'Evento Masivo', color: 'bg-amber-500/10 text-amber-700 border-amber-300' },
    tormenta: { name: 'Tormenta Severa', color: 'bg-blue-500/10 text-blue-700 border-blue-300' },
    brote_respiratorio: { name: 'Brote Respiratorio', color: 'bg-purple-500/10 text-purple-700 border-purple-300' },
  };

  const navTabs = [
    { id: 'map', label: 'Mapa & Gemelo 3D', icon: Box },
    { id: 'simulation', label: historicalClock ? 'Escenarios NYC' : 'Simulador en Vivo', icon: Sliders },
    { id: 'prediction', label: 'Predicción de Demanda', icon: Brain },
    { id: 'comparison', label: historicalClock ? 'Experimentos' : 'Comparación & Equidad', icon: GitCompare },
    { id: 'stats', label: 'Pruebas Estadísticas', icon: BarChart3 },
    { id: 'crispdm', label: 'CRISP-DM', icon: Workflow },
    { id: 'article-figures', label: 'Figuras del articulo', icon: Images },
    { id: 'data', label: 'Datos & CSV', icon: Database },
    { id: 'assistant', label: 'Asistente EMS', icon: MessageCircle },
    { id: 'code', label: 'Arquitectura & Python', icon: FileCode },
  ];

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs" id="app-main-navbar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Top Branding & Status Row */}
        <div className="flex flex-wrap items-center justify-between gap-2 py-3 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-sky-500/30">
              <Activity className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-slate-900 text-lg">EMS Digital Twin</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-300">
                  Prototipo Académico
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                {historicalClock ? 'NYC EMS · Demanda historica, pronosticos y escenarios simulados' : 'Simulacion urbana y despacho predictivo'}
              </p>
            </div>
          </div>

          {/* Real-time Status Badges & Quick Actions */}
          <div className="flex items-center space-x-3">
            {/* Clock */}
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
              <span className={`w-2.5 h-2.5 rounded-full ${isRunning ? 'bg-emerald-500 animate-ping' : 'bg-slate-400'}`} />
              <span className="font-mono font-semibold text-slate-700">{historicalClock ? `${historicalClock.slice(11, 16)} NYC` : `T + ${timeFormatted} hrs`}</span>
            </div>

            {/* Scenario Pill */}
            <span
              className={`hidden md:inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-md border ${
                scenarioLabels[scenario].color
              }`}
            >
              {scenarioLabels[scenario].name}
            </span>

            {/* Policy Pill */}
            <span
              className={`text-xs font-semibold px-2.5 py-1 rounded-md border ${
                policy === 'predictivo'
                  ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}
            >
              {policy === 'predictivo' ? 'Despacho Predictivo' : 'Despacho Tradicional'}
            </span>

            {/* Benchmark Quick Action */}
            <button
              id="btn-quick-benchmark"
              onClick={onRunQuickBenchmark}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium shadow-xs transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title="Ejecutar comparación pareada automática"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Benchmark Pareado</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs Bar */}
        <nav className="flex space-x-1 overflow-x-auto py-2 scrollbar-none" aria-label="Tabs" id="nav-tabs-bar">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`tab-btn-${tab.id}`}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
};
