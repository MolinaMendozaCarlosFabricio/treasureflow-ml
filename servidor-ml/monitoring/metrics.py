"""
Monitoreo diario de calidad del modelo — se ejecuta a las 1:30 AM.

Calcula el porcentaje de publicaciones completadas del día anterior que
no recibieron asignación de zona (outliers de inferencia).
Guarda el resultado en daily_monitoring de BD Almacén.
"""
import logging
from datetime import date, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from db.transaccional import fetch_daily_zone_stats
from db.almacen import upsert_daily_monitoring
from inference.loader import get_state

logger = logging.getLogger(__name__)


def calculate_and_store_daily_metrics() -> None:
    """
    Punto de entrada del job de monitoreo.
    Consulta BD Transaccional → calcula pct_without_zone → guarda en BD Almacén.
    """
    yesterday = date.today() - timedelta(days=1)
    logger.info("Calculando métricas de monitoreo para %s", yesterday)

    try:
        stats = fetch_daily_zone_stats(yesterday)
    except Exception as exc:
        logger.error("Error al consultar BD Transaccional para monitoreo: %s", exc)
        return

    total = stats["total"]
    without = stats["without_zone"]
    pct = without / total if total > 0 else 0.0
    requires_retraining = pct > config.ML_UMBRAL_PCT_SIN_ZONA

    state = get_state()
    active_version = state.get("active_version")

    logger.info(
        "Monitoreo %s — total=%d sin_zona=%d pct=%.2f%% requires_retraining=%s",
        yesterday,
        total,
        without,
        pct * 100,
        requires_retraining,
    )

    try:
        upsert_daily_monitoring(
            monitoring_date=yesterday,
            pct_without_zone=pct,
            total_publications_day=total,
            without_zone_day=without,
            active_model_version=active_version,
            requires_retraining=requires_retraining,
        )
        logger.info("Registro de monitoreo guardado en BD Almacén")
    except Exception as exc:
        logger.error("Error al guardar monitoreo en BD Almacén: %s", exc)
