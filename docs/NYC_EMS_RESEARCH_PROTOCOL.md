# Protocolo de investigacion NYC EMS

Version: 1.0.0. Ticket: EMS-011. Estado: protocolo inicial definido antes del procesamiento y la prueba final. Las decisiones operativas que dependan de calibracion se congelaran con validacion antes de abrir junio.

## Objetivo y preguntas

Evaluar un simulador EMS por zonas calibrado con NYC de abril-junio de 2026 y comparar despacho tradicional con asistencia predictiva. Caso empirico: Nueva York. El alcance es un estudio retrospectivo y de simulacion del trimestre; no estima efectos clinicos ni desempeño real en Trujillo.

1. Prediccion: cuanto mejora o empeora el pronostico de llamadas por borough en la siguiente hora frente a persistencia semanal y promedio historico?
2. Calibracion: que tan bien reproduce el escenario los tiempos y distribuciones observadas que no se impusieron directamente como entrada?
3. Politicas: cual es la diferencia pareada de tiempo de respuesta y cobertura entre tradicional y predictivo bajo las mismas condiciones exogenas?
4. Evaluacion por personas: que evidencia de contenido y consistencia interna presentan los instrumentos para utilidad percibida e interpretacion de resultados del software?

Hipotesis direccional de simulacion: predictivo reduce respuesta media. Se estimara diferencia `predictivo - tradicional`; negativo favorece predictivo. Se reportara tambien ausencia de mejora o deterioro. No seleccionar cohortes, metrica principal o escenarios a partir del resultado favorable.

## Poblacion y tiempo

La poblacion accesible son incidentes publicados creados en `[2026-04-01, 2026-07-01)`, no todos los pacientes ni recursos de FDNY. La principal excluye transferencias, standby y eventos especiales conocidos; banderas desconocidas forman una clase separada. Espera y reapertura permanecen incluidas. Definiciones completas en el [contrato historico](NYC_EMS_HISTORICAL_DATA_CONTRACT.md).

Publicar conteos de fuente, cuarentena, duplicados, cohortes y cobertura geografica. Los analisis adicionales de todas las llamadas o de eventos especiales se etiquetaran como sensibilidad. Una regla de cohorte retrospectiva define el objetivo estudiado; no demuestra que esos indicadores estuvieran disponibles al emitir cada decision.

| Uso | Inicio incluido | Fin excluido | Decisiones permitidas |
|---|---|---|---|
| Entrenamiento | 2026-04-01 00:00 | 2026-05-16 00:00 | Ajustar transformaciones, distribuciones, baselines y modelos |
| Validacion | 2026-05-16 00:00 | 2026-06-01 00:00 | Seleccionar modelo, parametros y diseno experimental |
| Prueba final | 2026-06-01 00:00 | 2026-07-01 00:00 | Evaluacion congelada y reporte |

El piloto tecnico de siete dias esta dentro de entrenamiento. Se puede auditar integridad de todos los archivos al descargar; no usar desempeno ni distribuciones objetivo de junio para ajustar el modelo o escenario. Por defecto no hay reentrenamiento despues de validacion; cambiarlo exige una nueva version antes de prueba.

Pronostico emitido a la hora `t`: objetivo conteo en `[t,t+1h)`. Rezago 1 usa `[t-1h,t)`, rezago 24 usa `[t-24h,t-23h)` y rezago 168 usa `[t-168h,t-167h)`. Media movil de `k` horas usa `[t-kh,t)`. Los conteos previos se asumen disponibles al cerrar cada hora para esta evaluacion retrospectiva; no se afirma disponibilidad de streaming del API.

Excluir etiquetas que crucen el fin de una particion. Reservar 168 horas iniciales para historia de rezagos, sin extraer meses adicionales. Validacion/prueba pueden usar observaciones pasadas de particiones anteriores o de horas ya finalizadas dentro de su bloque. Los coeficientes, normalizadores y codificaciones del modelo quedan ajustados con entrenamiento.

## Metricas y denominadores

