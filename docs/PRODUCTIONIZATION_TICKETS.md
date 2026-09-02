# EMS Digital Twin - tickets para salir de prototipo

Objetivo de esta fase: convertir la demo academica en una base implementable, medible y mantenible. Avance actual: 3/10 tickets completos = 30%.

## Estado

| ID | Ticket | Estado | Criterio de aceptacion |
| --- | --- | --- | --- |
| EMS-001 | Definir backend canonico del proyecto | Hecho | ADR documenta `server.ts` como backend canonico de Fase 1 y FastAPI queda marcado como experimental. |
| EMS-002 | Unificar contrato de metricas de simulacion | Hecho | `SimulationMetrics` se inicializa desde una fabrica compartida y las vistas usan `incidentes_totales`. |
| EMS-003 | Conectar frontend con API Node con fallback local | Hecho | La app intenta usar `/api/simulations`, `/api/simulations/step` y `/api/comparisons`; si falla, sigue operando localmente. |
| EMS-004 | Retirar duplicacion FastAPI/Express | Pendiente | FastAPI se elimina, se migra a paridad real, o se separa con responsabilidades no duplicadas. |
| EMS-005 | Persistencia de corridas, incidentes importados y parametros | Pendiente | Las simulaciones sobreviven reinicios y se pueden consultar por `run_id`. |
| EMS-006 | Validacion de entrada y errores API consistentes | Pendiente | Endpoints rechazan payloads invalidos con errores tipados y mensajes estables. |
| EMS-007 | Pruebas automatizadas de motores de simulacion/despacho/estadistica | Pendiente | Tests cubren generacion reproducible, seleccion de ambulancia, metricas y benchmark. |
| EMS-008 | Importacion CSV robusta | Pendiente | Parser soporta comillas, columnas faltantes, validacion por fila y reporte de errores. |
| EMS-009 | Observabilidad basica | Pendiente | Health check, logs estructurados, duracion de benchmark y errores de simulacion visibles. |
| EMS-010 | Empaquetado y despliegue reproducible | Pendiente | Dockerfile funcional, scripts de build/start verificados y variables documentadas. |

## Prioridad sugerida

1. EMS-004, EMS-006, EMS-007: consolidan arquitectura y evitan que cambios futuros sean fragiles.
2. EMS-005, EMS-008: convierten la herramienta en flujo de trabajo real con datos y corridas.
3. EMS-009, EMS-010: preparan demo productiva/deployable.

## Notas de revision

- La ruta mas funcional hoy es `server.ts` + React/Vite. `backend/app/main.py` existe, pero sus endpoints son stubs.
- `docker-compose.yml` referencia un `Dockerfile` que aun no existe.
- El proyecto no tenia `node_modules`, por lo que la verificacion de TypeScript requiere instalar dependencias.
- Hay textos con problemas de codificacion visibles en varias pantallas; conviene corregirlos en un ticket propio si se confirma que estan tambien en los archivos fuente y no solo en la consola.
