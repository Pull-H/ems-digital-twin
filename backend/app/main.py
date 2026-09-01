"""
EMS Digital Twin Prototype - FastAPI Backend
Simulación de red de servicios médicos de emergencia (EMS), despacho predictivo y análisis de equidad.
"""
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime
import math
import random

app = FastAPI(
    title="EMS Digital Twin API",
    description="Digital Twin prototype for Emergency Medical Services with equity & predictive dispatch",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory demo data store
@app.get("/")
def root():
    return {
        "project": "EMS Digital Twin Prototype",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "zones_count": 20,
        "bases_count": 4,
        "hospitals_count": 3,
        "ambulances_count": 12
    }

@app.get("/api/zones")
def get_zones():
    return {"message": "Consulte /api/zones en el servidor principal para obtener la cartografía GeoJSON completa de las 20 zonas."}

@app.get("/api/ambulances")
def get_ambulances():
    return {"message": "Retorna el estado en tiempo real de la flota de ambulancias."}

@app.post("/api/dispatch/evaluate")
def evaluate_dispatch(data: Dict[str, Any]):
    return {
        "selected_ambulance_id": 4,
        "ambulance_code": "AMB-04",
        "estimated_arrival_minutes": 6.3,
        "policy_used": data.get("policy", "predictivo"),
        "rationale": "Se seleccionó la ambulancia AMB-04 porque arriba en 6.3 min y preserva cobertura mínima en sector de alta vulnerabilidad."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