En todas las tablas reportar `n`, faltantes y unidad. Si el denominador es cero, devolver no disponible con motivo, nunca cero ni infinito. Distinguir una fila incidente, una celda zona-hora y una replica: no son unidades intercambiables de incertidumbre.

| Metrica | Poblacion / denominador y definicion |
|---|---|
| MAE | Celdas borough-hora de prueba con cobertura y etiqueta validas: suma de errores absolutos / numero de celdas |
| RMSE | Mismas celdas: raiz de suma de errores cuadrados / numero de celdas |
| WAPE (%) | Mismas celdas: 100 x suma de errores absolutos / suma de conteos observados; no disponible si todos son cero |
| Media, mediana y P90 historicos | Cohorte de respuesta; segundos / 60. Para percentiles usar interpolacion lineal y registrar version de libreria |
| Respuesta historica menor a 8 min (%) | 100 x incidentes de respuesta con segundos < 480 / incidentes de cohorte de respuesta; informar cobertura de esta cohorte respecto a principal |
| Respuesta simulada media, mediana y P90 | Incidentes principales admitidos que llegan a escena en cada corrida; tiempo de llegada menos llamada. Reportar n y pendientes por politica |
| Diferencia primaria pareada | Media de respuesta predictiva menos media tradicional por replica emparejada; promedio de diferencias sobre pares validos, IC respetando bloques |
| Cobertura simulada menor a 8 min (%) | 100 x llamadas admitidas con llegada antes de 480 segundos / llamadas admitidas con seguimiento de al menos 480 segundos; sin llegada dentro de ese seguimiento cuenta como incumplida |
| Fraccion sin llegada (%) | 100 x llamadas admitidas sin llegada al corte final / llamadas admitidas. Informar tambien cola al fin de llegadas y al fin de vaciado |
| Utilizacion simulada | Minutos-unidad ocupados dentro del intervalo de medicion / minutos-unidad programados en servicio en ese mismo intervalo; definir estados ocupados antes de prueba |
| Distancia simulada total (km) | Suma de tramos recorridos en intervalo medido; requiere matriz/red y movimiento validado; no es distancia observada EMS |
| Brecha territorial (min) | Maximo menos minimo de respuesta media entre zonas con casos validos; informar n por zona y zonas excluidas |
| Razon de disparidad territorial | Maximo / minimo de esas medias; no disponible si minimo cero o menos de dos zonas |

Las tasas historica y simulada de ocho minutos tienen denominadores diferentes por observabilidad: etiquetarlas separadas y no restarlas como cantidades equivalentes. En respuesta media, si las politicas completan poblaciones distintas, interpretar el estimando como condicionado a llegada; reportar sensibilidad de censura y cobertura antes de afirmar superioridad global.

Para resultados zonales, presentar tanto error global sobre celdas como resumen por borough. Quintiles socioeconomicos no entran en el analisis primario hasta que exista fuente externa compatible. Ocho minutos es un umbral del proyecto, no una recomendacion clinica.

## Calibracion y experimentos

Entrenamiento ajusta componentes temporales; validacion evalua plausibilidad y congela parametros. La reproduccion de llegadas historicas no valida por si sola generacion de demanda. No reutilizar la respuesta historica como salida contrafactual ni sumarla a esperas de cola nuevas.

Ambas politicas reciben mismos incidentes, recursos, estado inicial y condiciones exogenas. Preasignar variaciones por incidente/componente o flujos independientes de aleatoriedad: igual semilla con distinto consumo de numeros no basta. Semillas iniciales versionadas: modelo 20260401, simulacion 20260402 y bootstrap 20260403. Registrar algoritmo aleatorio y semillas efectivas por replica.

Presupuesto inicial: 30 pares, ajustable por precision estimada en validacion, nunca por significancia observada en junio. IC del 95% por diferencias pareadas con bloques temporales cuando corresponda. Si se mantienen llegadas fijas en todas las replicas, la incertidumbre es condicional a ellas; no tratar incidentes de una corrida como muestras independientes.

