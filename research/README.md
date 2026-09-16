# Investigacion NYC EMS

La fase 0 (EMS-011) define configuracion, contrato y protocolo. La fase 1 agrega descubrimiento API, descarga local reanudable del piloto y verificacion sin conexion. La fase 2 agrega extraccion trimestral por meses y copias versionadas de los insumos. Limpieza y entrenamiento siguen pendientes.

- [Configuracion del trimestre](config/nyc_ems_2026.json): ventana principal y piloto, columnas, cohortes, semillas, cortes temporales y rutas locales.
- [Diccionario normalizado](config/nyc_ems_fields_v1.csv) y [mapeos versionados](config/nyc_ems_mappings_v1.json).
- [Contrato historico](../docs/NYC_EMS_HISTORICAL_DATA_CONTRACT.md) y [protocolo de investigacion](../docs/NYC_EMS_RESEARCH_PROTOCOL.md).
- [Plan y tickets](../docs/PLAN_IMPLEMENTACION_NYC_EMS_2026.md).
- [Resultado del piloto ejecutado y ubicacion de sus datos](../docs/NYC_EMS_PILOT_REPORT.md).
- [Resultado del trimestre completo y version local para fase 3](../docs/NYC_EMS_FULL_EXTRACTION_REPORT.md). No concatenar el piloto con el trimestre: sus fechas se solapan.

El extractor usa Python 3.12+ y solo su biblioteca estandar; no requiere `pip install`. Las dependencias de analisis se fijaran al implementarlas. Node/Express sigue sirviendo la app; FastAPI mantiene su estado experimental segun ADR-001.

## Comandos de fase 1

Ejecutar desde la raiz del repositorio con el mismo interprete `python` durante todo un snapshot. El extractor recibe el token opcional mediante la variable de entorno `SOCRATA_APP_TOKEN`; no carga `.env` automaticamente.

```powershell
# Consultar esquema, fechas, conteos por mes/dia y unicidad del piloto.
# Guarda evidencia y muestra el ID del nuevo snapshot, sin descargar incidentes.
python -m research.pipeline.nyc_ems discover

# Descubrir y descargar un piloto nuevo de siete dias.
python -m research.pipeline.nyc_ems extract

# Continuar una descarga o usar el snapshot creado con discover.
python -m research.pipeline.nyc_ems extract --snapshot <ID_DEL_SNAPSHOT>

# Comprobar hashes, IDs, orden, ventana y conteos locales sin consultar la API.
python -m research.pipeline.nyc_ems verify --snapshot <ID_DEL_SNAPSHOT>

# Prueba de pausa controlada: descargar una pagina nueva y luego reanudar.
python -m research.pipeline.nyc_ems extract --max-pages 1
python -m research.pipeline.nyc_ems extract --snapshot <ID_DEL_SNAPSHOT>

# Pruebas sin red, con respuestas ficticias y directorios temporales aislados.
python -m unittest discover -s research/tests -v
```

Sustituir `<ID_DEL_SNAPSHOT>` por el ID que imprime el comando; no incluir los signos `< >`. Cada `extract` sin `--snapshot` crea otra copia. Reejecutar sobre un snapshot completo verifica fuente/archivos y no vuelve a descargar sus paginas.

El manifiesto tiene estado `discovered`, `extracting`, `paused`, `complete` o `invalidated`. Solo `complete` acredita descarga reconciliada. Tras una interrupcion, reanudar el mismo ID: las paginas registradas se verifican por SHA-256 antes de reutilizarse. Un archivo `.part` o una pagina escrita antes de registrar el manifiesto no se considera completada y puede reescribirse en esa posicion.

No ejecutar dos procesos de extraccion simultaneos sobre el mismo snapshot. Para **reanudar una extraccion**, cambios de configuracion, diccionario, mapeos, version exacta de Python o codigo extractor requieren un snapshot nuevo. La **verificacion offline** usa la configuracion archivada y permite verificar copias antiguas con el extractor actualizado. Un cambio detectado de fuente invalida el intento y conserva los archivos para auditoria. No hay aislamiento transaccional de Socrata: las marcas de actualizacion y conteos son controles de consistencia, no una garantia de snapshot del publicador.

## Comandos de fase 2

