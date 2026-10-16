# Plan de cierre: simulacion, evaluacion e investigacion NYC EMS

Fecha: 2026-09-28. Estado: fase 8C ejecutada; 8D-11 pendientes. [Auditoria, resultados y bloqueos para inferencia final](NYC_EMS_PHASE8C_AUDIT.md).

Complementa el [plan original](PLAN_IMPLEMENTACION_NYC_EMS_2026.md). Conserva las fases realizadas y la fase 9 dedicada a instrumentos. Las nuevas fases 8C-8G amplian la evaluacion existente; no sustituyen sus resultados.

## 1. Punto de partida y objetivo

Existe una base funcional con datos locales NYC EMS, limpieza, variables temporales, tres modelos, simulador SimPy, FastAPI, frontend, asistente LangGraph, experimentos pareados y visualizaciones CRISP-DM. El cierre propuesto busca una entrega academica reproducible y coherente entre software y articulo.

La comparacion reportada con 691 unidades produjo diferencias nulas entre politicas. Se investigara su causa: disponibilidad, decisiones equivalentes, supuestos o implementacion. El exito de este plan se mide por la validez y reproducibilidad de la evaluacion, no por obtener una ventaja predictiva.

La flota, posiciones de unidades y tiempos entre zonas contienen supuestos. El sistema sigue siendo una simulacion retrospectiva por zonas, sin GPS operativo ni evidencia de impacto clinico real. Este plan no convierte el prototipo en un sistema de despacho de emergencias en produccion.

## 2. Fases de implementacion

### Fase 8C. Auditoria del motor y congelamiento del protocolo

**Estado:** implementada y ejecutada. Incluye trazas de decisiones, controles con datos locales, pruebas de invariantes y protocolo versionado. Se habilita 8D; los hallazgos estadisticos/de censura documentados bloquean conclusiones finales hasta 8D/8F.

**Objetivo:** determinar por que las politicas coinciden y fijar una base verificable para los nuevos experimentos.

- Revisar cola, despacho, reserva de demanda, estados de ambulancias, tiempos de servicio y conteos al cierre.
- Registrar decisiones: unidad elegida, alternativas, componentes de puntuacion y diferencias entre politicas para el mismo incidente.
- Comprobar emparejamiento de llegadas y aleatoriedad por incidente/componente, disponibilidad temporal de pronosticos y reproduccion por semilla.
- Inventariar el origen de cada parametro; distinguir flota asumida de recursos observados y demanda historica de demanda generada.
- Auditar las pruebas estadisticas existentes. La comparacion de politicas documenta valores p aproximados; la comparacion de modelos debe revisar dependencia temporal y alineacion de pares.
- Congelar metrica primaria, comparaciones, ventanas, reglas de corte/vaciado, calentamiento y presupuesto de ejecucion antes de comparar la nueva politica.
- Registrar que junio ya fue consultado. Los analisis adaptados a esos resultados seran exploratorios; una confirmacion independiente necesita un periodo nuevo reservado.

**Entregables:** informe de auditoria, protocolo versionado, registro de decisiones y pruebas de invariantes del motor.

**Cierre:** se puede explicar con evidencia cuando ambas politicas eligen lo mismo; no hay fuga temporal ni duplicacion de tiempos detectada en los casos auditados. Los defectos encontrados quedan corregidos o bloquean los experimentos afectados.

### Fase 8D. Sensibilidad de flota y supuestos

**Objetivo:** medir en que condiciones cambia el comportamiento del sistema actual.

- Implementar un ejecutor por lotes con configuracion, semillas, reanudacion y salidas independientes por experimento.
- Probar inicialmente flotas de 691, 531, 400 y 300 unidades como escenarios asumidos. Justificar y congelar la rejilla antes de comparar resultados; estos numeros no representan un inventario real de NYC.
- Ejecutar ventanas comparables de distinta carga y dia de semana. Elegirlas mediante una regla documentada, no por el resultado favorable de una politica.
- Evaluar tambien incertidumbre en tiempos entre zonas y liberacion de recursos, con rangos justificados por la calibracion o identificados como supuestos exploratorios.
- Registrar respuesta media, P90, cumplimiento del umbral de analisis, cola, incidentes no atendidos, utilizacion y resultados por borough.
- Separar escenarios con llegadas historicas de escenarios generados desde pronosticos. La evaluacion principal de politicas usara demanda historica comun; la demanda pronosticada servira como sensibilidad.

**Entregables:** matriz de escenarios, resultados por corrida y resumen con curvas de flota frente a respuesta y pendientes.

**Cierre:** se reproducen todos los escenarios configurados y se identifican condiciones de holgura o saturacion sin seleccionar solo resultados favorables.

### Fase 8E. Politica predictiva v2 y reubicacion preventiva

**Objetivo:** convertir pronosticos en decisiones operativas explicitas y auditables.

