"""
Punto de entrada del Servidor ML — Persona 3.

Arranca:
  - FastAPI + Swagger (uvicorn)
  - Scheduler de monitoreo diario (BackgroundScheduler 1:30 AM)

Uso:
    # Con el venv activado, desde servidor-ml/
    python main.py
    # O directamente:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""
import logging
import os
import sys

import uvicorn

sys.path.insert(0, os.path.dirname(__file__))

import config
from api.app import app
from scheduler.monitoring_job import crear_scheduler_monitoreo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_scheduler = crear_scheduler_monitoreo()


@app.on_event("startup")
async def start_monitoring_scheduler():
    _scheduler.start()
    logger.info("Scheduler de monitoreo iniciado")


@app.on_event("shutdown")
async def stop_monitoring_scheduler():
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler de monitoreo detenido")


if __name__ == "__main__":
    port = int(os.getenv("ML_API_PORT", "8000"))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
