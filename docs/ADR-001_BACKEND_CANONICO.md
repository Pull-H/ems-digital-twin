# ADR-001 - Backend canonico de Fase 1

## Estado

Aceptado.

## Decision

Para la Fase 1 del proyecto, el backend canonico es `server.ts` con Node.js + Express.

`backend/app/main.py` queda como backend experimental/de investigacion. No debe usarse como fuente principal de endpoints ni como ruta de ejecucion local hasta que exista un ticket explicito de migracion o separacion de responsabilidades.

## Contexto

- `npm run dev` ejecuta `tsx server.ts`.
- `server.ts` sirve la API y el frontend Vite desde el mismo proceso en desarrollo.
- `server.ts` ya expone endpoints para zonas, bases, ambulancias, hospitales, incidentes, simulaciones, predicciones, despacho, reubicacion, comparaciones e import/export.
- La logica principal de simulacion, despacho, prediccion, estadistica y comparacion vive en TypeScript bajo `src/services`.
- El backend FastAPI actual contiene endpoints incompletos y respuestas placeholder.

## Consecuencias

- Los nuevos endpoints de Fase 1 deben implementarse primero en `server.ts`.
- Los contratos de API deben alinearse con los tipos de `src/types` y los motores de `src/services`.
- El README y los scripts del proyecto deben apuntar a Node/Express como ruta principal.
- FastAPI no se elimina todavia, pero queda fuera del flujo principal para evitar doble mantenimiento.

## Criterios de aceptacion cubiertos

- Existe una decision documentada.
- El comando principal de desarrollo apunta al backend elegido.
- Los endpoints principales estan listados en README.
- El backend secundario queda marcado como experimental.
