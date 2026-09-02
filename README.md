# EMS Digital Twin

Gemelo digital para simular una red urbana de servicios medicos de emergencia, comparar politicas de despacho y analizar indicadores de equidad socioeconomica.

## Estado del proyecto

El proyecto ya tiene una primera fase de produccionizacion al 30%. El detalle esta en [docs/PRODUCTIONIZATION_TICKETS.md](docs/PRODUCTIONIZATION_TICKETS.md).

Completado:

- Backlog inicial y criterios de aceptacion.
- Contrato de metricas unificado.
- Frontend conectado a la API Node con fallback local.

Pendiente principal:

- Retirar duplicacion o definir futuro del backend FastAPI experimental.
- Agregar persistencia y validacion fuerte de payloads.
- Incorporar pruebas automatizadas y Dockerfile.

## Arquitectura actual

- `src/`: frontend React/Vite y motores TypeScript de simulacion, prediccion, despacho, estadistica y comparacion.
- `server.ts`: backend canonico de Fase 1. Servidor Express que expone la API y sirve Vite en desarrollo o `dist` en produccion.
- `backend/app/main.py`: backend FastAPI experimental con endpoints incompletos. No es la ruta principal de ejecucion.
- `docs/`: tickets y notas de avance hacia implementacion.

La decision arquitectonica esta documentada en [docs/ADR-001_BACKEND_CANONICO.md](docs/ADR-001_BACKEND_CANONICO.md).
El contrato de datos de simulacion esta documentado en [docs/SIMULATION_CONTRACT.md](docs/SIMULATION_CONTRACT.md).

## Ejecutar localmente

Requisitos:

- Node.js 20+ recomendado.
- Dependencias instaladas con `npm install`.

Comandos:

```bash
npm install
npm run dev
```

La app queda disponible en `http://localhost:3000`.

## Scripts

```bash
npm run dev      # Express + Vite middleware
npm run build    # Build frontend + bundle del servidor
npm run start    # Ejecuta dist/server.cjs
npm run lint     # TypeScript sin emitir archivos
npm run clean    # Limpieza cross-platform de dist/server.js
```

## Variables

Copiar `.env.example` a `.env.local` si se necesita configuracion local.

- `PORT`: puerto del servidor Node. Por defecto `3000`.
- `VITE_API_BASE_URL`: URL base de la API si el frontend se sirve separado. Vacio usa rutas relativas.

## API principal

Backend canonico: `server.ts` en Node.js + Express.

- `GET /api/health`
- `POST /api/simulations`
- `POST /api/simulations/step`
- `PATCH /api/simulations/config`
- `GET /api/comparisons`
- `GET /api/predictions`
- `POST /api/dispatch/evaluate`
- `POST /api/relocation/recommend`
- `GET /api/data/export`
