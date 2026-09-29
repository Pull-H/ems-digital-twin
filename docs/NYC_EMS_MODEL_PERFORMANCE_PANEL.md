# NYC EMS - EMS-019C: panel visual de rendimiento predictivo

Fecha de implementacion: 2026-09-22.

## Objetivo

Mostrar dentro de la aplicacion los graficos y tablas generados en EMS-019B, para
que el rendimiento de modelos no quede solo como archivos locales.

## Ubicacion en la app

En modo NYC, abrir:

```text
Prediccion de Demanda
```

El panel muestra:

- resumen del modelo seleccionado por validacion;
- mejor modelo por MAE en prueba;
- WAPE menor;
- numero de boroughs evaluados;
- figuras SVG embebidas:
  - metricas globales;
  - matriz modelo-metrica;
  - MAE por borough;
  - real vs predicho;
- tabla global de prueba;
- pronostico activo por borough.

## Backend

Ruta agregada:

```text
GET /api/model-performance?dataset_id=<snapshot>
```

El endpoint lee:

```text
reports/nyc_ems/<snapshot>/model_performance/
```

y devuelve SVG embebido, rutas locales y tablas CSV parseadas.

## Frontend

Archivos principales:

- `src/components/historical/ModelPerformancePanel.tsx`
- `src/services/apiClient.ts`
- `src/types/index.ts`

## Limitacion

La app muestra los SVG ya generados. Si se borra `reports/nyc_ems/.../model_performance`,
hay que regenerarlos con:

```powershell
python research\visualization\model_performance.py --snapshot 20260909T040537085584Z-56d48fe7ce9b
```
