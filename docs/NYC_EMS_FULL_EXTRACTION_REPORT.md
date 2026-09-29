# Resultado de fase 2: extraccion completa y versionado

Estado de la descarga: completa y reconciliada. Ejecucion: 8 de septiembre de 2026 en America/Lima (9 de septiembre UTC). Python 3.12.10; manifiesto 2.0.0; configuracion 1.0.0.

## Version local

Snapshot completo: `20260909T040537085584Z-56d48fe7ce9b`.

- [Manifiesto: conteos, hashes, paginas y sesiones](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/manifest.json).
- [Descubrimiento previo](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/discovery.json) y [comprobacion posterior](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/discovery_after.json).
- [Configuracion congelada](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/config.json).
- [Diccionario archivado](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/provenance/dictionary.csv), [campos](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/provenance/fields.csv), [mapeos](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/provenance/mappings.json) y [codigo ejecutado](../data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/provenance/extractor.py).

Los datos originales estan en `data/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/raw/`, separados por mes. Cada pagina es un array JSON comprimido con gzip. Los archivos existen localmente y estan excluidos de Git; respaldar el directorio completo para compartir esta version exacta con el equipo.

## Volumen real

| Particion | Filas | Paginas | Bytes comprimidos | Bytes JSON originales |
|---|---:|---:|---:|---:|
| 2026-04 | 128922 | 13 | 6512693 | 111426798 |
| 2026-05 | 138649 | 14 | 6975675 | 118980898 |
| 2026-06 | 138427 | 14 | 6942551 | 118042798 |
| Total | **405998** | **41** | **20430919** | **348450494** |

Las paginas ocupan **20.43 MB decimales comprimidos**, frente a 348.45 MB de JSON original. Las cifras no incluyen metadatos, manifiesto ni copias de procedencia. La estimacion anterior de unas 42 paginas se concreta en 41: 13 de abril y 14 de cada mes restante.

Ventana: `[2026-04-01T00:00:00, 2026-07-01T00:00:00)` en hora local de Nueva York segun la convencion del estudio. Se descargaron las 26 columnas configuradas sin filtros de calidad, exclusiones ni imputacion.

## Integridad y reanudacion

La primera sesion se pauso tras las 13 paginas de abril, con 128922 filas. La segunda verifico y reutilizo abril, descargo 28 paginas de mayo/junio y completo 405998 filas. Los offsets se reinician a cero por mes; el orden global es fecha e ID.

Controles realizados: esquema y tipos esperados; conteos de fuente antes/despues; SHA-256 de paginas comprimidas y originales; fechas dentro de su particion; conteos de los 91 dias; **405998 IDs unicos** sin duplicados entre paginas o meses. El estado final es `complete` y la evidencia de fuente no cambio durante la extraccion.

Huella de fechas/IDs ordenados, segun el algoritmo del extractor:

```text
5797e227be624e8bd4034a85be98288f5b297bfbb0058162201930ce2a67fc66
```

El piloto `20260909T035057856354Z-56d48fe7ce9b` permanece intacto y se verifico nuevamente. Sus datos se solapan con abril: **no concatenar piloto y trimestre** para limpieza o entrenamiento. La fase 3 debe usar exclusivamente el snapshot completo indicado aqui.

## Recursos y pruebas

Las paginas sumaron 172.61 segundos de descarga. Las dos sesiones registraron 92.20 y 253.13 segundos, incluidas verificaciones, sin el descubrimiento inicial anterior a crear la copia. El pico maximo de asignaciones trazadas por Python fue 86366404 bytes (86.37 MB decimales); no equivale a RAM total del proceso.

Pasaron 14 pruebas automatizadas sin red: paginacion y limites de mes, reanudacion, idempotencia, IDs duplicados entre meses, corrupcion de paginas/insumos, cambios de fuente/esquema/configuracion y errores HTTP 429/400. Se conserva compatibilidad de verificacion offline con el manifiesto 1.0.0 del piloto. Reanudar una descarga requiere la misma version de codigo e insumos; verificar offline usa los insumos congelados.

```powershell
# Verificar localmente el trimestre sin consultar la API.
python -m research.pipeline.nyc_ems verify --snapshot 20260909T040537085584Z-56d48fe7ce9b

# Pruebas del extractor.
python -m unittest discover -s research/tests -v
```

Las marcas de actualizacion y conteos son controles de consistencia, no una transaccion aislada del publicador. Los hashes permiten detectar cambios en las copias guardadas, no autentican por si solos la fuente. El periodo queda congelado aunque Socrata publique meses posteriores.

## Siguiente fase

EMS-013 queda completado con la extraccion trimestral y versionado. La fase 3 / EMS-014 implementara perfilado, limpieza y cohortes sobre estos archivos locales. Todavia no existe un dataset limpio ni se ha entrenado ningun modelo con el trimestre.

Implementacion y operacion: [research/README.md](../research/README.md). Evidencia primaria: respuestas y consultas guardadas en el snapshot enlazado arriba.
