# NYC EMS - Fase 8: experimentos pareados

Fecha de implementacion: 2026-09-22.

## Objetivo

Comparar politica de despacho tradicional y politica predictiva bajo condiciones
controladas: misma ventana historica, misma flota, mismo modelo, mismas semillas y
mismos componentes de servicio. El resultado es evidencia de simulacion, no
validacion operacional real.

## Implementacion

Se agrego un experimento pareado en FastAPI:

- `GET /api/comparisons` con parametros historicos.
- `POST /api/comparisons/historical` para ejecutar configuracion explicita.
- Servicio: `backend/app/services/comparison_service.py`.
- Motor usado: `EMSSimulator` con demanda `historical` o `forecast`.
- Exportacion: `reports/nyc_ems/<snapshot>/phase8/`.

Parametros principales:

```json
{
  "dataset_id": "20260909T040537085584Z-56d48fe7ce9b",
  "model_id": "hist_gradient_boosting_v1",
  "start_minute": 64800,
  "duration_min": 720,
  "num_ambulances": 691,
  "seed": 12345,
  "repetitions": 10,
  "demand_source": "historical"
}
```

## Diseno experimental

Por cada replica se ejecutan dos corridas:

1. Politica `tradicional`.
2. Politica `predictivo`.

Ambas usan la misma demanda, semilla base, ventana, flota y modelo. La unidad de
inferencia es la replica. Tambien se conserva una muestra de pares de incidentes
para auditoria de trazabilidad.

El delta se define como:

```text
delta = tradicional - predictivo
```

Por tanto, un delta positivo en tiempos favorece a la politica predictiva.

## Indicadores

Resultado primario:

- diferencia pareada en tiempo medio de respuesta.

Resultados secundarios:

- diferencia en P90 de respuesta;
- diferencia en porcentaje menor a 8 minutos;
- diferencia de servicios no finalizados al corte;
- pares de incidentes emparejados;
- metricas del modelo de demanda utilizado.

No se reportan quintiles socioeconomicos porque el dataset NYC EMS no contiene esa
variable. La equidad se mantiene como limitacion metodologica o como trabajo futuro
si se integra una fuente externa compatible.

## Estadistica

El servicio calcula:

- prueba t pareada sobre deltas por replica;
- Wilcoxon pareado aproximado sobre deltas por replica;
- intervalos bootstrap percentiles al 95 %;
- resumen de metricas tradicionales y predictivas.

Los valores p son aproximados mediante normal estandar. Para el articulo final,
la recomendacion es congelar el protocolo y rerunear el experimento completo con
un presupuesto de replicas acordado.

## Validacion tecnica

Pruebas realizadas:

- `python -m unittest discover -s backend/tests -v`
- `npm run lint`
- `npm run build`

Prueba piloto local:

- Con flota proxy 691 y una ventana de 12 horas, las politicas pueden producir
  deltas cercanos a cero porque la disponibilidad de recursos es muy alta.
- Con una flota de sensibilidad menor, por ejemplo 100 ambulancias en la misma
  ventana, aparecen diferencias operativas entre politicas.

Esta lectura es importante para el articulo: si el sistema tiene recursos
abundantes, el valor de una politica predictiva puede no observarse; su efecto
aparece principalmente bajo presion de recursos, cola o demanda concentrada.

## Limites

- No usa GPS real de ambulancias.
- No usa capacidad hospitalaria observada.
- La liberacion de recursos usa un proxy calibrado.
- La evaluacion es simulada y retrospectiva.
- La conclusion final requiere fijar replicas, flota, ventana y sensibilidad
  antes de reportar resultados en el articulo.
