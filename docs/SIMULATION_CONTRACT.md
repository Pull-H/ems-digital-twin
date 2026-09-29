# Contrato de simulacion

Este contrato define la forma canonica de los datos que comparten la API FastAPI, los artefactos de simulacion y el frontend React.

## Fuente de verdad

- Tipos canonicos frontend: `src/types/index.ts`.
- Estado vivo de simulacion: `SimulationState`.
- Backend canonico que expone el estado: `backend/app/main.py`.
- Servicios backend: `backend/app/services/`.

## SimulationState

```ts
interface SimulationState {
  sim_minute: number;
  is_running: boolean;
  scenario: SimulationScenario;
  policy: DispatchPolicy;
  seed: number;
  speed_multiplier: number;
  total_duration_min: number;
  traffic_factor: number;
  weather_factor: number;
  zones: Zone[];
  bases: EMSBase[];
  hospitals: Hospital[];
  ambulances: Ambulance[];
  incidents: Incident[];
  predictions: DemandPrediction[];
  relocation_recommendations: RelocationRecommendation[];
  event_logs: SimEventLog[];
  metrics: SimulationMetrics;
  weights: DispatchWeights;
}
```

## Incident

Campos canonicos para tiempos y hospital:

- `tiempo_llamada`: minuto en que entra la llamada.
- `tiempo_despacho`: minuto en que se asigna ambulancia; `null` si aun no se despacho.
- `tiempo_llegada_escena`: minuto de llegada a escena; `null` si aun no llega.
- `tiempo_respuesta_min`: `tiempo_llegada_escena - tiempo_llamada`; `null` si no hay llegada.
- `duracion_atencion_escena_min`: duracion estimada/real de atencion en escena.
- `hospital_id`: hospital destino; `null` si no aplica o aun no se asigna.
- `tiempo_llegada_hospital`: minuto de llegada al hospital; `null` si no aplica o aun no llega.
- `tiempo_liberacion`: minuto en que la ambulancia queda disponible; `null` si sigue ocupada.

No usar nombres legacy para datos nuevos:

- No usar `tiempo_llegada`.
- No usar `tiempo_servicio_escena`.
- No usar `hospital_destino_id`.

## SimulationMetrics

La metrica global canonica para el total es `incidentes_totales`.

`total_incidentes` solo existe dentro de `QuintileMetric`, porque ahi representa el total por quintil.

```ts
interface SimulationMetrics {
  tiempo_promedio_respuesta: number;
  mediana_respuesta: number;
  p90_respuesta: number;
  tiempo_maximo_respuesta: number;
  porcentaje_menor_8min: number;
  distancia_total_km: number;
  utilizacion_ambulancias: number;
  incidentes_totales: number;
  incidentes_atendidos: number;
  incidentes_pendientes: number;
  por_quintil: Record<SocioeconomicQuintile, QuintileMetric>;
  diferencia_max_min_quintiles: number;
  razon_disparidad: number;
}
```

## Ejemplo de respuesta: POST /api/simulations

`POST /api/simulations` acepta el modo demo por defecto y, desde EMS-018, tambien modo historico:

```json
{
  "scenario": "dia_normal",
  "policy": "predictivo",
  "num_ambulances": 80,
  "seed": 12345,
  "duration_min": 43200,
  "weights": {
    "peso_tiempo": 0.45,
    "peso_demanda": 0.25,
    "peso_cobertura": 0.15,
    "peso_equidad": 0.15
  },
  "data_mode": "historical",
  "dataset_id": "20260909T040537085584Z-56d48fe7ce9b",
  "model_id": "hist_gradient_boosting_v1"
}
```

El modo historico obtiene datasets desde `GET /api/datasets` y perfiles desde `GET /api/datasets/{dataset_id}/profile`. Las coordenadas de incidentes historicos son aproximaciones versionadas, no GPS real.

