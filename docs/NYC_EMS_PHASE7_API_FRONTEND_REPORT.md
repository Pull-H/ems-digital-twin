# NYC EMS - Fase 7: integracion API y frontend

Fecha de ejecucion inicial: 2026-09-17 UTC. Ampliacion motor/UI: 2026-09-18 UTC. Cierre de persistencia y asistente: 2026-09-22.

**Estado vigente:** el [motor SimPy y la vista NYC](NYC_EMS_ENGINE_VISUAL_INTEGRATION.md)
sustituyen la reconstruccion de ventanas descrita en la prueba inicial de este reporte.
Hay simulacion de atencion sobre llegadas historicas o generadas desde pronosticos.
La ultima corrida se persiste localmente y puede restaurarse desde la API.

Snapshot integrado: `20260909T040537085584Z-56d48fe7ce9b`.

## Objetivo

Conectar los artefactos historicos de fases 3-6 con FastAPI y habilitar su carga desde el frontend sin eliminar el modo demo/local.

## Rutas agregadas o ampliadas

| Ruta | Uso |
|---|---|
| `GET /api/datasets` | Lista snapshots locales y marca si estan listos para modo historico. |
| `GET /api/datasets/{dataset_id}/profile` | Devuelve perfil del snapshot, calibracion, modelos disponibles y supuestos de recursos. |
| `POST /api/simulations` | Acepta `data_mode: "historical"`, `dataset_id` y `model_id`. |
| `GET /api/simulations` | Lista corridas recientes persistidas y la corrida activa. |
| `GET /api/simulations/current` | Devuelve la corrida activa en memoria o recuperada. |
| `POST /api/simulations/restore/latest` | Restaura la ultima corrida persistida. |
| `POST /api/simulations/step` | Avanza el reloj historico y refresca incidentes visibles/predicciones. |
| `GET /api/predictions` | En modo historico devuelve predicciones retrospectivas de Fase 5. |
| `POST /api/assistant/query` | Interpreta fases, datos, modelos y corrida activa mediante grafo LangGraph. |

## Integracion frontend

- `DataManagement` lista snapshots historicos disponibles.
- El usuario puede cargar el snapshot NYC listo desde la pestana de datos.
- `App` recibe zonas, bases, hospitales, incidentes, predicciones y metricas desde FastAPI.
- El modo NYC se pausa si la API no responde, sin fallback al demo.
- Se utiliza la flota configurada completa, sin limite visual de 80 unidades.
- Nueva vista 2D/3D con limites oficiales DCP y estados calculados por el motor.
- La pestana `Asistente EMS` consulta documentos, metricas de modelos y estado real de corrida.

## Persistencia de corridas

Se agrego persistencia local ligera en `data/runtime`:

- `active_simulation_run.json`: ultima corrida activa, parametros y estado visible.
- `simulation_runs_index.json`: indice de corridas recientes.
- `runs/<run_id>.json`: registro individual de corrida.

La recuperacion no serializa objetos internos de SimPy. Reconstruye el motor desde los
parametros persistidos y lo avanza hasta el minuto guardado, aprovechando semillas y
muestreo determinista. Esto es suficiente para retomar una corrida local y para que el
asistente pueda leer un estado valido. No sustituye almacenamiento transaccional,
control multiusuario. La auditoria experimental se implementa en Fase 8.

## Asistente analitico

El endpoint `/api/assistant/query` ahora usa LangGraph, con fallback determinista si la
libreria no esta disponible. El flujo ejecuta nodos de normalizacion, clasificacion,
carga documental, contexto del sistema, evidencia, preparacion y respuesta.

Fuentes consultadas:

- documentos locales del plan, reportes y articulo;
- `metrics.json` de Fase 5 para MAE, RMSE, WAPE y modelo seleccionado;
- corrida activa/persistida para politica, demanda, tiempos simulados, pendientes,
  completados, referencia observada y zonas con mayor carga;
- resumen de snapshot y cohortes disponibles mediante `historical_data_service`.

El asistente explica resultados disponibles y puede orientar sobre las comparaciones
pareadas de Fase 8, sin convertirlas en validacion operacional real.

## Verificacion funcional

Prueba inicial anterior a la ampliacion del motor, conservada como antecedente:

- Dataset listo detectado: `20260909T040537085584Z-56d48fe7ce9b`.
- Estado historico inicial: 5 zonas, 300 incidentes visibles, 5 predicciones, `data_mode = historical`.
- Step +60 min: reloj en `64860`, 300 incidentes visibles, 5 predicciones.

## Limitaciones

La Fase 7 integra reproduccion historica, predicciones, simulacion visual y persistencia local al producto. La comparacion experimental formal entre politica tradicional y predictiva se implementa en EMS-019/Fase 8.
