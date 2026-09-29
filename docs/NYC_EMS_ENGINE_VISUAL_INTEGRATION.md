# Motor EMS y visualizacion NYC

## Alcance implementado

Ampliacion de las fases 6-7: FastAPI conserva un motor de eventos discretos
SimPy durante la corrida. Cada llegada entra en cola, recibe una unidad disponible,
alcanza escena, recibe atencion y, cuando corresponde, traslado y entrega hospitalaria.
La liberacion permite despachar la siguiente llamada. La flota no se limita por motivos visuales.

Dos entradas comparten el motor:

- `demand_source: historical`: tiempos de llegada, zona, tipo y prioridad del historico.
  La atencion posterior es contrafactual; no es una reconstruccion de las operaciones FDNY.
- `demand_source: forecast`: conteo Poisson por zona/hora con media igual al pronostico;
  llegadas uniformes dentro de esa hora; tipo/prioridad muestreados del entrenamiento.
  IDs `SYN-...`. No se utilizan los conteos reales de validacion/prueba para generar llegadas.

Los pronosticos son retrospectivos, emitidos hora a hora con rezagos observados.
Una corrida de 12 horas NO equivale a un pronostico de 12 horas emitido al inicio.
No se utiliza una fila de pronostico emitida despues de su hora objetivo.

## Reglas del motor v1

- Ventana de calibracion: filas anteriores al fin de entrenamiento en `temporal_partitions.json`.
  Los resumenes de fase 6 del trimestre completo no se usan como distribucion de tiempos.
- Un muestreo de filas de entrenamiento por borough conserva conjuntamente tiempos de viaje,
  escena, traslado y cierre. Ausencias: 10, 25, 12 y 80 minutos respectivamente.
  Estos valores de respaldo son supuestos; los extremos positivos no se recortan.
- Preparacion inicial del despacho: 0.5 min asumidos; la cola del motor agrega espera por escasez.
  No se agrega el tiempo historico de espera en cola de la llamada evaluada.
- Viaje: asignacion-a-escena muestreada + distancia entre centroides a 38 km/h cuando cambia
  la zona. Es una aproximacion agregada, sin red vial; las lineas visibles no son rutas GPS.
- Transferencia: bandera muestreada del entrenamiento, no resultado futuro del caso evaluado.
  Entrega hospitalaria: maximo entre 10 min y cierre menos viaje, escena y traslado.
  Cierre no identifica liberacion real. Sin traslado, la unidad se libera al terminar escena.
- Seleccion en cola: prioridad alta/media/baja, luego fecha de llamada e ID.
  El mapeo de prioridad procede del pipeline y no constituye validacion clinica.
- Tradicional: menor tiempo estimado a escena.
- Predictiva: tiempo estimado + `2 * demanda_horaria_origen / unidades_libres_origen`.
  El factor 2 es un parametro fijo de esta primera regla, no un valor optimizado.
  Los pesos/quintiles del demo no intervienen en esta politica. No hay reubicacion preventiva.
- Flota inicial libre y repartida ciclicamente entre las bases proxy. 691 es un punto de
  partida asumido, configurable; no es la flota observada de FDNY.
- Misma semilla e ID producen el mismo muestreo de servicio independientemente de politica,
  cantidad de unidades o tamano de los pasos. Los eventos exactamente en el corte se procesan.

## Contrato y limites

`POST /api/simulations` acepta los campos anteriores y `demand_source`, `start_minute`,
`duration_min` (1-1440), `num_ambulances` (1-1500), `seed`, `policy`, `model_id` y `dataset_id`.
El escenario NYC admite `dia_normal`; no aplica multiplicadores demo.
Inicio posterior al entrenamiento y fin dentro del dataset. Fuentes/modelos/horas sin
pronostico completo se rechazan para la entrada pronosticada o politica predictiva.

`POST /api/simulations/step` avanza de 1 a 1440 minutos y se detiene en el fin de corrida.
`POST /api/simulations/{run_id}/run` ejecuta todos los eventos hasta ese fin.
Cambiar politica o configuracion requiere una nueva corrida, para evitar mezclar tratamientos.
Los IDs de corridas anteriores devuelven 404.

El estado agrega `simulation` con reloj NYC, fuente de demanda, supuestos, resumen por zona,
completados/no completados, conteo de exclusiones y referencia observada independiente.
`metrics` acumula todos los incidentes llegados, no solo los visibles.
Respuesta significa llegada a escena; completado significa servicio terminado y recurso libre.
La referencia observada solo incluye registros de la cohorte de respuesta valida cuya
llegada observada ya ocurrio al corte; los resultados invalidos no se convierten en ceros.
Utilizacion es fraccion del tiempo acumulado ocupado. No se reportan camas ni equidad
socioeconomica a partir de proxies como si fueran observadas.

La API conserva **una corrida activa en memoria**, serializa mutaciones y no ofrece aislamiento
multiusuario ni persistencia de corridas. El frontend puede exportar un estado JSON con
configuracion, procedencia, indicadores y hasta 1000 incidentes priorizando los no completados.
Los 120 eventos recientes son una ventana visual, no un registro experimental completo.
Los historicos crudos y modelos permanecen en los archivos locales existentes.

## Visualizacion

La app carga el primer snapshot preparado. Controles de nueva corrida, entrada de demanda,
politica, fecha, duracion, flota, modelo, semilla, pausa, avance, velocidad y exportacion.
Al fallar la API se pausa NYC; no se cambia al demo. Reset conserva la configuracion NYC.

2D, 3D y vista dividida comparten reloj y estado. Limites oficiales DCP 26b archivados en
`public/data/nyc-boroughs.geojson`, con procedencia y hash en su README. Barras de pronostico
por borough, unidades con color por estado y trayectos esquematicos. Tabla de llegadas,
cola, servicios activos/completados, unidades libres y pronostico de la hora en curso.
Las unidades libres se agrupan por borough; las que estan en servicio se representan
individualmente. Las etiquetas mantienen tamano legible y se separan al girar la camara.

## Pendiente de fase 8

Validar calentamiento, vaciado de cola al final, sensibilidad, politicas, parametros y tiempos;
ejecutar replicas pareadas, intervalos y pruebas. El corte actual conserva la cola y servicios
sin completar. No se debe concluir mejora con una sola corrida o comparar promedios con
denominadores distintos. Las pantallas y endpoints de benchmark demo quedan bloqueados
para NYC. La validacion operacional, GPS y decisiones de despacho en vivo quedan fuera de alcance.

## Verificacion reproducible

```powershell
$env:PYTHONPATH = 'backend'
python -m unittest discover -s backend/tests -v
npm run lint
npm run build
# Con frontend :5173 y FastAPI :8000 activos:
npx playwright install chromium
npx playwright test tests/historical-ui.spec.ts --workers=1
```

Pruebas del motor: secuencia de eventos, cola, liberacion, efecto de flota/politica,
reproducibilidad por semilla/paso y aislamiento de resultados futuros.
Pruebas UI: ambos modos, avance, 2D/3D, canvas no vacio/cambiante, escritorio/movil y fallo de API.

Referencia del planificador: [SimPy Environment](https://simpy.readthedocs.io/en/latest/topical_guides/environments.html).
