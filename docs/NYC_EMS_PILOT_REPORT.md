# Resultado de fase 1: descubrimiento y piloto NYC EMS

Estado: completado. Ejecucion: 8 de septiembre de 2026 en America/Lima; timestamps de evidencia en UTC, 9 de septiembre. Python 3.12.10, biblioteca estandar, configuracion 1.0.0.

## Datos locales

Snapshot: `20260909T035057856354Z-56d48fe7ce9b`.

- [Manifiesto y perfil del piloto](../backend/data/nyc_ems/20260909T035057856354Z-56d48fe7ce9b/manifest.json).
- [Evidencia de descubrimiento](../backend/data/nyc_ems/20260909T035057856354Z-56d48fe7ce9b/discovery.json).
- [Primera pagina original comprimida](../backend/data/nyc_ems/20260909T035057856354Z-56d48fe7ce9b/raw/2026-04/page-000000000.json.gz).

Estas rutas existen localmente y estan excluidas de Git. Para reproducir en otra computadora se requiere transferir la copia respaldada o ejecutar el extractor para crear otro snapshot; el API puede revisar datos publicados.

| Comprobacion | Resultado |
|---|---:|
| Ventana de creacion | 2026-04-01 incluido a 2026-04-08 excluido |
| Filas esperadas por API | 29332 |
| Filas descargadas | 29332 |
| IDs distintos | 29332 |
| Dias cubiertos | 7 |
| Columnas seleccionadas y verificadas contra esquema | 26 |
| Paginas | 10000 + 10000 + 9332 filas |
| Bytes JSON originales | 25440490 (25.44 MB decimales) |
| Bytes JSON comprimidos | 1480319 (1.48 MB decimales) |

Conteos diarios reconciliados: abril 1 = 4716; abril 2 = 4046; abril 3 = 4283; abril 4 = 4236; abril 5 = 3781; abril 6 = 4128; abril 7 = 4142.

La consulta trimestral confirmo 405998 filas y 91 dias con registros en abril-junio. La fecha maxima publicada sigue siendo `2026-06-30T23:59:34.000`. Solo el piloto de siete dias fue descargado; los conteos trimestrales provienen de consultas agregadas.

## Reanudacion e integridad

1. Primera ejecucion con `--max-pages 1`: estado `paused`, 10000 filas.
2. Reanudacion del mismo snapshot: descargo offsets 10000 y 20000; estado `complete`, 29332 filas. La primera pagina se reutilizo.
3. `verify` sin red: checksums, orden, unicidad y ventana correctos.
4. Nueva ejecucion de `extract` sobre snapshot completo: 0 paginas de incidentes descargadas; conteo y huella de IDs sin cambios. Se volvieron a consultar metadatos/agregados de consistencia.

Huella SHA-256 de fechas/IDs ordenados, definida por el extractor:

```text
992233edce4c561c39b72c6b018d7feaf9899bbc690d2007d2d5670bbad3c373
```

Los manifiestos contienen ademas hashes de cada pagina comprimida/original, configuracion, diccionario, mapeos y codigo. La evidencia de fuente antes/despues coincidio. El control detecta cambios mediante metadatos y conteos; no equivale a una transaccion aislada en Socrata.

## Recursos y estimacion

Las tres paginas tardaron aproximadamente 7.71 segundos de descarga en esta conexion. Las dos sesiones de extraccion registraron 14.44 y 21.87 segundos, incluyendo sus comprobaciones; esos tiempos no incluyen el descubrimiento inicial previo a crear el snapshot. La comprobacion posterior del snapshot completo tardo 19.78 segundos.

El mayor pico de asignaciones trazadas por Python de las tres sesiones fue 52395696 bytes (52.40 MB decimales). No es memoria total del proceso ni requisito minimo de RAM. El extractor procesa paginas y mantiene IDs para comprobar unicidad; no carga el trimestre entero en memoria.

Extrapolacion lineal al trimestre, usando este piloto: aproximadamente **20.49 MB comprimidos**, **352.13 MB de JSON original** y **106.67 segundos de descarga de paginas**. Es orientativa: no incluye discovery, verificaciones, reintentos, limpieza ni futuros artefactos; rendimiento y compresion pueden variar.

## Hallazgos para limpieza posterior

- No faltan IDs, fecha de creacion, borough ni area de despacho en el piloto.
- Faltan 783 ZIP, 823 fechas de asignacion, 2144 llegadas a escena y 2145 tiempos de respuesta publicados.
- Hay 2145 indicadores de respuesta invalida y 826 de despacho invalido. Se conservaron todas esas filas.
- Los codigos de indicadores observados son Y/N; los mapeos siguen siendo candidatos hasta su revision documentada. Que una categoria no aparezca en siete dias no prueba que no exista en otros meses.
- Boroughs publicados: BRONX 7169; BROOKLYN 7982; MANHATTAN 6880; QUEENS 6000; RICHMOND / STATEN ISLAND 1301. Se conservaron las etiquetas originales.

No se limpiaron, imputaron ni excluyeron incidentes del piloto. Los faltantes anteriores cuentan claves ausentes/nulas; no constituyen una auditoria completa de formatos, valores vacios o secuencias temporales.

## Verificacion y siguiente entrega

Pasaron 9 pruebas automatizadas sin red: reanudacion/idempotencia, paginas alteradas, cambios de fuente, cambio de esquema, IDs duplicados, filas fuera de ventana, configuracion modificada y comportamiento HTTP 429/400. Se ejecutaron fuera del sandbox porque los permisos de directorios temporales de Windows impedieron escribir las fixtures dentro de el.

```powershell
python -m research.pipeline.nyc_ems verify --snapshot 20260909T035057856354Z-56d48fe7ce9b
python -m unittest discover -s research/tests -v
```

EMS-012 (descubrimiento) queda completado. EMS-013 tiene completado el piloto y su reanudacion; sigue pendiente la extraccion trimestral por particiones de la fase 2. EMS-014 (limpieza) permanece pendiente.

Implementacion y comandos: [research/README.md](../research/README.md). Evidencia primaria: las respuestas y consultas guardadas en los archivos locales enlazados arriba.
