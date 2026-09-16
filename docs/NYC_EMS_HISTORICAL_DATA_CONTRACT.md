3# Contrato de datos historicos NYC EMS

Version: 1.0.0. Ticket: EMS-011. Alcance: especificacion de fase 0 para el pipeline local; su ejecucion se implementa en fases posteriores.

## Fuentes de verdad

- [Configuracion del estudio](../research/config/nyc_ems_2026.json): periodo, columnas, cohortes, cortes temporales, semillas y rutas.
- [Diccionario normalizado v1](../research/config/nyc_ems_fields_v1.csv): 26 campos seleccionados, tipos, procedencia, disponibilidad y unidades.
- [Mapeos v1](../research/config/nyc_ems_mappings_v1.json): reglas candidatas y estado de verificacion. Un mapeo pendiente no se considera validado.
- [Diccionario original](EMS_incident_dispatch_data_description.csv): su SHA-256 esta fijado en la configuracion. Cambiarlo exige revisar contrato/version y conservar el anterior en el historial Git.
- [Protocolo del estudio](NYC_EMS_RESEARCH_PROTOCOL.md): preguntas, poblaciones y denominadores de evaluacion.

Los paths se resuelven desde la raiz del repositorio. La configuracion no es un manifiesto de descarga: `publication_reference` conserva conteos consultados durante la planificacion, no prueba que exista una copia local.

## Unidad, tipos y capas

La unidad es un incidente CAD identificado por `incident_id`, no una ambulancia, paciente o trayecto. La ventana es `[2026-04-01, 2026-07-01)` en hora local de Nueva York. El piloto usa `[2026-04-01, 2026-04-08)` y solo valida el proceso tecnico.

**Raw:** respuestas originales por pagina JSON comprimida, sin filtrar por validez o indicadores. Conservar campos ausentes y valores originales. Cada pagina tiene consulta, conteo, hash y referencia de origen en el manifiesto. No sobrescribir una extraccion existente.

**Interim:** filas normalizadas con los 26 campos del diccionario, `snapshot_id`, `source_page`, `source_row`, `quality_flags` y clasificacion. Campos API ausentes en una fila se materializan como `null`; la desaparicion de una columna del esquema es un error contractual. Un valor obligatorio nulo/invalido va a cuarentena; no se crea un ID ni una fecha sustituta.

**Processed:** una fila por ID aceptado, columnas originales normalizadas, variables derivadas y pertenencia a cohortes. La tabla de cuarentena conserva todas las variantes conflictivas y sus motivos. ID, severidad, tipos, ZIP y codigos se conservan como texto, incluidos ceros iniciales. Numeros no finitos o imposibles son nulos con bandera; nunca cero por defecto.

Las fechas `local_datetime` son ISO sin offset de origen. Guardar su texto en raw y la interpretacion `America/New_York` en el manifiesto; la zona es una convencion pendiente de confirmacion del publicador. Cualquier exportacion UTC explicita conversion y offset. Horas locales ambiguas/inexistentes se ponen en cuarentena, sin elegir automaticamente una ocurrencia.

## Reglas de calidad y cohortes

Orden contable excluyente: fila no interpretable -> duplicado exacto redundante -> ID conflictivo -> registro aceptado. En cada paso se retiran las filas ya clasificadas. Conservar motivos secundarios para auditoria, pero usar una sola razon principal para reconciliar conteos.

En registros aceptados, clasificar por este orden: transferencia positiva, standby positivo, evento especial positivo, indicadores de elegibilidad desconocidos, principal. Las primeras tres clases pueden tener otras banderas positivas; esas superposiciones siguen disponibles en columnas originales. Principal requiere los tres indicadores explicitamente negativos, una vez verificado su mapeo. Desconocido no equivale a negativo.

| Cohorte | Inclusion | Uso |
|---|---|---|
| Todas las aceptadas | ID y fecha validos dentro de ventana y sin conflicto | Reconciliar publicacion y describir exclusiones |
| Demanda principal | Transferencia, standby y evento especial negativos | Conteos de llamadas y llegadas del experimento |
| Demanda zonal | Principal y borough con correspondencia verificada | Entrenamiento y evaluacion por borough |
| Respuesta | Principal, bandera de respuesta positiva, llamada/llegada validas, segundos no negativos y concordantes | Calibracion y descripcion del tiempo a escena |
| Despacho | Principal, bandera de despacho positiva, llamada/asignacion validas y segundos concordantes | Calibracion del intervalo de asignacion |
| Transporte descriptivo | Registros aceptados con salida/llegada hospitalaria coherentes | Intervalos de transporte por clase; no inferir hospital destino |

Retener `held_indicator` y `reopen_indicator` en la principal para no borrar episodios de espera. Tiempos invalidos no eliminan por si solos una llamada de demanda. Borough desconocido se mantiene en el total ciudad; no se sustituye con ZIP o dispatch area. Reportar nulos y exclusiones por dia y territorio.

Concordancia inicial: diferencia absoluta maxima de un segundo entre cantidad publicada y diferencia de timestamps. Es una regla del estudio basada en precision de segundos, no una garantia del publicador; cualquier cambio se decide con entrenamiento y queda versionado antes de prueba. Respuesta no exige validez de despacho: ambos objetivos tienen sus propios requisitos. Asignacion-a-escena requiere ambos timestamps coherentes y se audita aparte.

