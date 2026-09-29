# NYC EMS - Fase 6: calibracion y reproduccion historica

Fecha de ejecucion: 2026-09-17 UTC.

Snapshot procesado: `20260909T040537085584Z-56d48fe7ce9b`.

## Objetivo

Preparar un paquete de simulacion historica para que el backend y el frontend puedan consumir incidentes reales en fases posteriores. Esta fase no ejecuta todavia la comparacion final de politicas; deja lista la cola historica, los componentes observados y los supuestos de escenario.

## Resultados principales

| Indicador | Valor |
|---|---:|
| Llegadas historicas preparadas | 405998 |
| Respuestas observadas validas | 365578 |
| Traslados observados validos | 223333 |
| Tasa global de respuesta valida | 0.900 |
| Tasa de traslado sobre respuestas validas | 0.611 |
| Demanda horaria total media | 185.90 |
| Demanda horaria total P90 | 255.00 |

## Tiempos calibrados globales

| Componente | Mediana min | P90 min | P95 min |
|---|---:|---:|---:|
| Despacho / asignacion | 0.63 | 25.90 | 58.30 |
| Respuesta llamada-escena | 10.92 | 47.17 | 82.94 |
| Asignacion a escena | 8.82 | 20.28 | 28.43 |
| Escena a salida a hospital | 22.27 | 41.80 | 50.35 |
| Traslado a hospital | 12.88 | 22.17 | 26.12 |
| Llamada a cierre | 81.18 | 130.60 | 162.85 |

## Escenario NYC

Se genero `nyc_scenario.json` con cinco zonas tipo borough: Bronx, Brooklyn, Manhattan, Queens y Staten Island. Las coordenadas son centroides y cajas aproximadas para visualizacion, no ubicaciones GPS reales de incidentes ni limites oficiales. Cada incidente en `historical_replay_inputs.parquet` incluye una coordenada aproximada deterministica alrededor de su borough para permitir visualizacion futura sin afirmar precision geografica.

## Supuestos de recursos

El dataset no informa flota, bases reales, disponibilidad de ambulancias, camas, demoras hospitalarias ni red vial. Por eso `resource_assumptions.json` conserva esos puntos como supuestos explicitos.

Como punto de partida para sensibilidad, se estimo una flota proxy usando demanda horaria P90 y mediana llamada-cierre:

| Utilizacion objetivo | Ambulancias proxy |
|---|---:|
| 0.35 | 986 |
| 0.50 | 691 |
| 0.65 | 531 |

Estos valores no representan el tamano observado de FDNY EMS. Sirven como escala inicial para experimentos y deben compararse con varios escenarios de flota.

## Artefactos generados

- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/historical_replay_inputs.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/observed_time_components.parquet`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/calibration_parameters.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/nyc_scenario.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/resource_assumptions.json`
- `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/simulation/phase6_manifest.json`

## Reproducibilidad

```powershell
python -m research.pipeline.nyc_ems phase6 --snapshot 20260909T040537085584Z-56d48fe7ce9b
```