```json
{
  "run_id": "SIM-1788300367429",
  "message": "Simulacion inicializada con exito.",
  "state": {
    "sim_minute": 0,
    "is_running": false,
    "scenario": "dia_normal",
    "policy": "predictivo",
    "seed": 12345,
    "speed_multiplier": 1,
    "total_duration_min": 720,
    "traffic_factor": 1,
    "weather_factor": 1,
    "zones": [],
    "bases": [],
    "hospitals": [],
    "ambulances": [],
    "incidents": [],
    "predictions": [],
    "relocation_recommendations": [],
    "event_logs": [],
    "metrics": {
      "tiempo_promedio_respuesta": 0,
      "mediana_respuesta": 0,
      "p90_respuesta": 0,
      "tiempo_maximo_respuesta": 0,
      "porcentaje_menor_8min": 0,
      "distancia_total_km": 0,
      "utilizacion_ambulancias": 0,
      "incidentes_totales": 0,
      "incidentes_atendidos": 0,
      "incidentes_pendientes": 0,
      "por_quintil": {},
      "diferencia_max_min_quintiles": 0,
      "razon_disparidad": 1
    },
    "weights": {
      "peso_tiempo": 0.45,
      "peso_demanda": 0.25,
      "peso_cobertura": 0.15,
      "peso_equidad": 0.15
    }
  }
}
```

Nota: el ejemplo omite contenido de arreglos para hacerlo legible; en ejecucion real `zones`, `bases`, `hospitals`, `ambulances` y `predictions` vienen poblados.

## Ampliacion NYC: motor de eventos discretos

Contrato vigente de NYC: [motor e integracion visual](NYC_EMS_ENGINE_VISUAL_INTEGRATION.md).
Creacion admite `demand_source: "historical" | "forecast"`, duracion maxima 1440 min,
flota 1-1500 y un inicio dentro de validacion/prueba. `data_mode: "historical"` selecciona
el escenario NYC para ambas entradas. `simulation.demand_source` distingue llegadas reales
de sinteticas; toda atencion producida por el motor es simulada.

El objeto `simulation` agrega reloj, supuestos, indicadores por zona y referencia observada.
`metrics` usa todos los llegados; `incidents` contiene hasta 1000 para visualizacion/exportacion.
`start_minute` y `sim_minute` son minutos desde el inicio del snapshot.
La politica/configuracion NYC se cambia creando una nueva corrida; PATCH devuelve 409.
La API persiste localmente la ultima corrida y un indice de corridas recientes en `data/runtime`.
`GET /api/simulations` lista corridas persistidas, `GET /api/simulations/current` devuelve
la activa y `POST /api/simulations/restore/latest` reconstruye la ultima corrida desde sus
parametros y reloj persistidos. Esto no equivale a aislamiento multiusuario ni almacenamiento
transaccional.
Los run_id desconocidos devuelven 404; entradas invalidas devuelven 422.

## Contrato del asistente analitico

`POST /api/assistant/query` recibe:

```json
{
  "message": "Interpreta la corrida actual",
  "conversation": []
}
```

Devuelve respuesta, intencion clasificada, estado, capacidades, evidencia y traza del grafo.
El asistente puede consultar documentos locales, metricas de modelos, perfil de snapshot y
corrida activa/persistida. Las comparaciones de politica deben basarse en los artefactos
de Fase 8; no debe inventar mejoras fuera de esos resultados.

## Criterios de compatibilidad

- `quintil_socioeconomico` es `null` en NYC: no se infiere riqueza a partir del borough.
- En NYC `por_quintil` esta vacio y los indicadores de disparidad son `null`; la UI no los presenta como resultados.
- Un campo de tiempo que aun no ocurre se representa con `null`, no con `undefined`.
- El frontend no debe importar `SimulationState` ni `SimEventLog` desde `simulationEngine`; debe importarlos desde `src/types`.
- La API debe devolver `SimulationState` completo en creacion, step y cambios de configuracion.
