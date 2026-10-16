# Fase 8D. Sensibilidad de flota y supuestos

## Alcance

Comparacion descriptiva de las politicas tradicional y predictiva v1 con el snapshot local `20260909T040537085584Z-56d48fe7ce9b`. No introduce la politica v2 ni reubicacion; esas capacidades pertenecen a 8E. No estima valores p ni intervalos inferenciales: su revision corresponde a 8F.

El [protocolo 8C](../research/config/nyc_ems_phase8c_protocol_v1.json) se conserva. La [configuracion especifica de 8D](../research/config/nyc_ems_phase8d_sensitivity_v1.json) detalla la rejilla y los controles antes de ejecutar. Se utilizan dias de desarrollo de mayo; no se ejecuta la evaluacion final de junio ni se seleccionan modelos nuevos.

## Rejilla congelada

| Familia | Ventanas | Parametros | Escenarios | Pares |
|---|---|---|---:|---:|
| Flota historica | 18, 20 y 23 de mayo, 00:00-24:00 Nueva York | 691, 531, 400 y 300 unidades | 12 | 120 |
| Supuestos, un factor por vez | 20 de mayo, 300 unidades | Viaje entre zonas x0.8/x1.2; liberacion x0.8/x1.2; calentamiento 0/12 h | 6 | 60 |
| Demanda generada desde pronosticos | 20 de mayo | Las cuatro flotas | 4 | 40 |
| Total | Diez semillas por escenario | Dos politicas por par | **22** | **220** |

Se ejecutan **440 corridas**. Las semillas van de 12345 a 12354; cada par comparte llegadas, prioridades y componentes de servicio. Los hashes se comparan antes de aceptar el resultado. Usar la misma semilla tambien conserva los sorteos por incidente entre flotas; las variaciones de liberacion modifican deliberadamente ese componente.

Los dias corresponden a lunes, miercoles y sabado, elegidos por calendario, no por resultados favorables. Las cuatro flotas son escenarios asumidos; no representan un inventario FDNY. El control de supuestos usa el miercoles y la flota minima de la rejilla para acotar costo y examinar presion de recursos.

Las perturbaciones de +/-20% son exploratorias, no intervalos de incertidumbre estimados de datos reales. Se modifica un parametro por vez; no se ejecuta un factorial completo ni se generalizan las interacciones no exploradas.

## Medicion, calentamiento y vaciado

1. Se inicia con flota libre seis horas antes del dia medido. En los controles de calentamiento se usan cero o doce horas.
2. Las llegadas de calentamiento generan carga y pueden seguir ocupando unidades durante la medicion, pero no entran al denominador de respuestas del dia estudiado.
3. La cohorte medida comprende las llegadas del intervalo `[00:00, 24:00)`. Se procesan eventos de servicio exactamente en el corte, pero no entran llamadas nuevas de la siguiente jornada.
4. Se guardan metricas al corte. Despues se permite terminar cola y servicios hasta un limite de 1440 minutos adicionales, sin agregar llegadas.
5. Durante el vaciado, el despacho usa el pronostico de la ultima hora anterior al corte. No incorpora pronosticos emitidos despues del cierre de llegadas.
6. Se guardan metricas posteriores al vaciado y los casos que siguen sin respuesta o sin completar. El motor deja de avanzar cuando termina su agenda o alcanza el limite.

El multiplicador de viaje afecta exclusivamente el suplemento de tiempo calculado entre centroides; no cambia el tiempo base asignacion-a-escena muestreado. El multiplicador de liberacion afecta exclusivamente el residual posterior a la llegada al hospital; no modifica tiempos de escena ni agrega traslado a casos que no lo requieren.

## Indicadores y denominadores

| Indicador | Definicion |
|---|---|
| Respuesta media y P90 | Sobre llegadas de la cohorte medida cuya llegada a escena ya es conocida, al corte o tras vaciado segun la columna |
| Sin respuesta | Llamadas sin llegada a escena, incluyendo pendientes y unidades en ruta |
| Pendiente de despacho | Llamadas sin unidad asignada; incluye el plazo fijo de preparacion |
| Sin completar | Incluye todos los estados anteriores a liberar la unidad; no equivale a sin respuesta |
| Cumplimiento <=8 min entre respondedores | Casos con respuesta <=8 min divididos por respuestas conocidas |
| Cumplimiento <=8 min entre todas las llegadas | Casos conocidos <=8 min divididos por toda la cohorte; cota inferior si faltan respuestas |
| Utilizacion temporal | Intervalos ocupados recortados a las 24 horas medidas, divididos por flota x 1440 min |
| Resultados por borough | Cohorte medida de cada zona, conservando cantidades y respuestas faltantes |

