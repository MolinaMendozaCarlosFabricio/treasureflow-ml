from fastapi import APIRouter
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from inference.loader import get_state

router = APIRouter()


@router.get(
    "/health",
    summary="Estado del servicio",
    description="Verifica que el servicio esté activo e indica el modelo cargado en memoria.",
)
def health() -> dict:
    state = get_state()
    return {
        "status": "ok",
        "active_model": state["active_version"],
        "n_zones_in_memory": len(state["centroids"]),
        "mode": "normal" if state["centroids"] else "no_model",
    }
