# Contrato de simulacion

Este contrato define la forma canonica de los datos que comparten el motor TypeScript, la API Node/Express y el frontend React.

## Fuente de verdad

- Tipos canonicos: `src/types/index.ts`.
- Estado vivo de simulacion: `SimulationState`.
- Motor que produce el estado: `src/services/simulationEngine.ts`.
- Backend canonico que expone el estado: `server.ts`.

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

## Criterios de compatibilidad

- Todo objeto `Incident` nuevo debe incluir `quintil_socioeconomico`, aunque pueda inferirse desde zona.
- Un campo de tiempo que aun no ocurre se representa con `null`, no con `undefined`.
- El frontend no debe importar `SimulationState` ni `SimEventLog` desde `simulationEngine`; debe importarlos desde `src/types`.
- La API debe devolver `SimulationState` completo en creacion, step y cambios de configuracion.
