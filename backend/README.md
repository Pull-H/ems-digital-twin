# Backend FastAPI

Este es el backend oficial del proyecto.

## Ejecutar

```powershell
npm run dev:backend
```

La API queda disponible en:

```text
http://localhost:8000
http://localhost:8000/docs
```

El frontend React se ejecuta aparte con `npm run dev` y Vite redirige `/api`
hacia este backend.

El procesamiento de datos y ML vive en `research/`; esos scripts generan
artefactos en `data/` que este backend consumira en las fases siguientes.
