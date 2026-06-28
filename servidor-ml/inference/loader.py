"""
Estado global de centroides en memoria.

El servidor carga los centroides del modelo activo al arrancar y los mantiene
en memoria para que cada request de inferencia no toque la base de datos.
"""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.almacen import get_active_centroids
import config

logger = logging.getLogger(__name__)

_state: dict = {
    "centroids": [],       # lista de dicts {zone_id, centroid_lat, centroid_lng}
    "active_version": None,
    "eps_meters": config.ML_EPS_METROS,
}


def load_centroids_from_db() -> None:
    """
    Recarga los centroides del modelo activo desde BD Almacén.
    Llamar al arrancar el servidor y cada vez que Persona 2 registra un nuevo modelo.
    """
    try:
        rows = get_active_centroids()
        _state["centroids"] = rows
        if rows:
            _state["active_version"] = rows[0]["version"]
            _state["eps_meters"] = float(rows[0]["eps_meters"])
        else:
            _state["active_version"] = None
        logger.info(
            "Centroides cargados: %d zonas — versión activa: %s",
            len(rows),
            _state["active_version"],
        )
    except Exception as exc:
        logger.error("Error al cargar centroides desde BD: %s", exc)


def get_state() -> dict:
    return _state
