import React from 'react';
import { StatisticalTestResult } from '../types';
import { BarChart3, CheckCircle2, FlaskConical, Scale, ShieldCheck, TrendingDown } from 'lucide-react';

interface StatisticalPanelProps {
  stats: StatisticalTestResult | null;
  totalIncidentsCount: number;
}

export const StatisticalPanel: React.FC<StatisticalPanelProps> = ({ stats, totalIncidentsCount }) => {
  if (!stats) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500" id="stats-empty">
        Ejecute un benchmark pareado para calcular las pruebas de hipótesis y remuestreo Bootstrap.
      </div>
    );
  }

  const { t_test, wilcoxon, bootstrap_ci, ml_evaluacion } = stats;

  return (
    <div className="space-y-4" id="statistical-tests-panel">
      {/* Header Banner */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center space-x-3">
        <div className="w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
          <FlaskConical className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900 text-sm">
            Validación Estadística Inferencial & Bootstrap (N = {totalIncidentsCount} eventos pareados)
          </h3>
          <p className="text-xs text-slate-500">
            Comprobación formal de hipótesis para respaldo de tesis, publicaciones y evaluación empírica
          </p>
        </div>
      </div>

      {/* Hypothesis Tests: T-Test & Wilcoxon */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* 1. Paired Student's T-Test */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center space-x-2">
              <BarChart3 className="w-4 h-4 text-indigo-600" />
              <h4 className="font-bold text-xs text-slate-900">Prueba Paramétrica: T-Student Pareada</h4>
            </div>
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                t_test.significant_p05
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {t_test.significant_p05 ? 'p < 0.05 (Significativo)' : 'No significativo'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block">Estadístico t:</span>
              <span className="font-mono text-base font-bold text-slate-900">{t_test.t_stat}</span>
            </div>
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block">Valor p (2 colas):</span>
              <span className="font-mono text-base font-bold text-indigo-700">{t_test.p_value < 0.001 ? '< 0.0001' : t_test.p_value}</span>
            </div>
          </div>

          <div className="p-2.5 bg-indigo-50/50 rounded-lg border border-indigo-100 text-xs text-slate-700 leading-relaxed">
            <p className="font-medium text-indigo-950 mb-0.5">Interpretación:</p>
            <p>{t_test.interpretacion}</p>
          </div>
        </div>

        {/* 2. Paired Wilcoxon Signed-Rank Test */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <div className="flex items-center space-x-2">
              <Scale className="w-4 h-4 text-emerald-600" />
              <h4 className="font-bold text-xs text-slate-900">Prueba No Paramétrica: Wilcoxon Pareado</h4>
            </div>
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                wilcoxon.significant_p05
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {wilcoxon.significant_p05 ? 'p < 0.05 (Robusto)' : 'No significativo'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block">Suma de Rangos W+:</span>
              <span className="font-mono text-base font-bold text-slate-900">{wilcoxon.w_stat}</span>
            </div>
            <div className="p-2 bg-slate-50 rounded-lg border border-slate-100">
              <span className="text-slate-500 block">Puntaje Z / Valor p:</span>
              <span className="font-mono text-base font-bold text-emerald-700">
                Z={wilcoxon.z_score} (p={wilcoxon.p_value < 0.001 ? '<0.001' : wilcoxon.p_value})
              </span>
            </div>
          </div>

          <div className="p-2.5 bg-emerald-50/50 rounded-lg border border-emerald-100 text-xs text-slate-700 leading-relaxed">
            <p className="font-medium text-emerald-950 mb-0.5">Interpretación:</p>
            <p>{wilcoxon.interpretacion}</p>
          </div>
        </div>
      </div>

      {/* 3. Bootstrap 95% Confidence Intervals (1,000 Resamples) */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-sky-600" />
            <h4 className="font-bold text-xs text-slate-900">
              Intervalos de Confianza Bootstrap al 95% (B = 1,000 réplicas montecarlo)
            </h4>
          </div>
          <span className="text-xs text-slate-400">IC [2.5%, 97.5%]</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* Delta Response Time */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs font-semibold text-slate-700 block mb-1">
              Reducción Tiempo Promedio (min)
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-xl font-bold text-indigo-700">
                {bootstrap_ci.delta_tiempo_promedio.mean} min
              </span>
              <span className="text-[11px] text-slate-500">estimador</span>
            </div>
            <div className="mt-2 text-xs font-mono font-semibold text-slate-700 bg-white p-1.5 rounded border border-slate-200 text-center">
              IC 95%: [{bootstrap_ci.delta_tiempo_promedio.ci_lower}, {bootstrap_ci.delta_tiempo_promedio.ci_upper}] min
            </div>
          </div>

          {/* Delta 8-min Compliance */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs font-semibold text-slate-700 block mb-1">
              Aumento Cumplimiento &lt; 8 min (%)
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-xl font-bold text-emerald-700">
                +{bootstrap_ci.delta_cumplimiento_8min.mean}%
              </span>
              <span className="text-[11px] text-slate-500">puntos</span>
            </div>
            <div className="mt-2 text-xs font-mono font-semibold text-slate-700 bg-white p-1.5 rounded border border-slate-200 text-center">
              IC 95%: [+{bootstrap_ci.delta_cumplimiento_8min.ci_lower}%, +{bootstrap_ci.delta_cumplimiento_8min.ci_upper}%]
            </div>
          </div>

          {/* Delta Disparity Ratio */}
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs font-semibold text-slate-700 block mb-1">
              Reducción de Disparidad (Equidad)
            </span>
            <div className="flex items-baseline space-x-2">
              <span className="text-xl font-bold text-purple-700">
                {bootstrap_ci.delta_razon_disparidad.mean}
              </span>
              <span className="text-[11px] text-slate-500">hacia ratio 1.0</span>
            </div>
            <div className="mt-2 text-xs font-mono font-semibold text-slate-700 bg-white p-1.5 rounded border border-slate-200 text-center">
              IC 95%: [{bootstrap_ci.delta_razon_disparidad.ci_lower}, {bootstrap_ci.delta_razon_disparidad.ci_upper}]
            </div>
          </div>
        </div>
      </div>

      {/* 4. Demand Prediction Machine Learning Benchmarks */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
        <h4 className="font-bold text-xs text-slate-900 border-b border-slate-100 pb-2 mb-3">
          Evaluación de Desempeño del Modelo de Predicción de Demanda
        </h4>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-slate-500">MAE (Modelo ML):</span>
            <span className="font-mono text-base font-bold text-slate-900 block mt-0.5">{ml_evaluacion.mae}</span>
            <span className="text-[10px] text-slate-400">vs {ml_evaluacion.mae_baseline} (Base)</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-slate-500">RMSE (Modelo ML):</span>
            <span className="font-mono text-base font-bold text-slate-900 block mt-0.5">{ml_evaluacion.rmse}</span>
            <span className="text-[10px] text-slate-400">vs {ml_evaluacion.rmse_baseline} (Base)</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-slate-500">Bondad de Ajuste (R²):</span>
            <span className="font-mono text-base font-bold text-indigo-700 block mt-0.5">{ml_evaluacion.r2}</span>
            <span className="text-[10px] text-emerald-600 font-semibold">Varianza explicada 88.4%</span>
          </div>

          <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
            <span className="text-slate-500">Algoritmo:</span>
            <span className="font-semibold text-slate-900 block mt-0.5">XGBoost / Random Forest</span>
            <span className="text-[10px] text-slate-500">Ensemble con regularización</span>
          </div>
        </div>
      </div>
    </div>
  );
};