Una respuesta desconocida se guarda como ausente, nunca como cero. Si un subconjunto no contiene respuestas, su media y P90 son nulos. Las tablas conservan precision de calculo; el redondeo se aplica al informe.

El resumen por escenario promedia diez replicas. El resumen historico por flota promedia con el mismo peso cada dia y semilla; por tanto, su P90 es una media de P90 por corrida, no el percentil de una union de incidentes. Las bandas graficas representan minimo-maximo observado, no intervalos de confianza.

## Implementacion

- [Motor](../backend/app/services/ems_simulator.py): multiplicadores validados, vaciado limitado y pronostico congelado al corte.
- [Ejecutor](../research/experiments/fleet_sensitivity.py): escenarios, metricas por cohorte, comprobacion de emparejamiento, persistencia y reanudacion.
- [Visualizacion](../research/visualization/fleet_sensitivity.py): seis figuras PNG/SVG, informe y lectura especifica de cada figura.
- [Pruebas del motor](../backend/tests/test_ems_simulator.py) y [pruebas de sensibilidad](../research/tests/test_fleet_sensitivity.py): cola, vaciado, conservacion de entradas, cohortes, denominadores, utilizacion y deteccion de artefactos alterados.

La seleccion de ambulancia se acelero usando un representante por zona. Es equivalente a la regla v1 anterior: todas las unidades de una zona tienen la misma puntuacion y se conserva el desempate por menor ID. Una futura politica con posicion individual debe revisar esta equivalencia.

Los parametros por defecto siguen siendo multiplicadores 1 y corte sin vaciado en las corridas normales de la app. El calentamiento/vaciado se ejecuta en este lote de investigacion. La integracion visual de estos controles pertenece a 8G.

## Persistencia y reanudacion

Cada lote reside en `reports/nyc_ems/<snapshot>/phase8d/<hash>/`. El identificador depende de configuracion, codigo, entradas y versiones de entorno. El manifiesto almacena un hash por resultado; cada resultado verifica tambien su Parquet de incidentes.

La escritura usa archivos temporales y reemplazo atomico. Un par solo se declara completado despues de guardar y verificar sus resultados. Si se interrumpe entre escritura y actualizacion del manifiesto, ese par se vuelve a ejecutar; los pares registrados correctamente se reutilizan. La reanudacion explicita rechaza cambios de entradas/configuracion/codigo/entorno o archivos alterados.

No ejecutar dos controladores sobre la misma carpeta al mismo tiempo. La concurrencia interna se gestiona mediante `--workers`; cada proceso guarda pares distintos y el controlador actualiza el manifiesto.

## Comandos

Desde la raiz, con dependencias de backend y research instaladas:

```powershell
python -m research.experiments.fleet_sensitivity --workers 2
```

Si se interrumpe, ejecutar el mismo comando reutiliza el lote correspondiente al mismo codigo/configuracion. Para indicar el lote explicitamente:

```powershell
python -m research.experiments.fleet_sensitivity --workers 2 --resume reports/nyc_ems/20260909T040537085584Z-56d48fe7ce9b/phase8d/583b13134c76f924dffd
```

Para una comprobacion parcial, `--limit-pairs 2` ejecuta solo dos pares pendientes y deja el estado `partial`. Las figuras solo se generan cuando se completan todos los pares de la rejilla. Una ejecucion parcial no debe presentarse como cierre de fase.

## Artefactos

- `manifest.json` y `config.json`: procedencia, configuracion y estado del lote.
- `scenario_matrix.csv`: todos los escenarios previstos.
- `pairs/*.json`: resultados por politica, diferencias pareadas y comprobaciones.
- `pairs/*.parquet`: tiempos, unidades asignadas, estados al corte y tras vaciado por incidente, con bandera de cohorte medida.
- `tables/run_metrics.csv`: resultados por corrida con denominadores.
- `tables/by_zone_metrics.csv`: resultados por borough.
- `tables/paired_differences.csv`: diferencias descriptivas por par.
- `tables/scenario_summary.csv`: resumen por escenario y numero de replicas.
- `tables/historical_fleet_summary.csv`: resumen de flota usando solo llegadas historicas.
- `tables/artifact_interpretation.csv`: interpretacion especifica y limites por figura.
- `figures/`: respuesta, pendientes, utilizacion, supuestos, fuentes de demanda y boroughs, en PNG y SVG.
- `SENSITIVITY_REPORT.md`: informe con cifras y figuras incrustadas.

No se sobrescriben reportes anteriores de 8C/8, no se inicia el servidor y no se actualiza el articulo automaticamente. Los datos de mayo sirven para desarrollo; resultados nulos o adversos se conservan junto con los favorables.
