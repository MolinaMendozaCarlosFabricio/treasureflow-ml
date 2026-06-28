import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from inference.loader import load_centroids_from_db
from api.routes import inference, history, model, health

app = FastAPI(
    title="TreasureFlow ML API",
    description=(
        "Microservicio de clustering geográfico para TreasureFlow. "
        "Agrupa publicaciones de residuos en zonas de densidad usando "
        "DBSCAN con métrica haversine."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(inference.router, prefix="/inference", tags=["Inferencia"])
app.include_router(history.router, prefix="/inference", tags=["Historial"])
app.include_router(model.router, tags=["Modelo"])
app.include_router(health.router, tags=["Health"])


@app.on_event("startup")
async def startup_event():
    load_centroids_from_db()
