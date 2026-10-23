"""Re-render article figures at 600 dpi without resampling low-resolution originals."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

os.environ.setdefault("MPLBACKEND", "Agg")
from PIL import Image
from build_final_article import generate_figures, ROOT, SNAPSHOT

DEST = ROOT / "docs/article_assets/publication"
TITLES = [
    "Arquitectura del sistema", "Metricas globales de prueba", "MAE por borough",
    "Demanda real y predicha", "Comparacion de politicas",
]
NOTES = [
    "Flujo de datos, entrenamiento, simulacion y visualizacion.",
    "Prueba de junio de 2026. MAE y RMSE en incidentes por hora; WAPE en porcentaje. Comparar modelos dentro de cada metrica.",
    "Error absoluto medio por borough y modelo; valores menores indican menor error.",
    "Modelo seleccionado en validacion. Series agregadas con media movil de 24 horas: el suavizado puede ocultar picos.",
    "Experimento archivado de fase 8, politica v1. Evidencia descriptiva simulada; no representa la sensibilidad posterior de fase 8D ni impacto operacional.",
]


def main():
    figures = generate_figures(output_dir=DEST, dpi=600)
    entries = []
    for path, title, note in zip(figures.values(), TITLES, NOTES):
        with Image.open(path) as original:
            width, height = original.size
            dpi = original.info.get("dpi", (0, 0))
            if any(abs(value - 600) > .1 for value in dpi):
                raise ValueError(f"Unexpected DPI: {path}: {dpi}")
            original.convert("RGB").save(path.with_suffix(".tiff"), compression="tiff_lzw", dpi=(600, 600))
            preview = original.copy()
            preview.thumbnail((1200, 900))
            preview.save(path.with_name(path.stem + "_preview.png"))
        entries.append({
            "id": path.stem, "title": title, "description": note,
            "width_px": width, "height_px": height, "dpi": 600,
            "print_width_cm": round(width / 600 * 2.54, 2),
            "print_height_cm": round(height / 600 * 2.54, 2),
            "files": {ext: {"bytes": path.with_suffix('.' + ext).stat().st_size,
                              "sha256": hashlib.sha256(path.with_suffix('.' + ext).read_bytes()).hexdigest()}
                      for ext in ("png", "tiff")},
        })
    (DEST / "manifest.json").write_text(json.dumps({"snapshot": SNAPSHOT, "figures": entries}, indent=2), encoding="utf-8")
    with ZipFile(DEST / "article_figures_600dpi.zip", "w", ZIP_DEFLATED) as archive:
        archive.write(DEST / "manifest.json", "manifest.json")
        for entry in entries:
            for ext in ("png", "tiff"):
                path = DEST / f"{entry['id']}.{ext}"
                archive.write(path, path.name)
    print(f"Exported {len(entries)} figures: {DEST}")


if __name__ == "__main__":
    main()
