from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import article_figures, assistant, catalog, comparisons, data_io, datasets, dispatch, health, methodology, model_performance, predictions, simulations


def create_app() -> FastAPI:
    app = FastAPI(
        title="EMS Digital Twin API",
        description="Backend oficial en Python/FastAPI para el gemelo digital EMS.",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(article_figures.router, prefix="/api")
    app.include_router(catalog.router, prefix="/api")
    app.include_router(datasets.router, prefix="/api")
    app.include_router(data_io.router, prefix="/api")
    app.include_router(simulations.router, prefix="/api")
    app.include_router(predictions.router, prefix="/api")
    app.include_router(model_performance.router, prefix="/api")
    app.include_router(methodology.router, prefix="/api")
    app.include_router(dispatch.router, prefix="/api")
    app.include_router(comparisons.router, prefix="/api")
    app.include_router(assistant.router, prefix="/api")

    @app.get("/")
    def root():
        return {
            "project": "EMS Digital Twin",
            "backend": "fastapi",
            "status": "online",
            "docs_url": "/docs",
        }

    return app


app = create_app()
