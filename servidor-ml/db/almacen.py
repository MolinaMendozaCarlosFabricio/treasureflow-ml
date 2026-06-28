import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


def get_connection():
    return psycopg2.connect(
        host=config.DB_ALMACEN_HOST,
        port=config.DB_ALMACEN_PORT,
        database=config.DB_ALMACEN_NAME,
        user=config.DB_ALMACEN_USER,
        password=config.DB_ALMACEN_PASSWORD,
    )


def get_connection_trans():
    """Conexión a BD Transaccional. Solo usada por observer.py para LISTEN."""
    return psycopg2.connect(
        host=config.DB_TRANS_HOST,
        port=config.DB_TRANS_PORT,
        database=config.DB_TRANS_NAME,
        user=config.DB_TRANS_USER,
        password=config.DB_TRANS_PASSWORD,
    )


def fetch_processed_publications() -> pd.DataFrame:
    """Lee todas las publicaciones limpias de los últimos 90 días desde BD Almacén."""
    sql = """
        SELECT publication_id, lat, lng, lat_rad, lng_rad, publication_date, batch_date
        FROM processed_publications
        WHERE publication_date >= NOW() - INTERVAL '90 days'
        ORDER BY publication_date DESC
    """
    with get_connection() as conn:
        df = pd.read_sql(sql, conn)
    return df


def get_active_model() -> dict | None:
    """Devuelve la fila activa de model_versions o None si no existe."""
    sql = """
        SELECT id, version, silhouette_score, pca_explained_variance,
               n_zones, pct_outliers, batch_date
        FROM model_versions
        WHERE is_active = TRUE
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return dict(row) if row else None


def get_last_approved_model() -> dict | None:
    """Devuelve el último modelo aprobado (para calcular días sin entrenar)."""
    sql = """
        SELECT id, version, batch_date
        FROM model_versions
        WHERE approved = TRUE
        ORDER BY training_date DESC
        LIMIT 1
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return dict(row) if row else None


def count_new_publications(since_date: date) -> int:
    """Cuenta publicaciones en processed_publications cargadas después de since_date."""
    sql = """
        SELECT COUNT(*) AS n
        FROM processed_publications
        WHERE batch_date > %s
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (since_date,))
            row = cur.fetchone()
    return row[0] if row else 0


def count_total_publications() -> int:
    """Total de registros en processed_publications (para cold start check)."""
    sql = "SELECT COUNT(*) FROM processed_publications"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return row[0] if row else 0


def has_any_model() -> bool:
    """True si ya existe al menos un modelo registrado."""
    sql = "SELECT 1 FROM model_versions LIMIT 1"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone() is not None


def get_next_version() -> str:
    """Genera la siguiente cadena de versión (v1.0, v1.1, v1.2...)."""
    sql = "SELECT COUNT(*) FROM model_versions"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            count = cur.fetchone()[0]
    major = 1
    minor = count
    return f"v{major}.{minor}"


def get_active_centroids() -> list[dict]:
    """
    Devuelve los centroides del modelo activo en memoria.
    Cada dict: {zone_id, centroid_lat, centroid_lng, version, eps_meters}
    """
    sql = """
        SELECT mc.zone_id,
               mc.centroid_lat,
               mc.centroid_lng,
               mv.version,
               mv.eps_meters
        FROM model_centroids mc
        JOIN model_versions mv ON mc.version_id = mv.id
        WHERE mv.is_active = TRUE
        ORDER BY mc.zone_id
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def save_inference_log(
    publication_id: str | None,
    lat: float,
    lng: float,
    zone_id: int | None,
    distance_meters: float | None,
    assigned: bool,
    model_version: str | None,
) -> None:
    """Inserta una fila en inference_log (BD Almacén)."""
    sql = """
        INSERT INTO inference_log
            (publication_id, lat, lng, zone_id, distance_meters, assigned, model_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    import uuid as _uuid
    pub_id = None
    if publication_id:
        try:
            pub_id = _uuid.UUID(str(publication_id))
        except ValueError:
            pub_id = None

    # NUMERIC(8,2) max is 999999.99; clamp to avoid overflow for distant points
    _DIST_MAX = 999_999.99
    if distance_meters is not None and distance_meters > _DIST_MAX:
        distance_meters = _DIST_MAX

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (pub_id, lat, lng, zone_id, distance_meters, assigned, model_version))
        conn.commit()


def get_inference_history(
    limit: int = 50,
    offset: int = 0,
    zone_id: int | None = None,
    assigned: bool | None = None,
    from_date: str | None = None,
) -> tuple[int, list[dict]]:
    """
    Devuelve (total, resultados) del inference_log con filtros opcionales.
    from_date: ISO string 'YYYY-MM-DD'
    """
    conditions = []
    params: list = []

    if zone_id is not None:
        conditions.append("zone_id = %s")
        params.append(zone_id)
    if assigned is not None:
        conditions.append("assigned = %s")
        params.append(assigned)
    if from_date:
        conditions.append("inferred_at >= %s::date")
        params.append(from_date)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) FROM inference_log {where}", params)
            total = cur.fetchone()["count"]

            cur.execute(
                f"""
                SELECT id, publication_id, lat, lng, zone_id,
                       distance_meters, assigned, model_version, inferred_at
                FROM inference_log
                {where}
                ORDER BY inferred_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            rows = cur.fetchall()

    return total, [dict(r) for r in rows]


def upsert_daily_monitoring(
    monitoring_date: date,
    pct_without_zone: float,
    total_publications_day: int,
    without_zone_day: int,
    active_model_version: str | None,
    requires_retraining: bool,
) -> None:
    """Inserta o actualiza el registro diario en daily_monitoring (BD Almacén)."""
    sql = """
        INSERT INTO daily_monitoring
            (date, pct_without_zone, total_publications_day,
             without_zone_day, active_model_version, requires_retraining)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE SET
            pct_without_zone = EXCLUDED.pct_without_zone,
            total_publications_day = EXCLUDED.total_publications_day,
            without_zone_day = EXCLUDED.without_zone_day,
            active_model_version = EXCLUDED.active_model_version,
            requires_retraining = EXCLUDED.requires_retraining
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    monitoring_date,
                    pct_without_zone,
                    total_publications_day,
                    without_zone_day,
                    active_model_version,
                    requires_retraining,
                ),
            )
        conn.commit()
