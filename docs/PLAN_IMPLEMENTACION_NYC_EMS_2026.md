# Plan por fases: datos historicos NYC EMS, simulacion y articulo

Plan de cierre actualizado (2026-09-28): [ampliacion experimental 8C-8G, instrumentos 9A-9B, reproducibilidad y articulo](PLAN_CIERRE_IMPLEMENTACION_NYC_EMS.md). Fase 8C implementada y auditada; las restantes siguen pendientes. [Resultados y bloqueos metodologicos de 8C](NYC_EMS_PHASE8C_AUDIT.md).

Fecha de consulta: 2026-09-08. Estado actualizado: fases 0, 1, 2, 3, 4, 5, 6, 7, 7B y 8 completadas como base funcional de investigacion (EMS-011 a EMS-019), mas mini fases EMS-019B/EMS-019C de visualizacion predictiva; fase 9 pendiente. [Resultado del piloto](NYC_EMS_PILOT_REPORT.md), [extraccion trimestral y evidencia local](NYC_EMS_FULL_EXTRACTION_REPORT.md), [perfilado/limpieza/cohortes](NYC_EMS_PHASE3_QUALITY_REPORT.md), [geografia/features/particiones](NYC_EMS_PHASE4_FEATURES_REPORT.md), [comparacion de modelos](NYC_EMS_PHASE5_MODEL_REPORT.md), [visualizacion de modelos](NYC_EMS_MODEL_PERFORMANCE_VISUALS.md), [panel visual de modelos](NYC_EMS_MODEL_PERFORMANCE_PANEL.md), [calibracion/reproduccion historica](NYC_EMS_PHASE6_SIMULATION_CALIBRATION_REPORT.md), [integracion API/frontend](NYC_EMS_PHASE7_API_FRONTEND_REPORT.md) y [experimentos pareados](NYC_EMS_PHASE8_EXPERIMENTS.md).

## 1. Objetivo y alcance

Desarrollar y evaluar un simulador EMS por zonas, calibrado con incidentes historicos de Nueva York, que permita pronosticar demanda y comparar una politica de despacho tradicional con una politica asistida por prediccion. El resultado inicial sera un gemelo digital de investigacion con actualizacion por lotes y supuestos explicitos sobre recursos.

Pregunta propuesta para el articulo: **En escenarios calibrados con NYC EMS de abril a junio de 2026, que diferencias produce una politica predictiva frente a una tradicional en tiempos de respuesta, cobertura y diferencias territoriales?** La mejora es una hipotesis que se debe contrastar, incluso si los resultados no favorecen la politica predictiva.

El caso empirico de esta fase sera NYC. Este alcance actualiza la propuesta exploratoria de mezclar NYC con geografia de Trujillo en `DATASETS_HISTORICOS_PARA_INVESTIGACION.md`. Una adaptacion a Trujillo requerira un estudio de transferencia separado. Tres meses permiten un piloto temporal acotado; no permiten validar estacionalidad anual ni generalizacion a todo 2026.

## 2. Periodo verificado y volumen

