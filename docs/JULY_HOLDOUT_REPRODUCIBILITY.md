# Evaluacion temporal NYC EMS: julio de 2026

## Alcance y protocolo

Esta evaluacion complementa la [evidencia de desarrollo abril-junio](REPRODUCIBILITY.md).
El protocolo [nyc_ems_july_holdout_v1.json](../research/config/nyc_ems_july_holdout_v1.json)
se fijo el 23 de octubre de 2026 en el commit
`6d2a58cda9e9dd05c9712bf8859b1c4369259b2f`, antes de calcular las
salidas de julio. No equivale a un registro externo ni a un ensayo de campo.

Los modelos, reglas de despacho, calibracion y la flota primaria de 400
unidades proceden de abril-junio/mayo. Los incidentes de julio no se usaron
para reentrenar. La fuente es [NYC EMS Incident Dispatch Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj).
La extraccion fija `20261023T204623425822Z-721cf5988661` contiene 140 853
incidentes entre el 1 de julio y el 31 de julio de 2026, ambos inclusive.
El SHA-256 de la secuencia ordenada de identificadores de la extraccion es
`c9dc844edba978440dadd643c4b89f6afda49bca8c547a3d0c73473dea92a9bd`.
La fuente publica puede cambiar tras esta extraccion.

## Evidencia congelada

El archivo suplementario `nyc_ems_july_2026_holdout_evidence.zip` contiene
475 archivos: paginas JSON comprimidas de julio, manifiestos, cohortes,
entradas derivadas del simulador, pronosticos congelados, 210 pares con
trazas individuales, tablas diarias y analisis. SHA-256 del ZIP:

```text
4a657958cf4049c3267f29261a93b733f659914d67afbcde932b769f63507f8d
```

Se distribuye en la [release v2026.10-july-holdout](https://github.com/Pull-H/ems-digital-twin/releases/tag/v2026.10-july-holdout),
como suplemento de la release `v2026.10-repro` (abril-junio),
que aporta los modelos congelados necesarios para reconstruir el paquete de
evaluacion desde las extracciones originales. El ZIP de julio no sustituye
esa release de desarrollo. Los datos proceden de NYC Open Data; MIT cubre
el codigo, no cambia los terminos de los datos originales.

## Instalacion y comprobacion

Use un clon limpio en la etiqueta `v2026.10-july-holdout`. Descargue primero
e instale el ZIP de desarrollo conforme a [REPRODUCIBILITY.md](REPRODUCIBILITY.md)
y luego el ZIP suplementario de julio en `release_assets/`:

```powershell
git clone https://github.com/Pull-H/ems-digital-twin.git
cd ems-digital-twin
git checkout v2026.10-july-holdout
New-Item -ItemType Directory -Force release_assets | Out-Null
Invoke-WebRequest -Uri "https://github.com/Pull-H/ems-digital-twin/releases/download/v2026.10-july-holdout/nyc_ems_july_2026_holdout_evidence.zip" -OutFile "release_assets/nyc_ems_july_2026_holdout_evidence.zip"
(Get-FileHash release_assets/nyc_ems_july_2026_holdout_evidence.zip -Algorithm SHA256).Hash
python -m pip install -r requirements-repro.lock
python tools/july_holdout_bundle.py verify
python tools/july_holdout_bundle.py install
python -m research.experiments.july_holdout prepare
python -m research.pipeline.nyc_ems verify --snapshot 20261023T204623425822Z-721cf5988661 --config data/nyc_ems/july_holdout_config.json
python -m research.experiments.july_holdout forecast-report
python -m research.experiments.july_holdout analyze
```

`verify` comprueba el hash de cada archivo. `install` rehusa sobrescribir
evidencia ya existente. Para repetir desde los registros congelados en un
espacio de trabajo independiente, ejecute:

```powershell
python -m research.pipeline.nyc_ems phase3 --snapshot 20261023T204623425822Z-721cf5988661 --config data/nyc_ems/july_holdout_config.json
python -m research.pipeline.nyc_ems phase4 --snapshot 20261023T204623425822Z-721cf5988661 --config data/nyc_ems/july_holdout_config.json
python -m research.experiments.july_holdout build --snapshot 20261023T204623425822Z-721cf5988661
python -m research.experiments.july_holdout run --workers 2
python -m research.experiments.july_holdout analyze
```

La reconstruccion debe hacerse en **otro clon limpio**: instale la release
de desarrollo y, para julio, instale solo la fuente con
`python tools/july_holdout_bundle.py install-source`, seguida de
`python -m research.experiments.july_holdout prepare`. Despues ejecute la
secuencia siguiente; no sobrescriba artefactos publicados. Las corridas
pueden tardar varios minutos. El manifiesto de `evaluation/` impide reanudar con codigo,
configuracion o entradas alteradas. Los resultados se hallan en
`reports/nyc_ems/july_holdout_v1/evaluation/`.

## Resultados e interpretacion

- Ventana inferencial: 9-29 de julio, 21 dias calendarios consecutivos,
  diez semillas emparejadas por dia, 210 pares / 420 corridas.
- Resultado primario: media diaria de la diferencia reactiva menos asistida
  `+0,187` min (aproximadamente 11 segundos). IC 95 % percentil de bootstrap
  circular por bloques de siete dias: `[0,062; 0,285]` min. El IC con bloques
  de tres dias es `[0,031; 0,369]` min. La mediana diaria es `+0,002` min;
  la ventaja se concentra en algunos dias.
- Los 210 pares acabaron con 100 % de respuestas tras el vaciado limitado;
  no se confundieron incidentes pendientes al corte con respuestas ausentes.
- La proporcion dentro de ocho minutos fue 33,987 % en la regla reactiva y
  34,327 % en la asistida, pero la diferencia reactiva menos asistida es
  `-0,340` puntos porcentuales: esta metrica secundaria favorece a la
  asistida. Por tanto, ambas metricas de respuesta apuntan en la **misma**
  direccion en este conjunto, aunque el efecto medio es pequeño.
- Las 83 823 respuestas administrativas validas para los 21 dias tuvieron
  media de medias diarias de 24,947 min, frente a 12,939 min simulados con
  la regla reactiva. El error absoluto medio diario fue 12,008 min y el del
  P90 diario, 32,735 min. Es un desajuste importante: no hay validacion
  operacional del tiempo de respuesta.

Los IC y valores p se calculan sobre **21 dias**, no sobre 210 pares como si
fueran observaciones temporales independientes. La prueba HAC de tres rezagos
es secundaria; cuatro resultados secundarios preespecificados usan ajuste
de Holm. La eleccion de longitud de bloque con solo 21 dias sigue siendo
fragil. Ningun resultado prueba una mejora real del servicio: la flota de
400, geografia y reglas son supuestos, no observaciones de FDNY; tampoco se
simula relocalizacion preventiva ni hay GPS o prueba en Trujillo.

## Dependencias exactas

Python 3.12.10; versiones de `requirements-repro.lock`, en particular
NumPy 2.5.1, pandas 3.0.3, SciPy 1.18.0, scikit-learn 1.9.0,
SimPy 4.1.1 y statsmodels 0.14.6. Semillas: simulacion 12345-12354 y
bootstrap 20261023. El panel de prediccion utiliza los modelos entrenados
antes de julio, sin refit.
