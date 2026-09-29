# ADR-001 - Backend canonico del proyecto

## Estado

Actualizado.

## Decision

El backend canonico del proyecto es `backend/app/main.py` con Python/FastAPI.

El frontend React se ejecuta con Vite y consume rutas relativas `/api`. En
desarrollo, Vite redirige esas rutas hacia `http://localhost:8000`.

## Contexto

- El proyecto requiere procesamiento de datos, limpieza, modelos, simulacion y
  artefactos de investigacion, donde Python es el entorno principal solicitado.
- `research/` ya contiene el pipeline de extraccion y sera la base para las
  fases 3 en adelante.
- Node queda restringido al frontend y herramientas de build; no contiene API de
  negocio.
- La data local se ubica en `data/`, separada del backend y del frontend.

## Consecuencias

- Nuevos endpoints deben implementarse en `backend/app/api/`.
- La logica de negocio backend debe vivir en `backend/app/services/`.
- El frontend mantiene su cliente HTTP en `src/services/apiClient.ts`.
- `src/` no debe contener backend web.
- `research/` produce artefactos que FastAPI consumira desde `data/`.

## Criterios de aceptacion cubiertos

- Existe una decision documentada.
- El comando backend apunta a FastAPI.
- Las rutas `/api/...` se mantienen para no romper el frontend.
- No quedan dos backends de negocio compitiendo.
