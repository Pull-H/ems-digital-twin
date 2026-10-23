"""Read-only delivery of publication assets; never accepts arbitrary filesystem paths."""
import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.core.paths import PROJECT_ROOT

router = APIRouter(tags=["article-figures"])
ASSETS = PROJECT_ROOT / "docs/article_assets/publication"


def catalog():
    try:
        return json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(404, "Figuras no exportadas. Ejecuta python tools/export_article_figures.py") from exc


@router.get("/article-figures")
def list_figures():
    return catalog()


@router.get("/article-figures/archive")
def download_archive():
    path = ASSETS / "article_figures_600dpi.zip"
    if not path.is_file():
        raise HTTPException(404, "Paquete de figuras no disponible")
    return FileResponse(path, media_type="application/zip", filename=path.name)


@router.get("/article-figures/{figure_id}/{format}")
def get_figure(figure_id: str, format: Literal["preview", "png", "tiff"]):
    if figure_id not in {entry["id"] for entry in catalog()["figures"]}:
        raise HTTPException(404, "Figura no encontrada")
    name = f"{figure_id}_preview.png" if format == "preview" else f"{figure_id}.{format}"
    path = ASSETS / name
    if not path.is_file():
        raise HTTPException(404, "Archivo no disponible")
    return FileResponse(path, media_type="image/tiff" if format == "tiff" else "image/png",
                        filename=None if format == "preview" else name)
