"""
Job de monitoreo diario — se ejecuta a la 1:30 AM (antes del ETL).

Calcula pct_without_zone del día anterior consultando la BD Transaccional
y guarda el resultado en daily_monitoring de BD Almacén.
Este proceso es exclusivamente de auditoría analítica; no dispara
reentrenamiento (eso lo hace observer.py en tiempo real vía pg_notify).
"""
import logging
import sys
import os

from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from monitoring.metrics import calculate_and_store_daily_metrics

logger = logging.getLogger(__name__)


def crear_scheduler_monitoreo() -> BackgroundScheduler:
    """
    Crea y devuelve el scheduler de monitoreo en modo background.
    Se arranca desde main.py junto con uvicorn.
    """
    scheduler = BackgroundScheduler(timezone="America/Mexico_City")
    scheduler.add_job(
        calculate_and_store_daily_metrics,
        trigger="cron",
        hour=1,
        minute=30,
        id="monitoring_daily",
        name="Monitoreo diario pct_without_zone",
        replace_existing=True,
    )
    logger.info("Scheduler de monitoreo registrado — ejecución a las 01:30 AM (México)")
    return scheduler
