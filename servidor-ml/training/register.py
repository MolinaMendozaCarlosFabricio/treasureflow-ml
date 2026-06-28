import logging
import requests
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config
from db.almacen import get_connection

logger = logging.getLogger(__name__)


def registrar_modelo(
    version: str,
    metricas: dict,
    criterion: str,
    scaler_bytes: bytes,
    pca_bytes: bytes,
    aprobado: bool,
    rejection_reason: str | None,
    centroides: list[dict],
    batch_date,
) -> int:
    """
    Inserta la nueva versión en model_versions y, si aprobada, sus centroides.
    Devuelve el id de la fila insertada.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if aprobado:
                cur.execute(
                    "UPDATE model_versions SET is_active = FALSE WHERE is_active = TRUE"
                )

            cur.execute(
                """
                INSERT INTO model_versions (
                    version, eps_meters, min_samples,
                    silhouette_score, pca_explained_variance,
                    n_zones, pct_outliers, n_training_points,
                    is_active, approved, rejection_reason,
                    retraining_criterion, batch_date,
                    scaler_artifact, pca_artifact
                ) VALUES (
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
                RETURNING id
                """,
                (
                    version,
                    config.ML_EPS_METROS,
                    config.ML_MIN_SAMPLES,
                    metricas["silhouette_score"],
                    metricas["pca_explained_variance"],
                    metricas["n_zones"],
                    metricas["pct_outliers"],
                    metricas["n_training_points"],
                    aprobado,
                    aprobado,
                    rejection_reason,
                    criterion,
                    batch_date,
                    psycopg2_bytes(scaler_bytes),
                    psycopg2_bytes(pca_bytes),
                ),
            )
            version_id = cur.fetchone()[0]

            if aprobado and centroides:
                for c in centroides:
                    cur.execute(
                        """
                        INSERT INTO model_centroids
                            (version_id, zone_id, centroid_lat, centroid_lng, n_historical_publications)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (version_id, zone_id) DO NOTHING
                        """,
                        (
                            version_id,
                            c["zone_id"],
                            c["centroid_lat"],
                            c["centroid_lng"],
                            c["n_publications"],
                        ),
                    )

        conn.commit()

    logger.info(
        "Modelo %s registrado — aprobado=%s criterio=%s zonas=%d",
        version,
        aprobado,
        criterion,
        metricas["n_zones"],
    )
    return version_id


def notificar_persona3() -> bool:
    """Llama al endpoint de Persona 3 para que recargue centroides en memoria."""
    try:
        resp = requests.post(config.ML_API_RELOAD_URL, timeout=10)
        if resp.status_code == 200:
            logger.info("Persona 3 recargó el modelo correctamente")
            return True
        logger.warning("Persona 3 respondió con status %d", resp.status_code)
    except requests.RequestException as exc:
        logger.error("No se pudo notificar a Persona 3: %s", exc)
    return False


# --- Helpers ---

def psycopg2_bytes(data: bytes):
    """Convierte bytes a psycopg2.Binary para inserción BYTEA."""
    import psycopg2
    return psycopg2.Binary(data)
