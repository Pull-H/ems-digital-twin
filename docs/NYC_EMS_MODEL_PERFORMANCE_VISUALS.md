# NYC EMS - EMS-019B: visualizacion de rendimiento de modelos

Fecha de implementacion: 2026-09-22.

## Objetivo

Generar graficos y tablas exportables para el articulo a partir de los resultados
de Fase 5. Esta mini fase complementa la comparacion de modelos antes de presentar
la simulacion y los experimentos de Fase 8.

## Artefacto reproducible

Script:

```powershell
python research\visualization\model_performance.py --snapshot 20260909T040537085584Z-56d48fe7ce9b
```

El script lee:

- `research/artifacts/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase5/reports/metrics.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/retrospective_forecasts.parquet`

## Salidas

Carpeta principal:

```text
reports/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/model_performance/
```

Graficos SVG:

- `figures/global_test_metrics.svg`: barras MAE, RMSE y WAPE en prueba.
- `figures/model_metric_matrix.svg`: matriz modelo x metrica.
- `figures/borough_mae_test.svg`: MAE por borough y modelo.
- `figures/actual_vs_predicted_test.svg`: serie temporal real vs predicha para el modelo seleccionado.

Tablas CSV:

- `tables/global_model_metrics.csv`
- `tables/by_zone_model_metrics.csv`
- `tables/test_model_metric_matrix.csv`
- `tables/selected_model_test_timeseries.csv`

Reporte generado:

- `MODEL_PERFORMANCE_VISUAL_REPORT.md`

## Lectura para el articulo

La seleccion del modelo se hizo por MAE de validacion, por eso el sistema usa
`hist_gradient_boosting_v1`. En la prueba final, `random_forest_v1` obtuvo el
menor MAE y RMSE. Esto debe reportarse como dos hechos distintos:

- modelo seleccionado por protocolo: Gradient Boosting;
- mejor desempeno final observado en test: Random Forest.

## Nota metodologica

No se genera matriz de confusion porque el problema es de regresion de conteos
horarios, no clasificacion. En su lugar se genera una matriz modelo x metrica y
graficos de error por borough.