Se consultaron directamente la API, sus metadatos y los conteos mensuales y diarios. La fecha maxima de incidente devuelta fue **2026-06-30T23:59:34.000**. El catalogo oficial registra una actualizacion el 15 de julio de 2026; esa fecha de publicacion es distinta de la fecha de los incidentes. [Fuente: catalogo](https://catalog.data.gov/dataset/ems-incident-dispatch-data).

| Mes | Incidentes publicados |
|---|---:|
| Abril de 2026 | 128922 |
| Mayo de 2026 | 138649 |
| Junio de 2026 | 138427 |
| Total | **405998** |

La consulta diaria devolvio 91 dias con registros, entre 3700 y 5210 por dia. Esto demuestra continuidad diaria observada, pero no certifica que el publicador haya incluido todos los incidentes del sistema original.

Ventana congelada propuesta: **`[2026-04-01T00:00:00, 2026-07-01T00:00:00)`**. El extremo final es exclusivo para evitar duplicaciones en fronteras de meses. La disponibilidad de julio, agosto o septiembre no se presupone.

Para empezar, usar todos los incidentes del **1 al 7 de abril**, con fin exclusivo el 8 de abril. Luego ejecutar el mismo proceso sobre el trimestre completo. La muestra de siete dias sirve para probar el pipeline, no para obtener resultados finales del articulo.

Antes de una nueva extraccion se consultara la fecha maxima y la cobertura diaria. Se seleccionaran tres meses consecutivos de 2026 con cobertura hasta el ultimo dia y se revisaran posibles huecos. Si el ultimo mes es parcial se retrocedera al anterior. Si no hay tres meses elegibles en 2026, el proceso informara la limitacion sin cambiar silenciosamente de anio. Cada estudio conservara su ventana aunque el portal reciba nuevas publicaciones.

## 3. Evidencia disponible y cambios que necesita el proyecto

Se contrasto `EMS_incident_dispatch_data_description.csv` con el esquema de la API: hay 31 campos de negocio; sus nombres en la API estan en minusculas. Los espacios o asteriscos del diccionario no forman parte de los identificadores API.

| Evidencia del dataset | Uso previsto | Limite |
|---|---|---|
| Creacion, tipo inicial, severidad y zona | Demanda historica, llegadas y prioridades | Tipo de llamada no equivale a diagnostico clinico |
| Asignacion, llegada y banderas de validez | Calibrar y evaluar tiempos | Son datos del incidente y primeras unidades; no una trayectoria completa de cada ambulancia |
| Salida hacia hospital, llegada y cierre | Describir intervalos del incidente | No identifican hospital destino, camas disponibles ni momento real de liberacion de la unidad |
| Borough, dispatch area, ZIP | Analisis y simulacion por zonas | No hay coordenadas exactas; ZIP postal no equivale automaticamente a ZCTA censal |
| Indicadores de transferencia, espera, evento y reapertura | Definir cohortes y auditar excepciones | Una ausencia de dato no equivale a un indicador negativo |

El [catalogo NYC](https://catalog.data.gov/dataset/ems-incident-dispatch-data) explica que las ubicaciones se agregan para proteger la identidad. El diccionario local define `incident_travel_tm_seconds_qy` como **asignacion a llegada a escena**: incluye el intervalo previo a activacion y no debe confundirse con conduccion pura.

Hallazgos del codigo que se deben atender:

- `backend/app/api/data_io.py`: `/api/data/import` es una base de importacion; debe evolucionar hacia validacion robusta, trazabilidad de errores y conexion real con cohortes limpias.
- `src/services/simulationEngine.ts`: el constructor genera incidentes sinteticos; necesita recibir un conjunto historico y su configuracion espacial.
- `src/services/predictionEngine.ts`: las predicciones llamadas ML se calculan mediante formulas y multiplicadores; falta entrenamiento y evaluacion historica.
- `src/services/cityData.ts` y `dispatchEngine.ts`: la geografia y los recursos iniciales estan acoplados al prototipo; deben poder cargarse desde un escenario NYC.
- `src/types/index.ts`: varios campos obligatorios, como quintil, coordenadas y hospital, requieren distinguir evidencia, aproximaciones y datos no disponibles.
- `src/services/statsEngine.ts`: el bootstrap usa `Math.random()`; los experimentos reproducibles necesitan aleatoriedad controlada y pruebas estadisticas verificadas.

Se actualiza la decision de `ADR-001_BACKEND_CANONICO.md`: **FastAPI es el backend oficial**. El frontend React/Vite consume `/api` mediante proxy en desarrollo. Los scripts de `research/`, con pandas, PyArrow y scikit-learn cuando corresponda, exportaran artefactos a `data/` para ser consumidos por FastAPI.

## 4. Fases y criterios de salida

### Fase 0. Protocolo, contrato y configuracion

Definir unidad de analisis (incidente), cohorte principal (llamadas de emergencia, con reglas documentadas para transferencias, standby y eventos), geografia y preguntas del estudio. Descargar primero sin filtros de calidad para poder contar todas las exclusiones despues.

Crear una configuracion con dataset ID, ventana, columnas, tamano de pagina, zona horaria, semillas, reglas de limpieza y rutas de salida. Conservar ID y ZIP como texto. Versionar diccionario, mapeos y protocolo de evaluacion antes de ver resultados de prueba.

**Entregables implementados:** [configuracion](../research/config/nyc_ems_2026.json), [diccionario normalizado](../research/config/nyc_ems_fields_v1.csv), [mapeos versionados](../research/config/nyc_ems_mappings_v1.json), [contrato historico](NYC_EMS_HISTORICAL_DATA_CONTRACT.md) y [protocolo del estudio](NYC_EMS_RESEARCH_PROTOCOL.md). Uso y almacenamiento en [research/README.md](../research/README.md).

**Criterio de salida:** cada variable esta clasificada como observada, derivada, externa o asumida; cada metrica tiene poblacion y denominador definidos. No se asignan quintiles, prioridades clinicas ni coordenadas reales sin evidencia.

### Fase 1. Descubrimiento y extraccion piloto

Implementar consultas de fecha maxima, esquema y conteos por mes/dia. Guardar las respuestas como evidencia. Probar extraccion de siete dias y medir tiempo, bytes y consumo de memoria.

Endpoint de lectura verificado: `https://data.cityofnewyork.us/resource/76xm-jjuj.json`. Metadatos: `https://data.cityofnewyork.us/api/views/76xm-jjuj.json`. La interfaz Foundry necesita contenido dinamico; se contrasto su esquema mediante estos metadatos.

Usar paginas de **10000 registros**, orden estable por `incident_datetime,incident_id` y filtro temporal. Los campos de ID deben validarse como unicos; si no lo son, revisar la clave antes de reanudar por cursor. El trimestre requeriria unas 42 paginas no vacias si se pagina por mes, mas las consultas de control. El valor por defecto de Socrata es 1000 registros: una sola peticion sin paginacion puede quedar incompleta. [LIMIT](https://dev.socrata.com/docs/queries/limit.html), [OFFSET](https://dev.socrata.com/docs/queries/offset.html).

**Entregables implementados:** [CLI de descubrimiento/extraccion/verificacion](../research/pipeline/nyc_ems.py), muestra cruda local de 29332 incidentes, perfil de recursos y manifiesto piloto. [Comandos](../research/README.md#comandos-de-fase-1) y [reporte de ejecucion](NYC_EMS_PILOT_REPORT.md).

**Criterio de salida:** las filas descargadas coinciden con el conteo API del piloto; una interrupcion y reanudacion produce los mismos IDs sin duplicados. El costo del trimestre se estima con los bytes realmente observados, sin prometer un tamano de archivo antes de medirlo.

### Fase 2. Extraccion completa y versionado

Extraer abril, mayo y junio por particiones mensuales. Usar `$select` con las columnas del apartado 5, `$where` por intervalo y `$limit/$offset` con orden explicito. A estos volumenes, offset por mes es suficiente como primera implementacion.

Procesar y escribir cada pagina por separado. Aplicar timeout, reintentos limitados con espera exponencial para fallos transitorios, respeto de `Retry-After` ante 429 y parada ante errores de consulta/esquema. El token opcional se envia mediante `X-App-Token` y se guarda como `SOCRATA_APP_TOKEN` fuera de Git. [Documentacion de tokens](https://dev.socrata.com/docs/app-tokens.html).

El manifiesto incluira consultas sin credenciales, fecha de extraccion UTC, ventana, esquema, version del codigo/configuracion, metadatos de actualizacion de la fuente, conteos esperados/recibidos, bytes y SHA-256 de archivos. Marcar pagina completada solo tras una escritura atomica. Al reanudar, comprobar su hash y que la fuente sigue en la misma version.

El orden no proporciona aislamiento ante cambios del portal. Comparar metadatos y conteos antes y despues de extraer; si cambian, marcar el intento inconsistente y repetir la particion en una nueva version. Conservar la copia cruda del estudio: el portal puede revisar datos historicos.

**Entregables implementados:** 405998 incidentes en 41 paginas JSON comprimidas por mes, manifiesto completo y copias de configuracion, diccionarios, mapeos y codigo ejecutado. [Reporte de extraccion y rutas locales](NYC_EMS_FULL_EXTRACTION_REPORT.md). Datos grandes fuera de Git; scripts y resumen de procedencia disponibles en el repositorio.

**Criterio de salida:** completitud respecto al conteo de la misma version, ausencia de duplicados entre paginas, hashes verificables y ejecucion repetible sin volver a descargar particiones validas. El total esperado hoy es 405998; una revision futura debe registrarse, no forzarse a ese numero.

### Fase 3. Perfilado, limpieza y cohortes

Perfilar nulos, duplicados, tipos, categorias desconocidas, cobertura temporal/territorial, secuencias de fechas y distribuciones de duraciones. Conservar siempre la tabla cruda y generar banderas de calidad por fila.

Reglas iniciales:

1. Eliminar duplicados exactos dejando trazabilidad; poner IDs repetidos con contenido incompatible en cuarentena para revision.
2. Parsear fechas preservando el texto original. Socrata publica fechas sin offset; usar `America/New_York` como convencion del estudio, documentar su confirmacion con el publicador y tratar ambiguedades de horario de verano explicitamente. Nunca interpretar estas horas automaticamente como Lima o UTC. [Floating timestamps](https://dev.socrata.com/docs/datatypes/floating_timestamp.html).
3. Normalizar texto y convertir numeros sin transformar faltantes a cero. Validar valores reales de las banderas antes de fijar el mapeo Y/N/desconocido.
4. Contrastar `dispatch_response_seconds_qy` con asignacion menos llamada, y `incident_response_seconds_qy` con llegada menos llamada; registrar discrepancias con una tolerancia justificada por precision de la fuente.
5. Marcar duraciones negativas, secuencias incompatibles y tiempos extremos. No borrar automaticamente respuestas muy largas: pueden reflejar saturacion real. Si se ensaya recorte de extremos, fijarlo con entrenamiento y reportar analisis de sensibilidad.
6. Mantener una cohorte de **demanda** con fecha/ID y geografia utilizable, aunque falten tiempos de respuesta. Conservar zona desconocida para reconciliar el total de la ciudad.
7. Crear una cohorte de **respuesta** con banderas oficiales validas y tiempos coherentes. No imputar el tiempo objetivo ni excluir incidentes de demanda solo por carecer de respuesta valida.
8. Mantener cohortes de transporte y eventos especiales separadas. Una hora hospitalaria faltante no demuestra que no hubo traslado. Registrar eventos censurados al cierre del periodo.

**Entregables implementados:** `incidents_clean.parquet`, `demand_cohort.parquet`, `response_cohort.parquet`, `transport_cohort.parquet`, `quality_report.json`, `quarantine.csv`, `cohort_summary.json` e `inclusion_exclusion_report.json`. Resumen en [reporte de Fase 3](NYC_EMS_PHASE3_QUALITY_REPORT.md).

**Criterio de salida:** el conteo inicial se reconcilia con conservados, duplicados y cuarentena; las cohortes son reproducibles y sus exclusiones no se cuentan dos veces. Pruebas con nulos, comillas CSV, duplicados conflictivos y marcas de tiempo invalidas.

### Fase 4. Geografia, variables y particion temporal

Empezar el pronostico con **borough por hora**; construir una tabla de correspondencia estable para dispatch areas antes de usar mayor detalle en la simulacion. Evitar una misma columna que mezcle borough, ZIP y dispatch area como unidades equivalentes.

Obtener limites oficiales NYC y, si se implementan quintiles, datos socioeconomicos compatibles de Census/ACS con version y correspondencia geografica. La fuente EMS no contiene ingresos ni quintiles. Hasta contar con esa union, mostrar diferencias por territorio y representar los indicadores socioeconomicos como no disponibles.

Crear rejilla zona-hora completa: rellenar con cero un intervalo sin llamadas solo cuando se haya confirmado cobertura; un hueco de extraccion sigue siendo faltante. Variables: hora, dia de semana, fin de semana, zona, rezagos de 1/24/168 horas y medias moviles calculadas exclusivamente con pasado. Preservar tipo/severidad inicial para llegadas historicas y distribuciones de calibracion.

Objetivo inicial: numero de llamadas en la siguiente hora por zona. No usar tipo/severidad final, duraciones del mismo incidente, conteos futuros ni recursos inexistentes como predictores disponibles al emitir el pronostico.

Particion propuesta: entrenamiento del 1 de abril al 15 de mayo; validacion del 16 al 31 de mayo; prueba final del 1 al 30 de junio. Cortes a medianoche local, con intervalos exclusivos. Ajustar transformaciones solo con entrenamiento y mantener junio cerrado hasta congelar decisiones. Eliminar de cada particion etiquetas cuyo horizonte cruce su frontera. Las primeras 168 horas pueden usarse como calentamiento para los rezagos semanales.

**Entregables implementados:** `hourly_demand_panel.parquet`, `model_ready_hourly_demand_panel.parquet`, `feature_dictionary.json`, `temporal_partitions.json`, `geography_summary.json` y `historical_incident_events.parquet`. Resumen en [reporte de Fase 4](NYC_EMS_PHASE4_FEATURES_REPORT.md).

**Criterio de salida:** suma de conteos consistente con la cohorte elegida, ninguna variable usa futuro y geografia NYC independiente de los valores sinteticos de Trujillo.

### Fase 5. Baselines y entrenamiento

Comparar tres modelos reproducibles: baseline temporal por zona/dia/hora, Random Forest y Gradient Boosting. Configurar semillas y guardar versiones/dependencias.

Evaluar MAE y RMSE globales y por zona, mas WAPE cuando su denominador sea distinto de cero. Evitar MAPE en series con ceros. Evaluar en origen movil: en cada hora solo se incorporan observaciones previas; el esquema de actualizacion debe ser igual para todos los modelos. Registrar desempeno por hora y zona, no solamente una media favorable.

El primer producto usa horizonte de 60 minutos. El contrato actual tambien contempla 15 y 30: ocultarlos/deshabilitarlos en modo historico hasta entrenarlos y validarlos, sin presentarlos como resultados obtenidos dividiendo mecanicamente el pronostico horario.

Exportar inicialmente una tabla de pronosticos retrospectivos con `issued_at`, `target_start`, `target_end`, `zone_id`, `prediction`, `model_id` y fecha limite del entrenamiento. FastAPI consumira el pronostico correspondiente al reloj simulado. La inferencia en vivo sera una ampliacion posterior.

**Entregables implementados:** modelos `joblib`, `retrospective_forecasts.parquet`, `metrics.json`, `model_card.json` y copia de predicciones en `data/.../processed` para integracion posterior. Resumen en [reporte de Fase 5](NYC_EMS_PHASE5_MODEL_REPORT.md).

**Criterio de salida:** resultados reproducibles sobre la misma prueba final, sin valores ML ficticios y con disponibilidad temporal comprobada para cada pronostico.

### Fase 6. Calibracion y reproduccion historica del simulador

Introducir dos modos: reproduccion historica para inspeccionar lo ocurrido y simulacion contrafactual para comparar politicas. En la reproduccion pueden mostrarse tiempos observados; en el contrafactual las llegadas son comunes y los tiempos de respuesta los genera cada politica.

Implementar un adaptador de historicos a entradas del motor. `sim_time_min` sera la diferencia real desde el inicio de la ventana, no un incremento artificial por fila. Guardar los tiempos observados en una tabla de referencia separada de los resultados de cada corrida.

La calibracion usara entrenamiento; la validacion ajustara decisiones antes de junio. Comparar distribuciones por zona/franja/prioridad, medianas, P90 y volumen de llamadas. Si se usa reproduccion exacta, el volumen coincide por construccion y no cuenta como validacion independiente de demanda generada.

Para evaluar reubicacion hacen falta ubicacion/cantidad de unidades, tiempos entre zonas y disponibilidad. Crear un registro de supuestos con fuente, rango e incertidumbre: el dataset no identifica estos parametros de forma unica. Los centroides y posiciones generadas dentro de poligonos seran aproximaciones etiquetadas. Una matriz vial externa o simplificada debera justificarse y someterse a sensibilidad.

No sumar una respuesta historica completa a una espera de cola generada por el simulador: duplicaria componentes. Separar espera de asignacion, activacion/viaje, escena, traslado y disponibilidad. El cierre del incidente no equivale a liberacion de ambulancia; usarlo solo como proxy explicitamente identificado si se justifica, con sensibilidad.

**Entregables implementados:** `historical_replay_inputs.parquet`, `observed_time_components.parquet`, `calibration_parameters.json`, `nyc_scenario.json`, `resource_assumptions.json` y `phase6_manifest.json`. Resumen en [reporte de Fase 6](NYC_EMS_PHASE6_SIMULATION_CALIBRATION_REPORT.md).

**Criterio de salida:** cola historica real, tiempos coherentes, trazabilidad de parametros y pruebas de colas, recursos y conversion segundos/minutos. La aptitud para comparar politicas queda condicionada al ajuste y la sensibilidad; ajustar unas medias no demuestra reconstruccion exacta de FDNY.

### Fase 7. Integracion API y frontend

Extender las rutas existentes de FastAPI, preservando `/api/simulations`. Propuesta: catalogo/perfil mediante `/api/datasets` y `/api/datasets/:id/profile`; agregar a creacion de simulacion `dataset_id`, ventana, `data_mode`, `model_id` y version del escenario. Validar que pertenecen al mismo periodo/geografia.

Guardar dataset, corrida, parametros, resultados y procedencia con la persistencia de EMS-005. Cargar paginas de datos desde disco/almacenamiento; la extraccion no debe ejecutarse dentro de una peticion web larga ni enviar todo el trimestre al navegador.

`DataManagement` mostrara periodo, cobertura y calidad; `MapView` y `DigitalTwin3D` usaran la geografia NYC y ubicaciones aproximadas identificables; `PredictionPanel` mostrara modelo/horizonte/evaluacion; `ComparisonView` mostrara corridas realmente ejecutadas. Revisar el fallback local: una corrida de investigacion fallida no puede continuar silenciosamente con datos sinteticos.

Extender tipos y `SIMULATION_CONTRACT.md` para valores no disponibles y procedencia. Si faltan quintiles, no rellenarlos con los del prototipo; adaptar calculo y visualizacion de metricas. Si no hay evidencia de hospital destino, mantener destino observado como desconocido y cualquier hospital simulado como parametro del escenario.

**Entregables implementados:** `/api/datasets`, perfil de snapshot, modo `data_mode: "historical"` en `/api/simulations`, predicciones retrospectivas en `/api/predictions`, carga de snapshot desde `DataManagement`, persistencia local de corridas en `data/runtime`, endpoints de corridas recientes/activa/restauracion y reporte en [Fase 7](NYC_EMS_PHASE7_API_FRONTEND_REPORT.md).

**Criterio de salida:** reiniciar y recuperar una corrida; reproducirla con sus versiones; verificar que los incidentes importados alimentan el motor y que ningun resultado sintetico se presenta como historico.

### Cierre operativo de fases 6-7. Motor e integracion visual

Implementado: motor SimPy de cola/despacho/escena/traslado/liberacion, entradas historica
y pronosticada, semillas reproducibles y tiempos muestreados solo del entrenamiento.
Frontend NYC con limites DCP, controles de corrida y vistas 2D/3D sincronizadas.
La flota no se recorta por visualizacion; no hay fallback silencioso de NYC al demo.
Los indicadores observados y simulados estan separados y no se muestran quintiles inventados.

Detalle, supuestos y pruebas: [motor e integracion visual](NYC_EMS_ENGINE_VISUAL_INTEGRATION.md).
Implementado tambien: persistencia local de `run_id`, parametros, ultimo estado y resumen
de metricas en `data/runtime`. La API expone listado de corridas recientes, corrida
activa y restauracion de la ultima corrida. La recuperacion reconstruye el motor desde
parametros y lo avanza hasta el reloj persistido, por lo que conserva reproducibilidad
sin serializar objetos internos de SimPy.

Limite vigente: la persistencia es local y ligera, no multiusuario ni transaccional.
La validacion experimental pareada se desarrolla en fase 8.

### Fase 7B. Asistente analitico LangGraph

Agregar un modulo de interpretacion asistida para consultas sobre estado del proyecto, dataset, metodologia, limites y resultados disponibles. En la etapa actual funciona como asistente analitico determinista con LangGraph: clasifica preguntas, consulta documentos locales, lee artefactos de modelos, revisa la corrida activa o persistida y muestra evidencia usada.

El grafo incorpora herramientas internas para consultar modelos, corridas, metricas, reportes y configuraciones congeladas. El asistente no recomienda politicas ni concluye mejoras si no hay resultados reproducibles disponibles; las comparaciones formales se leen desde Fase 8.

**Entregables implementados:** pestana `Asistente EMS`, endpoint `/api/assistant/query`, grafo LangGraph determinista, trazabilidad de nodos/evidencia, lectura de `metrics.json`, interpretacion de la corrida activa/persistida y separacion explicita entre resultados disponibles y comparacion experimental pendiente.

**Criterio de salida final:** responde con datos del sistema persistido, cita artefactos usados, reconoce capacidades no disponibles y no inventa metricas, zonas prioritarias ni conclusiones del articulo.

### Fase 8. Experimentos y resultados del articulo

Congelar hipotesis, resultado primario, politicas y presupuesto de replicas antes de abrir prueba final. Propuesta primaria: diferencia pareada en respuesta promedio; secundarias: mediana, P90, proporcion menor a ocho minutos, pendientes y diferencias territoriales. Ocho minutos sera un umbral de analisis del proyecto, no un estandar clinico universal.

Comparar tradicional y predictivo con las mismas llegadas, flota, estado inicial y condiciones exogenas. Preasignar aleatoriedad por incidente/componente o usar flujos separados: la misma semilla global no garantiza escenarios pareados si las politicas consumen numeros aleatorios en distinto orden.

Comenzar con 30 replicas pareadas como presupuesto piloto y ajustar cantidad segun precision del intervalo, no segun significancia favorable. Usar dias/bloques y replicas como unidades de comparacion; el remuestreo debe respetar dependencia temporal. Si las replicas comparten demanda fija, sus intervalos solo describen incertidumbre condicionada a esa demanda.

Incluir calentamiento, cola pendiente al final y periodo de vaciado consistente. Reportar incidentes sin atender y denominadores para evitar que una politica parezca mejor por completar solo los casos faciles. Ejecutar sensibilidad a flota, tiempos entre zonas y liberacion de recursos.

**Entregables implementados:** endpoint historico en `/api/comparisons`, `POST /api/comparisons/historical`, ejecucion pareada tradicional vs predictivo, replicas con semillas controladas, deltas por replica, prueba t pareada, Wilcoxon aproximado, bootstrap percentil al 95 %, exportacion JSON/Markdown a `reports/nyc_ems/<snapshot>/phase8/` e integracion en la pestana `Experimentos`. Resumen tecnico en [reporte de Fase 8](NYC_EMS_PHASE8_EXPERIMENTS.md).

**Criterio de salida:** otra persona reproduce las tablas desde los artefactos congelados. La conclusion describe resultados de simulacion del trimestre estudiado, sin atribuir efectos clinicos ni mejoras observadas en operaciones reales. Antes del articulo final se debe congelar el presupuesto definitivo de replicas, flota y sensibilidad.

### Mini fase EMS-019B. Visualizacion de rendimiento predictivo

Generar graficos y tablas exportables para el articulo a partir de Fase 5: barras
globales por modelo, matriz modelo-metrica, errores por borough y serie temporal
real vs predicha para el modelo seleccionado.

**Entregables implementados:** `research/visualization/model_performance.py`, tablas CSV y figuras SVG en `reports/nyc_ems/<snapshot>/model_performance/`, y guia en [visualizacion de modelos](NYC_EMS_MODEL_PERFORMANCE_VISUALS.md).

**Criterio de salida:** el reporte se regenera con un comando, no usa datos simulados y distingue entre seleccion por validacion y mejor desempeno final en prueba.

### Mini fase EMS-019C. Panel visual de rendimiento predictivo

Mostrar dentro de la aplicacion los graficos y tablas generados en EMS-019B.

**Entregables implementados:** endpoint `GET /api/model-performance`, componente `ModelPerformancePanel` y vista integrada en la pestana `Prediccion de Demanda` cuando el snapshot NYC esta activo. Guia en [panel visual de modelos](NYC_EMS_MODEL_PERFORMANCE_PANEL.md).

**Criterio de salida:** el usuario puede ver dentro de la app la matriz modelo-metrica, barras globales, MAE por borough, serie real vs predicha, tabla global y pronostico activo.

### Fase 9. Instrumentos: Aiken, Cronbach y Kuder-Richardson

Disenar instrumentos desde la fase 0; revisar contenido antes del piloto y recoger respuestas una vez que el software permita tareas representativas. Estas respuestas requieren participantes y expertos reales y constituyen datos nuevos, separados de NYC EMS.

| Metodo | Aplicacion defendible en este estudio | Datos necesarios |
|---|---|---|
| V de Aiken | Validez de contenido: expertos valoran claridad, pertinencia y relevancia de items de los instrumentos | Matriz experto x item x criterio, escala y justificacion de seleccion de jueces |
| Alfa de Cronbach | Consistencia interna de puntuaciones de una escala Likert, por dimension coherente, por ejemplo utilidad percibida | Matriz participante x item, reglas de puntuacion, faltantes e items invertidos |
| KR-20 | Consistencia interna de una prueba de interpretacion de resultados/decision con items correcto-incorrecto | Matriz participante x item 0/1 y respuestas correctas definidas previamente |

Una lista heterogenea de requisitos tecnicos cumplidos no se convierte automaticamente en una escala apta para KR-20. Es preferible un test de tareas de interpretacion que mida una capacidad definida. Si ese instrumento no responde a una pregunta del estudio, justificar su exclusion con el asesor en lugar de forzar el coeficiente.

KR-20 coincide con alfa para los mismos items dicotomicos y convenciones de varianza; no son dos validaciones independientes. KR-21 exige supuestos adicionales sobre los items y no sera la opcion inicial. Alfa tampoco demuestra por si solo unidimensionalidad, validez ni exactitud del simulador. [Cronbach, 1951](https://www.ets.org/research/policy_research_reports/publications/article/1951/dblr.html), [Kuder y Richardson, 1937](https://doi.org/10.1007/BF02288391).

Protocolo: definir dimensiones, elaborar items, revision por expertos con V por item/criterio, revisiones documentadas, piloto, version final y aplicacion. Justificar cantidad de jueces y participantes segun precision y factibilidad; reportar intervalos e incertidumbre, sin fijar un numero universal ni seleccionar items solo para aumentar alfa. [Aiken, 1985](https://doi.org/10.1177/0013164485451012).

**Entregables:** instrumentos versionados, plan de participantes/consentimiento, respuestas anonimizadas, puntuaciones y analisis. Si se estudia aprendizaje con pre/post, definir ademas un diseno comparativo; KR-20 no estima el efecto del software.

**Criterio de salida:** cada coeficiente corresponde al instrumento y pregunta correctos; ningun resultado se calcula sobre filas EMS como si fueran encuestados ni se generan respuestas artificiales para el articulo.

## 5. Columnas de extraccion inicial

Seleccion de 26 campos; se omiten inicialmente cinco distritos administrativos que no participan en el primer analisis. El esquema completo se preserva en metadatos.

```text
incident_id,incident_datetime,initial_call_type,initial_severity_level_code,
final_call_type,final_severity_level_code,first_assignment_datetime,
valid_dispatch_rspns_time_indc,dispatch_response_seconds_qy,
first_activation_datetime,first_on_scene_datetime,
valid_incident_rspns_time_indc,incident_response_seconds_qy,
incident_travel_tm_seconds_qy,first_to_hosp_datetime,
first_hosp_arrival_datetime,incident_close_datetime,held_indicator,
incident_disposition_code,borough,incident_dispatch_area,zipcode,
reopen_indicator,special_event_indicator,standby_indicator,transfer_indicator
```

Guardar campos finales para descripcion y auditoria. Su inclusion en el archivo no autoriza usarlos como variables disponibles al despachar o predecir.

## 6. Consultas reproducibles en PowerShell

Estas consultas de lectura se verificaron contra la API durante la preparacion del plan. Las comillas simples evitan que PowerShell interprete `$select` o `$where` como variables del shell.

```powershell
# Fecha maxima publicada
curl.exe --silent --show-error --max-time 60 -G 'https://data.cityofnewyork.us/resource/76xm-jjuj.json' --data-urlencode '$select=max(incident_datetime) as latest,min(incident_datetime) as earliest'

# Conteo de los tres meses seleccionados
curl.exe --silent --show-error --max-time 60 -G 'https://data.cityofnewyork.us/resource/76xm-jjuj.json' --data-urlencode '$select=date_trunc_ym(incident_datetime) as month,count(*) as incidents,min(incident_datetime) as first_incident,max(incident_datetime) as last_incident' --data-urlencode '$where=incident_datetime >= ''2026-04-01T00:00:00'' AND incident_datetime < ''2026-07-01T00:00:00''' --data-urlencode '$group=date_trunc_ym(incident_datetime)' --data-urlencode '$order=month'
```

El extractor aplicara adicionalmente proyeccion, paginacion, reintentos y persistencia. Estos comandos agregados permiten verificar disponibilidad sin descargar cientos de miles de filas.

## 7. Artefactos y consumo de recursos

Estructura propuesta; los directorios y comandos del pipeline se implementaran en sus tickets:

```text
research/
  config/nyc_ems_2026.json
  requirements.txt
  pipeline/                    # discovery, extract, profile, clean, features
  models/                      # train, evaluate, export
  experiments/                 # calibracion y comparaciones
  instruments/                 # instrumentos y scripts psicometricos
data/nyc_ems/<version>/
  manifest.json
  raw/2026-04/                 # paginas .json.gz; tambien mayo y junio
  interim/                     # tablas normalizadas y cuarentena
  processed/                   # incidentes y paneles Parquet
  simulation/                  # llegadas, zonas, parametros y pronosticos
reports/nyc_ems/<version>/      # calidad, modelos, experimentos y figuras
```

Parquet comprimido sera el formato analitico; JSON/CSV acotado sera el intercambio con FastAPI y el articulo. Evitar duplicar el trimestre completo en varios CSV o cargarlo en React. Mantener en memoria una pagina de extraccion o una particion de procesamiento. Entrenar sobre la tabla agregada: cinco boroughs x 91 dias x 24 horas equivalen a 10920 celdas antes de excluir faltantes, frente a 405998 incidentes crudos.

Guardar datos y modelos grandes fuera de Git, con almacenamiento respaldado y acceso del equipo. Versionar configuraciones, mapeos, manifiestos sin secretos y una muestra pequena de prueba. Las respuestas de participantes se almacenaran aparte de los incidentes publicos y con acceso apropiado al protocolo del estudio.

## 8. Tickets propuestos para Jira

Numeracion nueva a partir de EMS-011; **EMS-011 a EMS-019 completados**, incluido el trimestre descargado, versionado, perfilado, limpiado, transformado en panel zona-hora, entrenado con tres modelos comparables, preparado como paquete de reproduccion historica, integrado a FastAPI/frontend y evaluado con experimentos pareados. EMS-020 a EMS-022 siguen pendientes. Las dependencias EMS-005/006/007/008 ya figuran en `PRODUCTIONIZATION_TICKETS.md` y se reutilizan.

| Ticket | Trabajo y entregable verificable | Depende de |
|---|---|---|
| EMS-011 (Hecho) | Protocolo y contrato NYC: ventana, cohortes, columnas, objetivos, configuracion y datos observados/asumidos documentados | EMS-002 |
| EMS-012 (Hecho) | Descubrimiento API: maximo, cobertura diaria/mensual, esquema y evidencia guardada; ventana congelada verificada | EMS-011 |
| EMS-013 (Hecho) | Piloto y trimestre completados: particiones mensuales, reintentos, reanudacion, conteos/hashes y procedencia archivada | EMS-012 |
| EMS-014 (Hecho) | Limpieza y calidad: Parquet, cohortes demanda/respuesta, cuarentena y reporte de exclusiones con pruebas de casos limite | EMS-013 |
| EMS-015 (Hecho) | Geografia y features: zonas NYC, panel horario completo, rezagos sin fuga y particiones congeladas | EMS-014 |
| EMS-016 (Hecho) | Baselines y modelo: entrenamiento, MAE/RMSE por zona, predicciones fechadas y model card reproducible | EMS-015 |
| EMS-017 (Hecho) | Calibracion del motor: adaptador historico, escenario NYC, componentes temporales y registro de supuestos | EMS-015, EMS-007 |
| EMS-018 (Hecho) | Integracion historica API/UI: dataset seleccionable, corridas persistidas y contrato actualizado; datos reales llegan a la cola | EMS-016, EMS-017, EMS-005, EMS-006, EMS-008 |
| EMS-018A (Hecho) | Asistente LangGraph: consulta documentos, modelos, corridas, metricas y limites metodologicos sin inventar resultados finales | EMS-011, EMS-018 |
| EMS-019 (Hecho) | Experimentos pareados: semillas/aleatoriedad controladas, replicas, IC bootstrap, pruebas pareadas y resultados exportables | EMS-018, EMS-007 |
| EMS-019B (Hecho) | Visualizacion predictiva: graficos SVG y tablas CSV de desempeno por modelo, metrica, borough y serie temporal | EMS-016 |
| EMS-019C (Hecho) | Panel visual predictivo en la app: endpoint de figuras/tablas y vista integrada en Prediccion de Demanda | EMS-019B, EMS-018 |
| EMS-020 | Instrumentos y V de Aiken: dimensiones, items, expertos, valoraciones y revision documentada | EMS-011; iniciar en paralelo |
| EMS-021 | Aplicacion y consistencia: piloto/participantes, alfa por dimension y KR-20 del test justificado, con incertidumbre | EMS-018, EMS-020 |
| EMS-022 | Paquete del articulo: metodos, tablas, figuras, limitaciones y reproduccion por otro integrante | EMS-019, EMS-021 |

Cada ticket usa como criterios detallados los de su fase correspondiente. Roles sugeridos: datos/ML para EMS-012 a EMS-016; backend/simulacion para EMS-017; full stack para EMS-018; investigacion con apoyo de estadistica para EMS-019 a EMS-022. EMS-011 debe revisarse conjuntamente.

## 9. Hitos de entrega

1. **Hito A: base de datos historica preparada.** Fases 0-3 / EMS-011 a EMS-014. Termina con trimestre extraido, limpio y auditable. Esta es la primera entrega recomendada del equipo.
2. **Hito B: software historico funcional.** Fases 4-7B / EMS-015 a EMS-018A. Permite visualizar NYC, reproducir incidentes, consultar pronosticos, ejecutar escenarios calibrados persistidos e interpretarlos con el asistente analitico.
3. **Hito C: evidencia para el articulo.** Fases 8-9 / EMS-019 a EMS-022. Termina con experimentos reproducibles e instrumentos aplicados, con resultados y limites documentados.

La preparacion de instrumentos comienza junto al Hito A. No se identifica un hito con un porcentaje arbitrario de toda la plataforma: el avance se demuestra por sus entregables y criterios de salida.

## 10. Referencias y evidencia

- [NYC EMS: dataset seleccionado](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj) y [documentacion Foundry](https://dev.socrata.com/foundry/data.cityofnewyork.us/76xm-jjuj).
- [Metadatos del esquema consultados](https://data.cityofnewyork.us/api/views/76xm-jjuj.json) y consultas del apartado 6: evidencia directa de nombres, tipos, fechas y conteos. Los resultados corresponden a esta consulta y pueden cambiar con futuras publicaciones.
- [Diccionario local de campos](EMS_incident_dispatch_data_description.csv): definiciones operativas utilizadas para tiempos y llamadas.
- [Catalogo oficial replicado en Data.gov](https://catalog.data.gov/dataset/ems-incident-dispatch-data): descripcion, agregacion geografica y fecha de actualizacion.
- [Socrata LIMIT](https://dev.socrata.com/docs/queries/limit.html), [OFFSET](https://dev.socrata.com/docs/queries/offset.html), [tokens](https://dev.socrata.com/docs/app-tokens.html) y [fechas sin zona](https://dev.socrata.com/docs/datatypes/floating_timestamp.html).
- [Aiken (1985), Three Coefficients for Analyzing the Reliability and Validity of Ratings](https://doi.org/10.1177/0013164485451012).
- [Cronbach (1951), Coefficient Alpha and the Internal Structure of Tests](https://www.ets.org/research/policy_research_reports/publications/article/1951/dblr.html).
- [Kuder y Richardson (1937), The Theory of the Estimation of Test Reliability](https://doi.org/10.1007/BF02288391).

La arquitectura, cortes temporales, tamanos de pagina, modelos y criterios propuestos son decisiones de diseno de este plan. Las fuentes documentan el dataset, la API y los fundamentos de los coeficientes; no avalan por si mismas la validez de los experimentos futuros.
