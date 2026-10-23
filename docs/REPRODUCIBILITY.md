# Reproducibilidad del estudio NYC EMS

## Version citable y alcance

El codigo fuente publico esta en https://github.com/Pull-H/ems-digital-twin.
La version concreta del estudio y el paquete de evidencia se publican juntos
en la release `v2026.10-repro`. Cite el commit de esa release y el SHA-256 del
archivo ZIP, no solo la rama `main`, que puede cambiar. No hay DOI de Zenodo.

Archivo: `nyc_ems_20260909T040537085584Z-56d48fe7ce9b_evidence.zip`
(626 archivos, 252 859 053 bytes). SHA-256:

```text
6485269efdb4fb464ef06fc282c97439375d943c4af6e4734024c93b3400d7cc
```

El paquete incluye el snapshot NYC EMS de abril-junio de 2026, cohortes y
features derivados, modelos entrenados, entradas de simulacion, resultados de
los experimentos y seis figuras de 600 ppp. El snapshot contiene 405 998
registros de la [fuente NYC Open Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj).
Los datos proceden de la ciudad de Nueva York; la licencia MIT de este
repositorio cubre el codigo, no sustituye los terminos de la fuente publica.

## Obtener y verificar la evidencia

1. Clonar el repositorio y cambiar a la etiqueta de la release.
2. Descargar el ZIP desde la [release](https://github.com/Pull-H/ems-digital-twin/releases/tag/v2026.10-repro)
   a `dist/repro/`.
3. Comparar el SHA-256 del ZIP con el publicado en las notas de la release.
4. Verificar cada archivo del ZIP y luego instalarlo en el clon limpio:

```powershell
git clone https://github.com/Pull-H/ems-digital-twin.git
cd ems-digital-twin
git checkout v2026.10-repro
New-Item -ItemType Directory -Force dist/repro | Out-Null
Invoke-WebRequest -Uri "https://github.com/Pull-H/ems-digital-twin/releases/download/v2026.10-repro/nyc_ems_20260909T040537085584Z-56d48fe7ce9b_evidence.zip" -OutFile "dist/repro/nyc_ems_20260909T040537085584Z-56d48fe7ce9b_evidence.zip"
(Get-FileHash dist/repro/nyc_ems_20260909T040537085584Z-56d48fe7ce9b_evidence.zip -Algorithm SHA256).Hash
python tools/repro_bundle.py verify
python tools/repro_bundle.py install
python -m research.pipeline.nyc_ems verify --snapshot 20260909T040537085584Z-56d48fe7ce9b
```

El instalador rechaza archivos ya presentes; use un clon limpio. El manifiesto
interno del ZIP lista ruta, tamano y SHA-256 de cada archivo. El verificador
no ejecuta codigo contenido en el ZIP. La verificacion del pipeline comprueba
tambien orden, identificadores, particiones y hashes del snapshot original.

## Entorno y pruebas

Entorno de referencia: Python 3.12.10, Node.js 20+, npm y las versiones exactas
del archivo `requirements-repro.lock`; `package-lock.json` fija el frontend.
En un entorno virtual nuevo, desde la raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-repro.lock
npm ci
python -m unittest discover -s research/tests -v
$env:PYTHONPATH = "backend"
python -m unittest discover -s backend/tests -v
Remove-Item Env:PYTHONPATH
python -m unittest discover -s tools/tests -v
npm run lint
npm run build
```

En Linux/macOS, active el entorno con `source .venv/bin/activate` y use
`PYTHONPATH=backend python -m unittest discover -s backend/tests -v`. `npm ci`
requiere una version de Node compatible con las dependencias del lockfile.
El entorno Python fue fijado a partir de la instalacion usada para esta
version; otras plataformas pueden resolver ruedas binarias distintas.

## Replicar el pipeline y los resultados

El ZIP permite auditar las salidas sin descargar Socrata. Para recalcular desde
el snapshot historico instalado (sin modificar el original, copie primero el
directorio del snapshot a otro espacio de trabajo), ejecute en orden:

```powershell
python -m research.pipeline.nyc_ems phase3 --snapshot 20260909T040537085584Z-56d48fe7ce9b
python -m research.pipeline.nyc_ems phase4 --snapshot 20260909T040537085584Z-56d48fe7ce9b
python -m research.pipeline.nyc_ems phase5 --snapshot 20260909T040537085584Z-56d48fe7ce9b
python -m research.pipeline.nyc_ems phase6 --snapshot 20260909T040537085584Z-56d48fe7ce9b
python -m research.visualization.model_performance --snapshot 20260909T040537085584Z-56d48fe7ce9b
python -m research.experiments.fleet_sensitivity --workers 2
```

La fase 8D contiene 22 escenarios, diez semillas (12345-12354) por escenario
y 440 corridas; puede tardar bastante. La configuracion exacta esta en
`research/config/nyc_ems_phase8d_sensitivity_v1.json`. Los resultados
publicados se pueden inspeccionar sin reejecutar el lote en
`reports/nyc_ems/<snapshot>/phase8d/<hash>/tables/` y `figures/`.

La extraccion desde la API (`python -m research.pipeline.nyc_ems extract
--mode full`) crea un snapshot **nuevo**: NYC Open Data puede corregir o
republicar filas. Por ello no equivale necesariamente al snapshot publicado.
Conserve el ZIP congelado y su SHA-256 para replicacion exacta de las entradas.

## Ejecutar el sistema

Con los archivos de evidencia instalados, abra dos terminales:

```powershell
npm run dev:backend
npm run dev
```

Abra `http://localhost:5173`; la API estara en `http://localhost:8000/docs`.
Existe `docker-compose.yml` para levantar frontend y backend con
`docker compose up --build`; monte la evidencia en la carpeta del clon antes
de arrancar. El contenedor no reemplaza el archivo de evidencia.

## Licencia, procedencia y limites

El codigo se distribuye bajo MIT (`LICENSE`). Los incidentes son una copia
de [NYC Open Data](https://www.nyc.gov/opendata/get-started/FAQs) y se
atribuyen a NYC/FDNY; no son datos obtenidos en Peru. La ciudad puede
actualizar la fuente y no garantiza aptitud para un uso operativo. El proyecto
no contiene datos de participantes. Tampoco contiene ubicaciones GPS,
inventario real de ambulancias ni validacion prospectiva; las politicas y
flotas evaluadas son escenarios de investigacion, no recomendaciones de
despacho clinico.
