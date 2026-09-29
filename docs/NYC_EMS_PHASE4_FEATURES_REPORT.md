# NYC EMS - Fase 4: geografia, variables y particion temporal

Fecha de ejecucion: 2026-09-17 UTC.

Snapshot procesado: `20260909T040537085584Z-56d48fe7ce9b`.

## Resultado

| Indicador | Valor |
|---|---:|
| Unidad de pronostico | borough |
| Zonas observadas | 5 |
| Horas por zona | 2184 |
| Filas del panel zona-hora | 10920 |
| Filas listas para modelo | 10080 |
| Eventos historicos para simulacion | 405998 |

## Particiones temporales

| Particion | Ventana | Filas | Filas listas para modelo |
|---|---|---:|---:|
| Entrenamiento | 2026-04-01 a 2026-05-16 | 5400 | 4560 |
| Validacion | 2026-05-16 a 2026-06-01 | 1920 | 1920 |
| Prueba | 2026-06-01 a 2026-07-01 | 3600 | 3600 |

Las primeras 168 horas por zona se conservan, pero quedan marcadas como `feature_ready=false` por calentamiento de rezagos semanales.

## Variables generadas

- `hour`, `day_of_week`, `day_of_month`, `month`, `is_weekend`.
- Rezagos: `lag_1h`, `lag_24h`, `lag_168h`.
- Ventanas moviles: `rolling_mean_24h`, `rolling_sum_24h`, `rolling_mean_168h`, `rolling_sum_168h`.
- Etiquetas: `target_demand_count`, `target_start`, `target_end`.
- Control metodologico: `split`, `feature_ready`, `label_available`.

Todas las variables de rezago y ventanas moviles usan solo demanda observada antes de `target_start`.

## Artefactos generados

- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/hourly_demand_panel.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/model_ready_hourly_demand_panel.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/feature_dictionary.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/temporal_partitions.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/geography_summary.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/historical_incident_events.parquet`

## Conteos por zona

| Borough | Demanda | Respuesta | Horas del panel |
|---|---:|---:|---:|
| BRONX | 96641 | 82590 | 2184 |
| BROOKLYN | 112002 | 105444 | 2184 |
| MANHATTAN | 97207 | 84714 | 2184 |
| QUEENS | 82878 | 76294 | 2184 |
| RICHMOND / STATEN ISLAND | 17270 | 16536 | 2184 |

## Reproducibilidad

```powershell
python research\pipeline\nyc_ems.py phase4 --snapshot 20260909T040537085584Z-56d48fe7ce9b
```
