# Datasets históricos para el EMS Digital Twin

Fecha de revisión: 2026-09-08

## Objetivo

Reemplazar los incidentes y parámetros ficticios del prototipo por datos históricos
reproducibles. El objetivo técnico es entrenar la predicción de demanda, calibrar la
simulación y evaluar el despacho tradicional frente a políticas predictivas sin afirmar
resultados clínicos que los datos no permitan demostrar.

No existe un único dataset público que cubra a la vez llamadas EMS, flota, hospitales,
red vial, tráfico, clima y vulnerabilidad social para Trujillo. El estudio debe usar un
**dataset operativo principal** y fuentes contextuales complementarias.

## Resumen de opciones

| Prioridad | Dataset / fuente | Cobertura y unidad | Aporta al proyecto | Limitación relevante | Recomendación |
|---|---|---|---|---|---|
| 1 | [NYC EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj) | Nueva York; incidente CAD, más de 30 millones de filas | Hora de incidente, tipo y severidad, asignación, tiempos de despacho, llegada a escena, viaje y traslado a hospital | Ubicación agregada por privacidad; ciudad distinta de Trujillo | **Mejor base principal** para demanda, tiempos y comparación de políticas. |
| 2 | [NEMSIS Public-Release Research Dataset](https://nemsis.org/using-ems-data/request-research-data/) | EE. UU.; activaciones EMS de múltiples agencias | Registro EMS estandarizado, variables clínicas y operativas; gran escala | Requiere solicitud y los identificadores geográficos/agencias están anonimizados | Alternativa nacional para investigación de patrones, no la primera para simulación espacial fina. |
| 3 | [Fire Department and EMS Dispatched Calls for Service, DataSF](https://data.sfgov.org/w/nuek-vuh3/default) | San Francisco; llamadas CAD despachadas | Tiempos de llamada, despacho, arribo, cierre, tipo y ubicación aproximada | Una llamada puede tener varias unidades: exige consolidar por `call_number` | Buena segunda ciudad para validación externa o piloto espacial. |
| 4 | [Seattle Real Time Fire 911 Calls](https://data.seattle.gov/w/kzjm-xkqj/2myu-6xk5) | Seattle; despacho 911 geocodificado | Fecha/hora, tipo de llamada, latitud/longitud e ID de incidente; filtrar `Aid Response`, `Medic Response` y alarmas médicas | No entrega todo el ciclo de respuesta ni tiempos a escena | Útil para entrenar pronóstico de demanda geoespacial, no para validar tiempos de respuesta. |
| 5 | [SAMU - cubo de atenciones](https://www.datosabiertos.gob.pe/dataset/samu) | Perú; llamadas y atenciones SAMU en cuadros estadísticos | Contexto nacional, volumen de atenciones y categorías públicas | Es agregado; no expone eventos individuales georreferenciados ni ciclo CAD | Usarlo para contextualización peruana o contrastar magnitudes, no para entrenar el motor actual. |
| 6 | [RENIPRESS / listado de IPRESS](https://www.datosabiertos.gob.pe/dataset/datos-de-registros-de-nacidos-vivos/resource/f54b40f4-bf05-4f7c-a461-62e70dec3c62) | Perú; establecimientos de salud registrados | Código, nombre, categoría, estado, distrito, dirección y coordenadas de hospitales/IPRESS | No contiene camas disponibles, ocupación ni tiempos de espera | **Obligatorio** para reemplazar hospitales ficticios de Trujillo. |
| 7 | [INEI: Sistema de Información Distrital y REDATAM](https://www.inei.gob.pe/sistemas-consulta/) | Perú; distrito y, en algunos casos, manzana | Población, vivienda, variables sociales/económicas y geografía para construir índice de vulnerabilidad | La unidad territorial puede ser más gruesa que una zona de despacho | **Obligatorio** para el componente de equidad en Trujillo. |
| 8 | [OpenStreetMap / extracto Perú de Geofabrik](https://download.geofabrik.de/south-america/peru.html) | Perú; red vial y puntos de interés | Calles, sentidos, longitudes, velocidades etiquetadas y puntos de hospitales; permite rutas reales | Cobertura y atributos varían; no equivale a tráfico histórico observado | **Obligatorio** para tiempos de viaje por red vial en Trujillo. |
| 9 | [SENAMHI - descarga de datos meteorológicos](https://www.senamhi.gob.pe/servicios/?p=descarga-datos-meteorologicos) | Perú; estaciones meteorológicas | Precipitación, temperatura y otras variables para modelar escenarios climáticos | Requiere seleccionar estación, periodicidad y depurar faltantes | Recomendado si se evalúan efectos de clima/lluvia. |

## Elección recomendada

### Ruta A: artículo sólido y factible

Usar **NYC EMS Incident Dispatch Data** como dataset operativo principal y un periodo
cerrado, por ejemplo 12 a 24 meses. Conservar una partición temporal: entrenamiento,
validación y prueba final. Complementar con:

1. RENIPRESS, INEI, OSM y SENAMHI para construir una representación real de Trujillo.
2. Una adaptación explícita: el modelo de demanda y de respuesta se calibra con NYC;
   la red espacial, hospitales y análisis de equidad representan Trujillo.
3. Una declaración metodológica transparente: no se infiere desempeño real del SAMU en
   Trujillo sin registros locales de su central de emergencias.

Esta ruta permite un artículo de simulación reproducible sin depender de una autorización
institucional para acceder a microdatos sensibles peruanos.

### Ruta B: mayor validez local

Solicitar a SAMU, GERESA La Libertad, hospitales o municipalidad un extracto
anonimizado de incidentes. Debe contener al menos: identificador anonimizado, fecha y hora
de llamada, prioridad/tipo, coordenada o zona, hora de despacho, hora de llegada a escena,
recurso asignado, hora de liberación y destino hospitalario. Esta es la única ruta que
permitiría afirmar resultados operativos específicos para Trujillo.

### Ruta C: validación de generalización

Entrenar con NYC y evaluar el pronóstico de demanda en Seattle o San Francisco, usando
solo variables comparables. Sirve para demostrar robustez entre ciudades, no para mezclar
sus tiempos de respuesta como si provinieran de una misma población.

## Correspondencia con el modelo actual

| Campo canónico del proyecto | Fuente preferida | Transformación esperada |
|---|---|---|
| `fecha_hora`, `sim_time_min` | NYC, SF o Seattle | Convertir zona horaria; derivar hora, día de semana y minuto relativo. |
| `tipo`, `prioridad` | NYC o NEMSIS | Mapear códigos de llamada/severidad a categorías documentadas; preservar tabla de mapeo. |
| `latitud`, `longitud`, `zona_id` | SF/Seattle; o zona agregada NYC | Asignar a una cuadrícula o zona administrativa. NYC no permite coordenada exacta de incidente. |
| `tiempo_despacho`, `tiempo_llegada_escena`, `tiempo_respuesta_min` | NYC o SF | Calcular diferencias entre marcas de tiempo válidas; no inventar valores faltantes. |
| `hospital_id`, `tiempo_llegada_hospital` | NYC y RENIPRESS | Mapear el destino cuando exista; RENIPRESS aporta la red peruana, no tiempos históricos. |
| `quintil_socioeconomico` | INEI | Crear un índice reproducible por zona/manzana; no asignarlo manualmente. |
| rutas, distancia y tiempo estimado | OSM/Geofabrik | Construir red de calles de Trujillo y calcular rutas; calibrar velocidad con evidencia observada. |
| lluvia/clima | SENAMHI | Unir por fecha/hora y estación cercana; registrar porcentaje de faltantes. |

## Plan de limpieza y procesamiento

1. **Congelar la descarga.** Guardar URL, fecha, licencia, diccionario, consulta usada y
   hash del archivo. No trabajar contra un portal que cambia sin conservar una copia.
2. **Definir la unidad de análisis.** Un incidente, no una unidad despachada. En fuentes
   como SF, consolidar múltiples recursos asociados a la misma llamada.
3. **Normalizar tiempos.** Convertir todas las fechas a una zona horaria definida;
   eliminar o marcar secuencias imposibles, por ejemplo llegada anterior al despacho.
4. **Filtrar calidad.** Usar las banderas de validez del dataset cuando existan. No
   imputar la variable objetivo de respuesta; reportar exclusiones y faltantes.
5. **Anonimizar y agregar.** No almacenar direcciones ni identificadores personales en
   el repositorio. Preferir zona/cuadrícula para análisis y publicación.
6. **Crear zonas.** Usar polígonos administrativos o una cuadrícula regular. Unir
   incidentes, población, vulnerabilidad, hospitales y red vial mediante un identificador
   espacial estable.
7. **Construir variables.** Hora, día, feriado, tipo, severidad, clima, demanda histórica
   rezagada, población, vulnerabilidad, distancia/ruta al hospital y disponibilidad de
   recursos cuando la fuente lo permita.
8. **Dividir por tiempo.** Entrenar con meses iniciales, validar con meses posteriores y
   reservar el último bloque para prueba. No usar una división aleatoria que filtre
   información futura.
9. **Documentar el linaje.** Generar `data/raw`, `data/interim`, `data/processed` fuera
   de Git si contienen datos pesados o restringidos, con scripts reproducibles para cada
   transformación.

## Experimentos mínimos para el artículo

| Pregunta | Datos y método | Métricas |
|---|---|---|
| ¿Puede predecirse la demanda por zona y franja horaria? | Conteos históricos por zona-hora; baseline estacional frente a modelo de ML | MAE, RMSE, WAPE/SMAPE y calibración. |
| ¿La simulación reproduce patrones históricos? | Parámetros calibrados con conjunto de entrenamiento y comprobación en prueba | Distribución de llamadas, tiempos de respuesta, P50/P90, tasa menor a 8 min y error de calibración. |
| ¿La política predictiva mejora sobre la tradicional? | Réplicas de simulación con semillas diferentes y mismos escenarios de entrada | Diferencia de medias, IC bootstrap **pareado**, tamaño de efecto y razón de disparidad. |
| ¿El resultado es equitativo? | Resultados por zona vinculados a índice INEI de vulnerabilidad | Brechas de tiempo, cumplimiento menor a 8 min y razón de disparidad con IC. |

Una réplica es una ejecución completa con una semilla y escenario; los incidentes dentro
de una sola simulación no deben presentarse como réplicas completamente independientes.

## Qué no debe afirmarse con los datos disponibles

- Un dataset estadounidense no prueba que el despacho predictivo funcionará en Trujillo.
- SAMU agregado no permite reconstruir tiempos individuales, rutas ni disponibilidad de
  ambulancias.
- RENIPRESS identifica establecimientos, pero no su capacidad real, ocupación ni admisión.
- OSM proporciona una red vial; no proporciona automáticamente tráfico histórico ni tiempos
  reales de ambulancia.
- La validación con alfa de Cronbach, V de Aiken o KR-20 corresponde a instrumentos de
  evaluación por expertos/usuarios, no sustituye la validación predictiva u operativa.

## Decisión práctica

Para avanzar sin esperar permisos: elegir **NYC EMS + RENIPRESS + INEI + OSM**, y dejar
SENAMHI como variable adicional. Para afirmar relevancia local, iniciar en paralelo una
solicitud formal de microdatos anonimizados al operador EMS de La Libertad.

## Fuentes consultadas

- [NYC Open Data: EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj): dataset CAD, variables y restricciones de ubicación.
- [NEMSIS: solicitud del Public-Release Research Dataset](https://nemsis.org/using-ems-data/request-research-data/) y [diccionario de datos](https://nemsis.org/technical-resources/version-3/version-3-data-dictionaries/).
- [DataSF: llamadas despachadas Fire Department y EMS](https://data.sfgov.org/w/nuek-vuh3/default).
- [Seattle Open Data: Real Time Fire 911 Calls](https://data.seattle.gov/w/kzjm-xkqj/2myu-6xk5).
- [Plataforma Nacional de Datos Abiertos: SAMU](https://www.datosabiertos.gob.pe/dataset/samu).
- [Plataforma Nacional de Datos Abiertos: listado RENIPRESS/IPRESS](https://www.datosabiertos.gob.pe/dataset/datos-de-registros-de-nacidos-vivos/resource/f54b40f4-bf05-4f7c-a461-62e70dec3c62).
- [INEI: sistemas de consulta](https://www.inei.gob.pe/sistemas-consulta/) y [mapa de pobreza monetaria](https://www.inei.gob.pe/media/DocumentosPublicos/pobreza/2018/Mapa-de-Pobreza-2018-Desagregacion.pdf).
- [Geofabrik: extracto OSM de Perú](https://download.geofabrik.de/south-america/peru.html) y [licencia de los extractos](https://www.geofabrik.de/data/download.html).
- [SENAMHI: descarga de datos meteorológicos](https://www.senamhi.gob.pe/servicios/?p=descarga-datos-meteorologicos).
