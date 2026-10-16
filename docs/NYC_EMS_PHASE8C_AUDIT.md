# Fase 8C. Auditoria del motor y protocolo experimental

Fecha local de trabajo: 2026-09-28 (America/Lima). Ejecuciones archivadas con fecha UTC.

Estado: auditoria tecnica implementada y ejecutada; habilita el desarrollo de 8D. La inferencia final sigue bloqueada por los hallazgos asignados a 8D/8F, no por un fallo de ejecucion del motor.

## 1. Alcance y evidencia

Se auditaron `EMSSimulator`, el servicio de comparaciones, la construccion de variables/pronosticos y los calculos estadisticos CRISP-DM. Se utilizaron los artefactos locales del snapshot `20260909T040537085584Z-56d48fe7ce9b`, sin descargas ni cambios a los datos originales.

Implementacion: [ejecutor de auditoria](../research/experiments/audit_phase8c.py), [protocolo versionado](../research/config/nyc_ems_phase8c_protocol_v1.json), [motor](../backend/app/services/ems_simulator.py) y [pruebas](../backend/tests/test_ems_simulator.py).

Ejecucion de cierre: `20260929T031934524970Z`. [Resumen generado](../reports/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase8c/20260929T031934524970Z/AUDIT_SUMMARY.md) y [evidencia JSON](../reports/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase8c/20260929T031934524970Z/audit_summary.json). Resultado: **94 controles tecnicos aprobados**, **17 pruebas de backend** y **18 pruebas del pipeline** aprobadas.

Cada ejecucion escribe en `reports/nyc_ems/<snapshot>/phase8c/<UTC>/`:

- `protocol.json`: copia exacta del protocolo usado.
- `audit_summary.json` y `AUDIT_SUMMARY.md`: controles y resultados, sin valores p sobre estas corridas diagnosticas.
- `<caso>/<politica>_decisions.jsonl.gz`: todas las decisiones, sin el limite de 120 eventos de la pantalla.
- `<caso>/<politica>_incidents.jsonl.gz`: llegadas, componentes de servicio, asignaciones, estados y tiempos de todos los incidentes.
- `artifact_sha256.json`: hashes de las salidas; el resumen incluye tambien hashes de entradas/codigo y versiones de dependencias.

Las carpetas generadas quedan fuera de Git conforme al `.gitignore` existente. Este documento, el protocolo, las pruebas y el ejecutor si son versionables. No se sobrescribe `phase8/paired_experiment_results.json` ni se reemplazan tablas del articulo.

## 2. Por que coincidian las politicas

El despacho tradicional minimiza tiempo estimado. La politica predictiva v1 minimiza:

```text
tiempo_estimado + 2 * demanda_pronosticada_zona_origen / unidades_libres_zona_origen
```

El factor 2 es un peso heuristico de puntuacion, no un parametro estimado ni una conversion fisica validada. El desempate usa el ID de ambulancia. Las unidades de una misma zona tienen el mismo tiempo estimado y la misma penalizacion; sus coordenadas visuales no modifican ese calculo.

Con suficientes unidades libres en la zona del incidente, la penalizacion puede no compensar el tiempo adicional de traer una unidad de otra zona. Por tanto, ambas politicas eligen exactamente lo mismo. No hay reubicacion preventiva en v1.

### Control historico de referencia

16 de mayo de 2026, 00:00-12:00 Nueva York; modelo `hist_gradient_boosting_v1`; semilla 12345; 691 unidades asumidas.

| Indicador | Tradicional | Predictiva v1 |
|---|---:|---:|
| Llegadas | 1753 | 1753 |
| Despachos al corte | 1750 | 1750 |
| Respuestas conocidas al corte | 1711 | 1711 |
| Servicios completados | 1514 | 1514 |
| Servicios sin completar | 239 | 239 |
| Respuesta media, min | 11.709147 | 11.709147 |
| Utilizacion temporal | 0.224520 | 0.224520 |
| Despachos entre zonas | 0 | 0 |

En **1750 despachos comunes hubo cero elecciones diferentes y cero respuestas diferentes**. Ningun despacho espero mas que los 0.5 minutos fijos de preparacion. Los tres incidentes pendientes al corte no demuestran saturacion: aun no habian superado ese plazo de preparacion.

La cifra 11.709147 corresponde a una semilla. No reemplaza la media 11.591 previamente publicada para diez replicas; tienen presupuestos de ejecucion distintos.

### Control de escasez

La misma ventana y semilla con 100 unidades es un control diagnostico de una condicion ya mencionada en el informe anterior; no es una propuesta de flota real.

| Indicador | Tradicional | Predictiva v1 |
|---|---:|---:|
| Llegadas | 1753 | 1753 |
| Despachos | 855 | 857 |
| Respuestas conocidas | 819 | 833 |
| Pendientes sin despacho | 898 | 896 |
| Respuesta media condicionada a llegada a escena, min | 84.133543 | 82.766024 |