- Conservar tradicional y predictiva v1 como comparadores versionados.
- Disenar una politica v2 que calcule necesidades por zona con pronosticos disponibles en el reloj de simulacion y disponibilidad actual de recursos.
- Incorporar reubicacion de unidades libres desde zonas con excedente hacia zonas deficitarias, con reserva minima y limites de movimiento.
- Representar traslado, tiempo, costo aproximado y disponibilidad durante la reubicacion. Definir si una unidad en traslado puede ser redirigida a un incidente.
- Evitar movimientos repetidos entre zonas mediante umbrales y tiempos minimos; ajustar parametros solo en ventanas de desarrollo.
- Comparar por ablacion despacho predictivo sin reubicacion y despacho con reubicacion para distinguir sus aportes.
- Guardar motivo, origen, destino, pronostico utilizado y efecto sobre cobertura de cada movimiento.

**Entregables:** politica v2 configurable, eventos de reubicacion, contrato API actualizado y pruebas de conservacion de flota, estados y reproducibilidad.

**Cierre:** una prueba controlada demuestra que las decisiones responden a la demanda prevista sin usar futuro, duplicar unidades ni moverlas instantaneamente. No se exige mejora en la metrica para aprobar la implementacion.

### Fase 8F. Evaluacion estadistica y cierre experimental

**Objetivo:** producir evidencia defendible sobre modelos y politicas.

- Ejecutar tradicional, predictiva v1 y v2 con llegadas y condiciones exogenas comunes por escenario. Incluir las ablaciones fijadas en el protocolo.
- Revisar las pruebas aproximadas actuales y usar implementaciones estadisticas verificadas con tratamiento de ceros, empates y varianza nula.
- Para errores de pronostico, definir bloques temporales y conservar juntas las zonas de una misma unidad temporal al remuestrear; revisar sensibilidad a longitud de bloque.
- Para politicas, distinguir variabilidad entre dias y entre replicas condicionadas a las mismas llegadas. No tratar incidentes dependientes como replicas independientes.
- Reportar diferencias en unidades originales, intervalos de confianza, tamanos del efecto definidos y valores p cuando sus supuestos sean defendibles. Aplicar correccion por comparaciones multiples a las familias especificadas.
- Fijar el presupuesto final por precision y costo medidos en un piloto, no detener las ejecuciones cuando aparezca significancia.
- Registrar tiempos de entrenamiento, inferencia y simulacion medidos, junto con entorno y versiones.
- Mantener la seleccion del modelo por validacion temporal; no sustituirla por el ganador de la prueba ya observada. Documentar la relacion entre la busqueda CRISP-DM y el modelo realmente consumido por el motor.

**Entregables:** resultados completos por escenario, tablas estadisticas, informe de sensibilidad y conclusiones por pregunta de investigacion.

**Cierre:** otra ejecucion reproduce las tablas dentro de tolerancias declaradas; los resultados nulos, negativos y las limitaciones de inferencia quedan incluidos.

### Fase 8G. Integracion de resultados y explicaciones en la app

**Objetivo:** que las pantallas muestren y expliquen los nuevos experimentos con la misma evidencia del articulo.

- En Simulacion, mostrar politica/version, flota asumida, demanda de entrada y estados de reubicacion, con representacion 2D/3D acorde al motor.
- En Experimentos, integrar sensibilidad de flota, comparaciones de politicas, intervalos y resultados territoriales.
- En Prediccion de Demanda y CRISP-DM, consolidar al menos seis tablas y seis figuras pertinentes, reutilizando las existentes cuando respondan a las preguntas del estudio.
- Dar a cada tabla/figura titulo, unidades, periodo, poblacion, fuente, interpretacion especifica y limites. Distinguir lectura de resultados de explicacion del modelo; evitar textos genericos repetidos.
- Conectar el asistente a las nuevas versiones y resultados, con evidencia identificable y respuestas que reconozcan resultados nulos.
- Probar escritorio y movil, estados sin resultados, exportacion y correspondencia entre cifras de API, pantalla y reportes.

**Entregables:** vistas actualizadas, exportaciones y pruebas de integracion/visualizacion.

**Cierre:** las decisiones y metricas visibles coinciden con la corrida seleccionada; cada interpretacion corresponde al artefacto mostrado.

### Fase 9A. Preparacion de instrumentos y analisis

**Objetivo:** dejar listo el material para evaluar utilidad percibida e interpretacion de resultados.

- Definir dimensiones, poblacion, criterios de participantes y tareas representativas; justificar su relacion con las preguntas del articulo.
- Redactar cuestionario Likert, test de interpretacion con clave de respuestas y ficha de jueces para claridad, pertinencia y relevancia.
- Preparar consentimiento, identificadores anonimos, plantillas de captura, reglas para faltantes e items invertidos y plan de revision/piloto.
- Implementar validacion de entradas y scripts para V de Aiken, alfa por dimension y KR-20, con intervalos y casos no calculables documentados.
- Probar los scripts con ejemplos artificiales identificados exclusivamente como pruebas tecnicas.

**Entregables:** instrumentos versionados, guia de aplicacion, plantillas y scripts. Reutiliza EMS-020/EMS-021 del plan original.

