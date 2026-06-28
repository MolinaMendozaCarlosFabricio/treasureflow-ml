from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from db.almacen import get_inference_history

router = APIRouter()


class InferenceRecord(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    publication_id: Optional[str]
    lat: float
    lng: float
    zone_id: Optional[int]
    distance_meters: Optional[float]
    assigned: bool
    model_version: Optional[str]
    inferred_at: str


class HistoryResponse(BaseModel):
    total: int
    results: list[InferenceRecord]


@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="Historial de inferencias realizadas",
    description=(
        "Consulta paginada del log de inferencias almacenado en BD Almacén. "
        "Soporta filtros por `zone_id`, `assigned` y `from_date` (ISO YYYY-MM-DD)."
    ),
)
def get_history(
    limit: int = Query(50, ge=1, le=500, description="Máximo de resultados por página"),
    offset: int = Query(0, ge=0, description="Número de registros a omitir"),
    zone_id: Optional[int] = Query(None, description="Filtrar por zona específica"),
    assigned: Optional[bool] = Query(None, description="Filtrar por asignación exitosa"),
    from_date: Optional[str] = Query(None, description="Fecha mínima ISO YYYY-MM-DD"),
) -> HistoryResponse:
    total, rows = get_inference_history(
        limit=limit,
        offset=offset,
        zone_id=zone_id,
        assigned=assigned,
        from_date=from_date,
    )
    records = []
    for r in rows:
        records.append(
            InferenceRecord(
                id=r["id"],
                publication_id=str(r["publication_id"]) if r.get("publication_id") else None,
                lat=float(r["lat"]),
                lng=float(r["lng"]),
                zone_id=r.get("zone_id"),
                distance_meters=float(r["distance_meters"]) if r.get("distance_meters") else None,
                assigned=r["assigned"],
                model_version=r.get("model_version"),
                inferred_at=r["inferred_at"].isoformat() if r.get("inferred_at") else "",
            )
        )
    return HistoryResponse(total=total, results=records)
