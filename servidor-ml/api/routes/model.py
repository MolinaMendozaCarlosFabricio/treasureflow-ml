from fastapi import APIRouter
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from inference.loader import load_centroids_from_db, get_state

router = APIRouter()


@router.post(
    "/reload-model",
    summary="Recargar centroides del modelo activo",
    description=(
        "Uso interno — llamado por Persona 2 (training server) tras registrar "
        "una nueva versión aprobada. Recarga los centroides desde BD Almacén "
        "sin reiniciar el servicio."
    ),
)
def reload_model() -> dict:
    load_centroids_from_db()
    state = get_state()
    return {
        "status": "ok",
        "version_loaded": state["active_version"],
        "n_zones": len(state["centroids"]),
    }