Hubo 767 elecciones de ambulancia diferentes entre 850 incidentes despachados por ambas politicas. De 815 incidentes con respuesta en ambas, 717 tuvieron respuestas distintas. Cuatro tuvieron respuesta solo en tradicional y 18 solo en predictiva al corte.

El registro contrasta tambien las dos reglas sobre **el mismo estado**: hubo 16 elecciones potencialmente diferentes en la trayectoria tradicional y 26 en la predictiva. Esto difiere de los 767 cambios entre corridas porque una decision distinta altera la disponibilidad posterior y produce trayectorias distintas.

Este control demuestra que las politicas no son identicas por construccion. No permite afirmar superioridad: una sola replica y subconjuntos distintos de respuestas no justifican esa conclusion.

### Control de demanda pronosticada

Con 691 unidades y dos horas, ambas politicas recibieron 337 llegadas generadas identicas, despacharon 335 incidentes y registraron 295 respuestas. Los tiempos de servicio y las decisiones tambien coincidieron. Esto comprueba emparejamiento para demanda generada; no valida que las llegadas sinteticas sean lo realmente ocurrido.

## 3. Controles temporales y operativos

La auditoria verifico 16560 filas de pronosticos y 10920 celdas zona-hora. Se comprobaron claves unicas, etiquetas compartidas entre modelos, horizonte de una hora y entrenamiento terminado antes de emitir el pronostico.

Se recalcularon rezagos 1/24/168 horas y medias/sumas moviles 24/168 horas usando exclusivamente observaciones previas. Coincidieron con el panel y con las variables del panel listo para modelar. Este control verifica cronologia retrospectiva; no acredita que la fuente publique incidentes con latencia suficiente para operacion en vivo.

Las dos politicas recibieron las mismas llegadas, prioridades y componentes de servicio por incidente, comprobados mediante hashes. La aleatoriedad de servicio depende de `semilla + identificador del incidente`, por lo que una decision distinta no cambia el muestreo de los casos siguientes.

Se comprobaron conservacion de flota, IDs unicos, asignaciones consistentes, secuencia de tiempos, componentes positivos, utilizacion entre 0 y 1, conteos al corte y reproduccion en pasos de 60 minutos. Los tiempos de respuesta se reconciliaron con espera desde la llamada mas el componente de viaje registrado en la decision. No se suma el tiempo de respuesta historico completo a la cola simulada.

Se ejecutaron nueve corridas: tres casos por dos politicas, mas una repeticion por pasos de la politica predictiva en cada caso. Los controles no constituyen validacion clinica ni acreditan todas las combinaciones posibles de parametros.

## 4. Correcciones y registro incorporados

- Se rechazan pronosticos duplicados por modelo/hora/zona, horizontes invalidos, valores no finitos/negativos y procedencia temporal ausente o incompatible.
- La cobertura se verifica por conjunto de zonas, evitando que un duplicado encubra una zona faltante.
- El baseline mostrado por el motor tambien respeta `issued_at`; una fila futura no se incorpora al estado actual.
- La hora de llamada conserva precision de origen durante el calculo; antes se redondeaba a dos decimales antes de restarla. Los resultados nuevos pueden diferir ligeramente de los archivados, que se conservan.
- `audit_decisions=True` registra alternativas por zona, cantidades disponibles, puntuaciones, eleccion de ambas reglas y unidad seleccionada. Es opcional, no se activa en la UI ni altera las decisiones. La compresion por zona es exacta para v1 porque sus unidades empatan en puntuacion; debe revisarse si v2 usa posicion individual.

## 5. Inventario de supuestos

| Elemento | Procedencia y comportamiento actual | Limite / accion |
|---|---|---|
| Fecha y zona de incidentes historicos | Cohorte local del dataset | No son GPS individuales; zonas desconocidas se contabilizan aparte |
| Demanda prevista | Modelos congelados, seleccion por validacion | Pronosticos retrospectivos de una hora, actualizados con pasado observado |
| Flota 691 | Proxy de capacidad del paquete Fase 6 | No inventario FDNY; 8D compara 691/531/400/300 |
| Distribucion inicial | Reparto circular entre bases; todas libres | Arranque frio; controlar calentamiento en 8D |
| Preparacion | 0.5 min por incidente | Constante asumida, no tiempo de despacho individual observado |
| Viaje dentro de zona | Muestra de asignacion-a-escena del entrenamiento por zona | Incluye activacion, no solo conduccion; no condicionado a prioridad/hora |
| Viaje adicional entre zonas | Distancia entre centroides a 38 km/h | No red vial; aditivo sobre muestra observada, someter a sensibilidad |
| Escena y transporte | Muestra de entrenamiento; faltantes con 25/12 min; viaje faltante 10 min | Imputaciones del motor, no datos observados del incidente actual |
| Liberacion con traslado | Maximo entre 10 min y cierre proxy menos viaje/escena/transporte; cierre faltante 80 min | El cierre desde llamada incluye otras esperas; no identifica entrega hospitalaria real |
| Sin traslado | Liberacion despues de escena; no aplica residual de cierre | Supuesto distinto al de transportados; revisar sensibilidad |
| Valores temporales cero | La regla existente `valor or fallback` usa el fallback para cero; piso 0.1 min | Documentar y evaluar en 8D antes de modificar calibracion |
| Necesidad de traslado | Muestreada del entrenamiento por zona | No destino/traslado observado del incidente de evaluacion |
| Ubicaciones y hospitales | Aproximaciones del escenario | No camas, trafico ni rutas GPS reales |
| Penalizacion predictiva | Peso 2, demanda dividida por libres | Heuristica sin optimizacion; v2 se versionara en 8E |
| Corte | Fin fijo, sin calentamiento ni vaciado | Medias de respuestas conocidas; pendientes y activos permanecen en denominadores descriptivos |

