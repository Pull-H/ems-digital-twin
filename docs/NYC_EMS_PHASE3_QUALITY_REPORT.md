# NYC EMS - Fase 3: perfilado, limpieza y cohortes

Fecha de ejecucion: 2026-09-17 UTC.

Snapshot procesado: `20260909T040537085584Z-56d48fe7ce9b`.

## Resultado

| Indicador | Valor |
|---|---:|
| Filas crudas verificadas | 405998 |
| Cohorte de demanda | 405998 |
| Cohorte de respuesta | 365578 |
| Cohorte de transporte | 223333 |
| Eventos especiales | 57 |
| Filas en cuarentena | 11 |

## Artefactos generados

- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/interim/quality_report.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/interim/inclusion_exclusion_report.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/interim/quarantine.csv`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/incidents_clean.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/demand_cohort.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/response_cohort.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/transport_cohort.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/processed/cohort_summary.json`

## Hallazgos principales

- No se encontraron IDs faltantes, fechas de incidente invalidas, IDs duplicados ni duplicados exactos.
- La ventana observada va de `2026-04-01T00:00:05` a `2026-06-30T23:59:34`.
- La cohorte de demanda conserva las 405998 filas.
- La cohorte de respuesta conserva 365578 filas con bandera oficial valida y tiempo de respuesta coherente.
- Se excluyen de respuesta 40420 registros por bandera oficial no valida y ausencia de `incident_response_seconds_qy`.
- No se detectaron duraciones negativas en despacho, respuesta ni viaje.
- Se identificaron 11 registros con llegada hospitalaria anterior a llegada a escena; quedan trazados en cuarentena.
- `zipcode` tiene 12106 faltantes; no se imputa.

## Conteos por borough

| Borough | Demanda | Respuesta |
|---|---:|---:|
| BRONX | 96641 | 82590 |
| BROOKLYN | 112002 | 105444 |
| MANHATTAN | 97207 | 84714 |
| QUEENS | 82878 | 76294 |
| RICHMOND / STATEN ISLAND | 17270 | 16536 |

## Reproducibilidad

Comando:

```powershell
python research\pipeline\nyc_ems.py phase3 --snapshot 20260909T040537085584Z-56d48fe7ce9b
```

Verificacion previa del snapshot:

```powershell
python research\pipeline\nyc_ems.py verify --snapshot 20260909T040537085584Z-56d48fe7ce9b
```
