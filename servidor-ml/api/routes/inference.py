from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, field_validator, ConfigDict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from inference.predict import assign_zone
from inference.loader import get_state
from db.almacen import save_inference_log

router = APIRouter()


class InferenceRequest(BaseModel):
    publication_id: Optional[str] = None
    lat: float
    lng: float

    @field_validator("lat")
    @classmethod
    def lat_range(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("lat debe estar entre -90 y 90")
        return v

    @field_validator("lng")
    @classmethod
    def lng_range(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("lng debe estar entre -180 y 180")
        return v


class InferenceResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    zone_id: Optional[int]
    distance_meters: Optional[float]
    model_version: Optional[str]
    assigned: bool
    mode: str


@router.post(
    "/assign-zone",
    response_model=InferenceResponse,
    summary="Asignar zona geográfica a una publicación",
    description=(
        "Recibe las coordenadas de una publicación de residuos y retorna "
        "la zona DBSCAN más cercana. Si la publicación está fuera del radio "
        "de cualquier zona (`eps_meters`) retorna `zone_id: null` y "
        "`assigned: false`. En cold start retorna `mode: 'no_model'`."
    ),
)
def assign_zone_endpoint(request: InferenceRequest) -> InferenceResponse:
    result = assign_zone(request.lat, request.lng)
    state = get_state()
    result["model_version"] = state["active_version"]

    save_inference_log(
        publication_id=request.publication_id,
        lat=request.lat,
        lng=request.lng,
        zone_id=result["zone_id"],
        distance_meters=result["distance_meters"],
        assigned=result["assigned"],
        model_version=result["model_version"],
    )

    return InferenceResponse(**result)