```powershell
# Crear un snapshot del trimestre congelado: abril, mayo y junio.
python -m research.pipeline.nyc_ems extract --mode full

# Descubrir la cobertura del trimestre sin descargar incidentes.
python -m research.pipeline.nyc_ems discover --mode full

# Reanudar con el ID mostrado: el modo se obtiene del manifiesto.
python -m research.pipeline.nyc_ems extract --snapshot <ID_DEL_SNAPSHOT>

# Verificar todos los meses e insumos archivados, sin conexion.
python -m research.pipeline.nyc_ems verify --snapshot <ID_DEL_SNAPSHOT>
```

El modo predeterminado sigue siendo `pilot`; `full` debe indicarse al crear la copia completa. El trimestre y piloto tienen IDs diferentes. No se reutilizan automaticamente archivos del piloto dentro de la copia trimestral: se extrae cada mes bajo la misma evidencia de fuente del nuevo snapshot.

`raw/2026-04/`, `raw/2026-05/` y `raw/2026-06/` tienen offsets independientes desde cero. Los intervalos son inicio incluido/fin excluido. El manifiesto 2.0.0 guarda las particiones y sus conteos esperados; la verificacion comprueba tambien unicidad global de IDs, orden, conteos diarios y que cada fila pertenezca al mes de su pagina. Una particion completada no se vuelve a descargar al reanudar.

## Versionado de copias

Los snapshots nuevos incluyen `provenance/dictionary.csv`, `provenance/fields.csv`, `provenance/mappings.json` y `provenance/extractor.py`. Sus hashes se comparan con el manifiesto; `config.json` conserva la configuracion efectiva. El codigo archivado es evidencia de la version ejecutada, no un comando de ejecucion independiente de su estructura de proyecto.

La evidencia `discovery.json` y `discovery_after.json` contiene esquema, metadatos, fechas y conteos antes/despues. El modo completo comprueba tambien IDs distintos en toda la ventana, no solo en el piloto. Los manifiestos 1.0.0 del piloto anterior permanecen verificables sin modificar sus archivos; no contenian estas copias adicionales de procedencia.

Si cambia la fuente durante una extraccion, el intento queda invalidado cuando se puede comparar la nueva evidencia y se conserva para auditoria. Un error de esquema tambien detiene el proceso. Ejecutar nuevamente sin `--snapshot` crea una version nueva; el sistema no borra ni reemplaza automaticamente versiones anteriores.

## Archivos del piloto

Cada snapshot contiene `config.json`, `discovery.json`, `manifest.json` y paginas `raw/2026-04/page-*.json.gz`. Al terminar o pausar correctamente tambien guarda `discovery_after.json`. Las paginas son arrays JSON comprimidos, con los valores originales de las 26 columnas solicitadas; no se rellenan faltantes ni se filtra por validez.

El manifiesto incluye hashes, URL de cada pagina sin token, filas y bytes, sesiones/reanudaciones, conteos diarios, faltantes y categorias de indicadores/borough. Los datos de perfilado son descriptivos; no marcan automaticamente los mapeos como verificados ni constituyen limpieza.

El perfil de recursos registra segundos de descarga y ejecucion, bytes de respuesta, bytes comprimidos y pico de memoria **trazada por Python** por proceso (no RAM total/RSS). El procesamiento se realiza por paginas y mantiene un conjunto de IDs para comprobar unicidad. La estimacion trimestral extrapola bytes y segundos del piloto; no incluye reintentos, procesamiento ni cambios en red/compresion.

Las salidas se resolveran desde la raiz del repositorio:

```text
backend/data/nyc_ems/<snapshot_id>/raw/
backend/data/nyc_ems/<snapshot_id>/interim/
backend/data/nyc_ems/<snapshot_id>/processed/
backend/data/nyc_ems/<snapshot_id>/simulation/
reports/nyc_ems/<snapshot_id>/
research/artifacts/nyc_ems/<snapshot_id>/
research/private/participants/
```

Estos directorios se crean al producir archivos y estan excluidos de Git. Conservar sus copias y manifiestos en almacenamiento respaldado para el equipo. No introducir tokens en JSON ni respuestas personales en los archivos de configuracion. `SOCRATA_APP_TOKEN` es la variable opcional del extractor.

La ventana esta congelada a abril-junio de 2026. Las fases siguientes deben verificar la fuente otra vez y registrar cada snapshot, sin cambiar de trimestre automaticamente. Los mapeos pendientes permiten descubrir/perfilar datos, pero impiden asumir equivalencias para simulacion antes de documentarlas.