Retener duraciones extremas y valores cero coherentes; no imputar objetivos de respuesta ni recortarlos por percentiles del trimestre completo. Si el incidente cierra despues del limite temporal, conservar su seguimiento observado y marcar `followup_crosses_window`; seleccionar por creacion, no por cierre. Un cierre ausente no significa unidad libre.

## Procedencia de variables adicionales

Todos los 26 campos fuente son `observed` segun el CSV. `availability` describe el momento conceptual del registro, no garantiza que el API publico estuviese disponible en tiempo real. Las banderas retrospectivas definen la poblacion de analisis; no se usan como informacion futura de despacho.

| Variable derivada/propuesta | Clase | Definicion o condicion |
|---|---|---|
| `snapshot_id`, `source_page`, `source_row` | derived | Linaje de extraccion; no atributo clinico |
| `quality_flags`, `cohort`, `eligible_response`, `eligible_dispatch` | derived | Reglas anteriores, con multiples motivos y una clasificacion principal |
| `borough_normalized`, `zone_id` | derived | Normalizacion y correspondencia verificada; conservar original |
| `response_minutes` | derived | Segundos de respuesta validos / 60; nulo fuera de cohorte |
| `dispatch_seconds_derived` | derived | Primera asignacion menos llamada |
| `assignment_to_scene_seconds` | derived | Llegada menos asignacion; incluye preactivacion |
| `activation_to_scene_seconds` | derived | Llegada menos activacion si secuencia valida; proxy, no trayectoria medida |
| `scene_to_hospital_departure_seconds` | derived | Salida al hospital menos llegada a escena si ambas existen |
| `hospital_transport_seconds` | derived | Llegada hospitalaria menos salida hacia hospital |
| `followup_crosses_window` | derived | Alguna marca de seguimiento posterior al fin de ventana |
| `local_hour`, `local_day_of_week`, `is_weekend` | derived | Calendario de creacion, lunes=0 hasta domingo=6 |
| `zone_hour_count` | derived | Conteo de demanda zonal en `[hora, hora+1h)` |
| `lag_1h`, `lag_24h`, `lag_168h`, `rolling_mean_24h`, `rolling_mean_168h` | derived | Solo intervalos finalizados antes de emitir pronostico |
| `sim_time_min` | derived | Diferencia temporal real desde inicio de corrida / 60 segundos |
| `prediction`, `issued_at`, `target_start`, `target_end`, `model_id` | derived | Salida del modelo y su linaje; nunca observacion EMS |
| Limites y centroides de zonas | external | Fuente geografica versionada, pendiente de incorporar |
| Ingreso, poblacion, vulnerabilidad y quintil | external | Fuente compatible y union versionada, pendientes; inicialmente no disponibles |
| Coordenada representativa de incidente | assumed | Centroide o posicion generada, nunca ubicacion exacta observada |
| Flota, bases activas, capacidades y disponibilidad inicial | assumed | Parametros de escenario pendientes de evidencia y sensibilidad |
| Matriz de viaje entre zonas | assumed | Estimacion versionada, con insumo externo si se incorpora red vial |
| Hospital simulado y liberacion de ambulancia | assumed | Reglas de escenario; fuente EMS no identifica estos atributos |
| Prioridad y tipo simplificados para el motor | derived | Mapeos pendientes con respaldo; conservar codigos iniciales |

Agregar una variable exige actualizar esta clasificacion y documentar su disponibilidad. No usar la clasificacion `observed` para coordenadas generadas, quintiles supuestos, pronosticos o respuestas contrafactuales.

## Frontera con el simulador

El formato historico no es directamente `Incident` de `src/types/index.ts`. Fase 6 implementara un adaptador y fase 7 actualizara el contrato compartido para representar valores desconocidos. Hasta entonces los archivos historicos no deben pasar por el importador actual que usa coordenadas y prioridades por defecto.

Reproduccion historica: permite mostrar tiempos observados y huecos. Contrafactual: entrega a ambas politicas las mismas llegadas y atributos iniciales admitidos; respuesta, despacho y liberacion son salidas de cada corrida. Guardar referencias observadas por separado para evitar fuga de resultados futuros.

Un mapeo de severidad/tipo pendiente bloquea el adaptador que lo requiera, pero no la descarga ni el perfilado. Un quintil no disponible bloquea metricas de equidad socioeconomica; permanecen posibles comparaciones territoriales. La geografia observada publicada se usa como aproximacion de la ubicacion conocida al llamar, con esa limitacion documentada.

## Versionado y preparacion para fase 1

Cada snapshot futuro incluira hashes de configuracion, diccionario y mapeos, version de codigo, consultas sin tokens, conteos, metadatos API antes/despues y checksums por pagina. Diferenciar `study_id` estable de `snapshot_id` unico por intento. Las actualizaciones de fuente producen otra copia, no alteran un estudio congelado.

Antes de limpiar, verificar categorias reales de indicadores; antes de entrenar, verificar boroughs; antes de simular, validar mapeos y supuestos. El archivo de mapeos versiona esos pendientes sin inventar equivalencias. La fase 1 puede ejecutarse con ellos pendientes porque descarga y perfila valores originales.
