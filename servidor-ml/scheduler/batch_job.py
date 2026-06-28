"""
Cron job nocturno — se ejecuta a las 2:30 AM.

Evalúa criterios planificables y dispara entrenamiento si alguno se cumple:
  - Preventivo: días sin entrenar > ML_UMBRAL_DIAS_SIN_ENTRENAR
  - Predictivo: publicaciones nuevas >= ML_UMBRAL_PUBLICACIONES_NUEVAS
"""
import logging
import sys
import os
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from db.almacen import get_last_approved_model, count_new_publications, has_any_model
from training.train import ejecutar_pipeline_completo

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def debe_entrenar() -> tuple[bool, str | None]:
    """
    Evalúa en orden preventivo → predictivo.
    Retorna (True, criterion) o (False, None).
    """
    ultimo = get_last_approved_model()

    # --- Preventivo: demasiado tiempo sin reentrenar ---
    if ultimo:
        dias = (date.today() - ultimo["batch_date"]).days
        logger.info("Días desde último entrenamiento aprobado: %d", dias)
        if dias > config.ML_UMBRAL_DIAS_SIN_ENTRENAR:
            logger.info("Criterio PREVENTIVO activado (%d días > %d)", dias, config.ML_UMBRAL_DIAS_SIN_ENTRENAR)
            return True, "preventive"

    # --- Predictivo: suficientes datos nuevos acumulados ---
    since = ultimo["batch_date"] if ultimo else date(2000, 1, 1)
    nuevas = count_new_publications(since)
    logger.info("Publicaciones nuevas desde %s: %d", since, nuevas)
    if nuevas >= config.ML_UMBRAL_PUBLICACIONES_NUEVAS:
        logger.info(
            "Criterio PREDICTIVO activado (%d pubs >= %d)",
            nuevas,
            config.ML_UMBRAL_PUBLICACIONES_NUEVAS,
        )
        return True, "predictive"

    logger.info("Ningún criterio de reentrenamiento programado se cumple. Modelo vigente sigue activo.")
    return False, None


def ejecutar_batch():
    """Punto de entrada del cron job."""
    logger.info("=== Batch job iniciado ===")

    # Cold start: si no hay ningún modelo, intentar entrenar directamente
    if not has_any_model():
        logger.info("No existe ningún modelo — evaluando cold start")
        ejecutar_pipeline_completo(criterion="cold_start")
        return

    entrenar, criterion = debe_entrenar()
    if entrenar:
        ejecutar_pipeline_completo(criterion=criterion)
    else:
        logger.info("=== Batch job finalizado sin reentrenamiento ===")


def iniciar_scheduler():
    """Arranca el scheduler APScheduler en modo bloqueante."""
    scheduler = BlockingScheduler(timezone="America/Mexico_City")
    scheduler.add_job(
        ejecutar_batch,
        trigger="cron",
        hour=2,
        minute=30,
        id="batch_training",
        name="Entrenamiento ML nocturno",
        replace_existing=True,
    )
    logger.info("Scheduler iniciado — entrenamiento programado a las 02:30 AM (México)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler detenido")


if __name__ == "__main__":
    iniciar_scheduler()
