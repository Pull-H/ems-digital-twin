# NYC EMS - Fase 5: baselines y modelos predictivos

Fecha de ejecucion: 2026-09-17 UTC.

Snapshot procesado: `20260909T040537085584Z-56d48fe7ce9b`.

## Objetivo

Comparar tres enfoques predictivos para estimar la demanda horaria de incidentes EMS por borough, usando el panel zona-hora generado en la Fase 4. La variable objetivo es `target_demand_count` con horizonte de 60 minutos.

## Modelos comparados

| Modelo | Identificador | Descripcion |
|---|---|---|
| Baseline temporal | `baseline_temporal_v1` | Promedio historico por zona, dia de semana y hora, con respaldos por zona-hora, zona y media global. |
| Random Forest | `random_forest_v1` | Ensamble de arboles para regresion tabular con rezagos, calendario y zona codificada. |
| Gradient Boosting | `hist_gradient_boosting_v1` | Modelo de boosting para relaciones no lineales en datos tabulares. |

## Variables usadas

Los modelos usan `zone_id`, `hour`, `day_of_week`, `day_of_month`, `month`, `is_weekend`, `lag_1h`, `lag_24h`, `lag_168h`, `rolling_mean_24h`, `rolling_sum_24h`, `rolling_mean_168h` y `rolling_sum_168h`.

## Resultados globales

La seleccion se hizo con MAE en validacion. Bajo ese criterio, el modelo seleccionado es `hist_gradient_boosting_v1`.

| Modelo | Split | Filas | MAE | RMSE | WAPE | Sesgo |
|---|---|---:|---:|---:|---:|---:|
| Baseline temporal | Validacion | 1920 | 6.037 | 8.073 | 0.162 | -1.280 |
| Gradient Boosting | Validacion | 1920 | 5.674 | 7.589 | 0.152 | -0.847 |
| Random Forest | Validacion | 1920 | 5.681 | 7.543 | 0.152 | -0.251 |
| Baseline temporal | Prueba | 3600 | 6.035 | 8.349 | 0.157 | -1.942 |
| Gradient Boosting | Prueba | 3600 | 5.638 | 7.725 | 0.147 | -0.864 |
| Random Forest | Prueba | 3600 | 5.557 | 7.501 | 0.145 | -0.319 |

En prueba final, `random_forest_v1` obtiene el menor MAE y RMSE, mientras que `hist_gradient_boosting_v1` fue el mejor segun el criterio predefinido de validacion. Para el articulo conviene reportar ambos hechos: seleccion por validacion y desempeno final en test.

## Artefactos generados

- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/models/baseline_temporal_v1.joblib`
- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/models/random_forest_v1.joblib`
- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/models/hist_gradient_boosting_v1.joblib`
- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/predictions/retrospective_forecasts.parquet`
- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/reports/metrics.json`
- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/reports/model_card.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/retrospective_forecasts.parquet`

La copia en `data/.../processed/retrospective_forecasts.parquet` queda preparada para que FastAPI la consuma en fases posteriores.

## Reproducibilidad

```powershell
python -m research.pipeline.nyc_ems phase5 --snapshot 20260909T040537085584Z-56d48fe7ce9b
```

