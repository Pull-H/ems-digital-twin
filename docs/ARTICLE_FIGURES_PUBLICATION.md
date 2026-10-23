# Figuras del articulo a 600 dpi

En la barra de navegacion, abrir **Figuras del articulo**. Disponible tambien sin
cargar una corrida NYC. Incluye las cinco figuras de `docs/article_assets`, vista
previa, dimensiones, descarga individual PNG/TIFF y paquete ZIP completo.

Las copias originales permanecen intactas. Las versiones de publicacion se
encuentran en `docs/article_assets/publication/`. Matplotlib vuelve a dibujar las
figuras a 600 dpi desde las mismas tablas y resultados archivados, sin ampliar
los PNG originales. TIFF usa compresion LZW sin perdida. La API entrega los bytes
originales del archivo; la vista previa reducida no se utiliza como descarga.

## Regenerar

Desde la raiz, con los reportes originales de modelos y fase 8 disponibles:

```powershell
python -m pip install -r research/requirements.txt python-docx Pillow
python tools/export_article_figures.py
```

Esto genera solo figuras, manifiesto y ZIP; no modifica el articulo DOCX.
El manifiesto contiene snapshot, dimensiones, DPI, tamanos de impresion, bytes y
SHA-256 para comprobar las descargas. Reexportar despues de cambiar los reportes.
Si se despliega el backend en otra maquina, incluir tambien esta carpeta.

## Calidad de impresion

600 dpi depende del tamano fisico: ancho en cm = pixeles / 600 * 2.54.
La galeria indica el tamano correspondiente. Ampliar la imagen por encima de ese
tamano reduce su resolucion efectiva; reducirla la aumenta. Desactivar compresion
de imagenes en el editor del manuscrito y entregar los archivos originales como
figuras separadas cuando la revista lo solicite. PNG puede registrar 599.9988 dpi
por redondeo de su campo entero de pixeles por metro: equivale a 600 dpi.

Las figuras conservan su contenido cientifico: la comparacion de politicas es
del experimento archivado de fase 8, no del lote posterior 8D. MAE/RMSE y WAPE
tienen distintas unidades en la figura global. Exportar a 600 dpi no sustituye
la revision de leyendas, unidades, tipografia y requisitos especificos de la revista.

## API

- `GET /api/article-figures`: catalogo.
- `GET /api/article-figures/archive`: ZIP con diez imagenes y manifiesto.
- `GET /api/article-figures/{id}/preview`: vista previa.
- `GET /api/article-figures/{id}/png`: descarga PNG original a 600 dpi.
- `GET /api/article-figures/{id}/tiff`: descarga TIFF a 600 dpi.

IDs ajenos al catalogo y formatos no admitidos se rechazan. Las rutas no permiten
seleccionar archivos arbitrarios del servidor.