Antes de fase 8, registrar con entrenamiento/validacion: politicas exactas y desempates, geografia, flota, matriz de viaje, parametros de servicio/liberacion, rango de sensibilidad, estados ocupados, calentamiento del motor, intervalo de medicion, vaciado y regla de censura. Estos valores quedan pendientes de calibracion; no se toman automaticamente del prototipo. El calentamiento de 168 horas de features no determina el calentamiento del motor.

Mantener igual ventana de llegadas y reglas de vaciado para ambas politicas. No borrar casos pendientes para mejorar resultados. Registrar tolerancias de calibracion y precision objetivo antes de ejecutar prueba final. Si la calibracion no permite comparacion defendible, reportar el limite y conservar el resultado como exploratorio.

## Instrumentos de evaluacion

| Instrumento propuesto | Unidad / entradas | Coeficiente y calculo |
|---|---|---|
| Rubrica de contenido, escala 1-4 por claridad, pertinencia y relevancia | Experto x item x criterio; jueces con experiencia pertinente | V de Aiken por item/criterio: suma de (valoracion - 1) / [n de jueces con respuesta x 3] |
| Escala de utilidad percibida, Likert 1-5, con dimensiones previamente definidas | Participante x item tras tareas representativas del sistema | Alfa por dimension: k/(k-1) x [1 - suma de varianzas de items / varianza del total]; mismos participantes para todas las varianzas |
| Test de interpretacion de resultados, correcto=1 e incorrecto=0 | Participante x item, clave de correccion definida antes de aplicacion | KR-20: k/(k-1) x [1 - suma p(1-p) / varianza del total]; usar varianza poblacional para consistencia con p(1-p) |

Para alfa: excluir del calculo inicial de una dimension a participantes con items faltantes en ella y reportar n/exclusiones; invertir items segun clave previa. Para KR-20: mismos casos completos y reglas de puntuacion; faltante no se transforma automaticamente en incorrecto. Para Aiken: reportar jueces efectivos por item/criterio y faltantes. Coeficientes no disponibles si faltan suficientes casos, k < 2 o varianza total cero; valores negativos se reportan, no se recortan a cero.

Alfa para items 0/1 y KR-20 coinciden usando convenciones consistentes. Estos coeficientes no estiman exactitud de prediccion ni beneficio del despacho. No aplicar KR-20 a una lista heterogenea de requisitos funcionales o usarlo como acuerdo entre jueces.

EMS-020 definira items, dimensiones, seleccion/cantidad justificada de expertos, reglas de revision e intervalos para V. EMS-021 definira muestreo/tamano justificado de participantes, tareas, consentimiento, anonimato y precision de coeficientes antes de recoger respuestas. Las valoraciones y respuestas reales se recogen despues; nunca derivarlas de incidentes NYC ni generarlas artificialmente. No hay aprobacion de comite ni participantes reclutados en fase 0.

## Reproducibilidad y decisiones pendientes

Versionar protocolo, configuracion, diccionario y mapeos. Una modificacion exige motivo, version, fecha y aclarar si se observaron resultados de prueba. Modelos, extracciones y resultados guardaran sus hashes y versiones efectivas. Los originales de datos quedan locales fuera de Git; los instrumentos y respuestas de participantes tienen almacenamiento separado.

Pendientes con responsable tecnico: EMS-012/014 verifican codigos de banderas y zona horaria; EMS-015 valida geografia; EMS-017 sustenta mapeos, recursos y calibracion; EMS-019 cierra diseno de replicas antes de prueba; EMS-020/021 desarrollan y aplican instrumentos. La incertidumbre queda explicita y no bloquea la descarga piloto de fase 1.

Referencias metodologicas y del dataset: [fuentes del plan](PLAN_IMPLEMENTACION_NYC_EMS_2026.md#10-referencias-y-evidencia). Este protocolo concreta decisiones del proyecto; no constituye un registro externo ni una validacion empirica ya realizada.