**Cierre:** los materiales estan listos para revision por expertos y aplicacion piloto; los ejemplos de prueba no se presentan como evidencia del estudio.

### Fase 9B. Aplicacion con expertos y participantes

**Objetivo:** obtener evidencia real de los instrumentos.

- Gestionar revision etica o determinacion institucional que corresponda, consentimiento y convocatoria a cargo del equipo investigador.
- Recoger valoraciones de jueces, revisar instrumentos y realizar piloto antes de congelar la version final.
- Recoger respuestas reales, ejecutar los analisis e informar exclusiones, incertidumbre y cambios de version.
- Interpretar estos coeficientes como evidencia sobre instrumentos; no como validacion del pronostico ni del simulador.

**Entregables:** respuestas protegidas, resumen anonimizado y reporte de instrumentos.

**Cierre:** existen participantes y valoraciones reales trazables bajo el protocolo. Esta fase depende del equipo humano y no puede completarse generando encuestas artificiales.

### Fase 10. Reproducibilidad y entrega del software

**Objetivo:** que otro integrante reproduzca el estudio en un entorno limpio.

- Consolidar dependencias y comandos de datos, entrenamiento, simulacion, experimentos y figuras; reutilizar los comandos existentes.
- Crear un comando orquestador y un entorno reproducible, con Docker cuando resulte compatible con las dependencias del proyecto.
- Congelar configuraciones, versiones, manifiestos y hashes de datos/modelos/resultados; distinguir regeneracion desde el snapshot y nueva descarga desde una fuente mutable.
- Probar instalacion, pruebas automatizadas y reproduccion de una ejecucion de referencia, registrando recursos y tolerancias.
- Preparar paquete compartible, revisar licencias y excluir secretos y respuestas personales. Publicar repositorio o DOI solo cuando el usuario autorice y exista un destino real.

**Entregables:** README de replicacion, entorno fijado, automatizacion y manifiesto de entrega.

**Cierre:** otro entorno reproduce la ejecucion de referencia y puede localizar todos los artefactos citados.

### Fase 11. Reporte general y articulo final

**Objetivo:** cerrar la documentacion con resultados verificables y consistentes.

- Generar el reporte general solicitado: que hace el sistema, origen de datos, modelos, supuestos, escenarios, resultados, interpretacion y limites.
- Actualizar una nueva version del articulo conservando el contenido original y referencias existentes; introducir solo cambios necesarios y referencias adicionales justificadas.
- Integrar resultados definitivos, figuras, tablas, amenazas a la validez y respuestas a las preguntas de investigacion.
- Vincular cada cifra/figura a su artefacto reproducible y documentar protocolo exploratorio frente a confirmatorio.
- Incorporar los instrumentos solo con el alcance realmente ejecutado. Si falta 9B, dejar explicita esa limitacion y acordar el alcance del manuscrito con el asesor.
- Revisar declaraciones de IA, etica, financiamiento y conflictos con informacion confirmada por los autores; comprobar el checklist editorial sin afirmar cumplimiento de requisitos sin evidencia.

**Entregables:** reporte general, nueva version DOCX preservando el avance, figuras de publicacion, anexos y matriz de evidencia del checklist.

**Cierre:** software y manuscrito reportan los mismos resultados; no se atribuyen mejoras operativas reales ni evaluaciones humanas inexistentes. La calidad editorial no garantiza aceptacion Q1.

## 3. Orden y dependencias

Ruta principal: **8C -> 8D -> 8E -> 8F -> 8G -> 10 -> 11**.

La fase 9A puede comenzar en paralelo tras fijar objetivos en 8C. La fase 9B requiere instrumentos revisados y una version estable de las tareas del software, preferiblemente despues de 8G. Su reporte se incorpora a 11 si forma parte del alcance final. La documentacion de reproducibilidad se mantiene durante todas las fases aunque se verifique formalmente en 10.

| Hito | Fases | Resultado verificable |
|---|---|---|
| Diagnostico experimental | 8C-8D | Explicacion trazable de diferencias nulas y sensibilidad del motor actual |
| Evaluacion ampliada | 8E-8F | Politica versionada y comparacion reproducible con incertidumbre |
| Software academico integrado | 8G, 10 | Pantallas consistentes y ejecucion replicable |
| Instrumentos preparados | 9A | Formularios y analisis listos para aplicar |
| Evaluacion humana | 9B | Datos reales de jueces/participantes y analisis |
| Cierre documental | 11 | Reporte general y articulo respaldados por artefactos |

## 4. Limites y prioridades

Podemos implementar ahora 8C-8G, 9A, 10 y la parte de 11 respaldada por evidencia disponible. La fase 9B requiere colaboracion de expertos/participantes y decisiones institucionales del equipo.

No se programan por ahora nuevos modelos, mas datos, clima, GPS real, uso clinico, despliegue multiusuario ni transferencia a Trujillo. Un periodo nuevo reservado se incorporaria solo si se decide una evaluacion confirmatoria adicional. La prioridad inmediata tras la auditoria 8C es **8D: sensibilidad de flota y supuestos**, respetando los bloqueos identificados.
