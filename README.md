# EMS Digital Twin

Gemelo digital para simular una red urbana de servicios medicos de emergencia,
comparar politicas de despacho y analizar indicadores de equidad.

## Arquitectura actual

- `src/`: frontend React/Vite.
- `backend/`: backend oficial Python/FastAPI.
- `research/`: scripts de extraccion, limpieza, entrenamiento y experimentos.
- `data/`: datos locales y artefactos generados, normalmente fuera de Git.
- `docs/`: plan, articulo, contratos y reportes.

La decision arquitectonica esta documentada en
[docs/ADR-001_BACKEND_CANONICO.md](docs/ADR-001_BACKEND_CANONICO.md).

## Ejecutar localmente

Requisitos:

- Node.js 20+.
- Python 3.12+ recomendado.
- Dependencias frontend instaladas con `npm install`.
- Dependencias backend instaladas con `pip install -r backend/requirements.txt`.
- Dependencias de investigacion/ML instaladas con `pip install -r research/requirements.txt`.

Terminal 1:

```bash
npm run dev:backend
```

Terminal 2:

```bash
npm run dev
```

El frontend queda disponible en `http://localhost:5173`.
La API queda disponible en `http://localhost:8000` y `http://localhost:8000/docs`.

## Scripts

```bash
npm run dev          # Frontend Vite con proxy /api -> FastAPI
npm run dev:backend  # Backend FastAPI
npm run build        # Build del frontend
npm run start        # Preview del frontend construido
npm run lint         # TypeScript sin emitir archivos
npm run clean        # Limpia dist/
```

## API principal

Backend canonico: `backend/app/main.py` en Python/FastAPI.

- `GET /api/health`
- `POST /api/simulations`
- `POST /api/simulations/step`
- `PATCH /api/simulations/config`
- `GET /api/comparisons`
- `GET /api/predictions`
- `POST /api/dispatch/evaluate`
- `POST /api/relocation/recommend`
- `GET /api/data/export`
- `POST /api/assistant/query`