La sensibilidad futura debe justificar sus rangos antes de ejecutar la comparacion final; no se interpreta un parametro proxy como estimacion identificada del sistema real.

## 6. Hallazgos que bloquean la inferencia final

| Hallazgo | Consecuencia | Fase de cierre |
|---|---|---|
| Prueba t de politicas usa colas normales | Los valores p no corresponden a Student con grados de libertad finitos | 8F |
| Wilcoxon propio omite correccion por empates | Aproximacion no suficientemente justificada; revisar ceros y muestras pequenas | 8F |
| Diferencia constante no nula produce infinito | Estadistico no serializable como JSON estricto; definir resultado no estimable | 8F |
| Deltas redondeados antes de inferencia | Puede ocultar pequenas diferencias o crear empates | 8F |
| Bootstrap de modelos remuestrea filas zona-hora independientes | No preserva dependencia espacial/temporal; revisar unidad y bloques | 8F |
| Sin correccion por comparaciones multiples | No tratar todas las comparaciones como una unica prueba primaria | 8F |
| `dropna` por modelo antes de restar arrays | Los pares pueden desalinearse si cambian artefactos; los actuales estan completos | 8F |
| Media de respuesta al corte con casos distintos | Una diferencia puede reflejar censura/composicion; informar pendientes y vaciado | 8D/8F |
| Campos legacy de equidad/R2 en cero y baseline mal etiquetado | En comparaciones historicas, ausencia no equivale a cero; baseline usa validacion del modelo seleccionado | 8F/8G |
| Persistencia Fase 8 sobrescribe su mismo archivo | Necesita resultados por experimento y procedencia completa | 8D |

El JSON de auditoria incluye controles numericos artificiales contra SciPy para mostrar las diferencias de calculo. Son pruebas de software, nunca participantes ni evidencia empirica del articulo.

Los resultados de comparaciones existentes conservan su valor descriptivo, pero sus valores p no se declaran evidencia robusta definitiva. Los defectos estadisticos quedan explicitamente bloqueados para el cierre del articulo; no se corrigen silenciosamente ni se cambian sus resultados archivados en esta fase.

## 7. Protocolo congelado para continuar

La version JSON fija ventanas de desarrollo (18, 20 y 23 de mayo), dias de evaluacion (1-7 de junio), modelo, flotas, semillas, direcciones de diferencias y reglas de corte. Su congelamiento es local y posterior a resultados ya vistos; no es un preregistro ni restaura junio como prueba independiente.

Para 8D/8F se especifican medicion de 24 horas, calentamiento de 6 horas (sensibilidad 0/12), vaciado maximo de 24 horas y reporte de casos sin resolver. Esas capacidades estan **planificadas y aun no implementadas**: las corridas de 8C preservan el corte antiguo para diagnosticarlo.

Se fija un piloto de costo de 10 replicas y evaluacion de 30 por dia/escenario, sin detener por significancia. Cualquier revision por costo debe crear otra version antes de evaluar v2. El emparejamiento comparte llegadas y componentes exogenos; las comparaciones de dias deben conservar su dependencia temporal y la estructura de replicas.

La comparacion primaria prevista es tradicional frente a v2 en respuesta media, reportada junto con completitud; v1 y las ablaciones son comparaciones secundarias. No se afirmara superioridad basandose solo en respondedores cuando queden casos sin resolver. Antes de 8F se congelaran ademas los parametros concretos de v2 y el detalle implementable del analisis por bloques.

Junio ya fue consultado. Las nuevas decisiones adaptadas a este trimestre son exploratorias; una confirmacion independiente exige un periodo nuevo reservado. No se ampliara el dataset automaticamente.

## 8. Reproduccion y criterio de cierre

Desde la raiz, con dependencias de `backend/requirements.txt` y `research/requirements.txt` instaladas:

```powershell
python -m research.experiments.audit_phase8c
python -m unittest discover -s research/tests -v
```

Pruebas del backend desde `backend/`:

```powershell
python -m unittest discover -s tests -v
```

No se requiere levantar frontend ni servidor. La auditoria devuelve codigo distinto de cero si falla un control tecnico. `formal_inference_ready=false` conserva visibles los bloqueos metodologicos aun cuando los controles tecnicos pasen.

La fase 8C cierra el diagnostico y deja evidencia para continuar con **8D: sensibilidad de flota y supuestos**. No cierra las correcciones estadisticas de 8F ni implementa la politica v2.
