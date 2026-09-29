# NYC EMS - Metodologia CRISP-DM

Snapshot: `20260909T040537085584Z-56d48fe7ce9b`.

## Alcance

El proyecto usa CRISP-DM como marco de trazabilidad entre datos, modelos,
simulacion y articulo. No se usa k-fold aleatorio porque el problema es temporal;
la validacion cruzada se implementa como `rolling-origin`, entrenando siempre con
pasado y evaluando futuro.

## Evidencia en el software

| Fase CRISP-DM | Evidencia principal |
|---|---|
| Comprension del negocio | `docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md`, preguntas de investigacion y contrato de simulacion |
| Comprension de datos | `docs/NYC_EMS_PHASE3_QUALITY_REPORT.md`, cohortes y EDA por borough |
| Preparacion de datos | `docs/NYC_EMS_PHASE4_FEATURES_REPORT.md`, panel zona-hora, rezagos y particiones |
| Modelado | `docs/NYC_EMS_PHASE5_MODEL_REPORT.md`, modelos, hiperparametros y seleccion |
| Evaluacion | `reports/nyc_ems/<snapshot>/crisp_dm/`, validacion temporal, pruebas e interpretabilidad |
| Despliegue | FastAPI, React, visualizacion 2D/3D, panel CRISP-DM y asistente LangGraph |

## Artefactos generados

El paquete metodologico esta en:

`reports/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/crisp_dm/`

Incluye 6 tablas principales:

1. `crisp_dm_traceability.csv`
2. `eda_quality_summary.csv`
3. `temporal_cv_metrics.csv`
4. `hyperparameter_search.csv`
5. `model_statistical_tests.csv`: t pareada, Wilcoxon signed-rank y bootstrap percentil 95 % sobre errores absolutos pareados.
6. `interpretability_feature_importance.csv`

Tambien incluye `artifact_interpretation.csv`, que explica como interpretar cada
tabla y grafico.

Incluye 6 graficos:

1. Flujo CRISP-DM.
2. EDA de demanda por borough.
3. Particion temporal.
4. MAE por fold temporal.
5. Hiperparametros vs MAE.
6. Importancia de variables del Random Forest.

## Evidencia en el articulo

La version final 2 incorpora una subseccion:

`4.7. Integracion metodologica bajo CRISP-DM`

Tambien enlaza la metodologia con:

- `5. Resultados`
- `6. Discusion`
- `7. Conclusiones`
- `8. Disponibilidad de datos, codigo y reproducibilidad`
- `9. Declaraciones eticas, confidencialidad y uso de IA`

Archivo:

`docs/Articulo de Investigacion-final-v2.docx`

## Como regenerar

```powershell
python research\visualization\crisp_dm_methodology.py --snapshot 20260909T040537085584Z-56d48fe7ce9b
python tools\complete_article_v2_preserve.py
```

## Lectura metodologica

El software contiene EDA, preparacion, entrenamiento, seleccion de modelo,
validacion temporal, busqueda ligera de hiperparametros, pruebas estadisticas
pareadas, interpretabilidad global e integracion visual. La politica predictiva
v1 aun no demuestra mejora operacional; ese resultado se conserva como evidencia
experimental y orienta la siguiente iteracion CRISP-DM.
