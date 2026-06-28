"""
Orquestador principal del pipeline de entrenamiento ML.

Uso:
    from training.train import ejecutar_pipeline_completo
    ejecutar_pipeline_completo(criterion='predictive')
"""
import logging
from datetime import date

import numpy as np
from sklearn.cluster import DBSCAN

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from db.almacen import (
    fetch_processed_publications,
    get_active_model,
    has_any_model,
    count_total_publications,
    get_next_version,
)
from training.pca_analysis import aplicar_scaler_pca, serializar
from training.evaluate import calcular_metricas, evaluar_aprobacion
from training.register import registrar_modelo, notificar_persona3

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


def ejecutar_pipeline_completo(criterion: str) -> bool:
    """
    Pipeline completo de entrenamiento.

    Args:
        criterion: 'predictive' | 'preventive' | 'corrective' | 'cold_start'

    Retorna True si el modelo fue aprobado y registrado, False en caso contrario.
    """
    logger.info("=== Iniciando pipeline de entrenamiento [%s] ===", criterion)

    # 1. Determinar parámetros según contexto
    is_cold_start = not has_any_model()
    if is_cold_start:
        criterion = "cold_start"
        min_samples = config.COLD_START_MIN_SAMPLES
        umbral_pubs = config.COLD_START_UMBRAL
    else:
        min_samples = config.ML_MIN_SAMPLES
        umbral_pubs = config.ML_UMBRAL_PUBLICACIONES_NUEVAS

    # 2. Cargar datos
    df = fetch_processed_publications()
    n_total = len(df)
    logger.info("Publicaciones cargadas: %d", n_total)

    if is_cold_start and n_total < config.COLD_START_UMBRAL:
        logger.warning(
            "Cold start requiere mínimo %d publicaciones, solo hay %d. Abortando.",
            config.COLD_START_UMBRAL,
            n_total,
        )
        return False

    if n_total < 2:
        logger.warning("Datos insuficientes para entrenar (%d registros). Abortando.", n_total)
        return False

    # 3. Escalar + PCA
    scaler, pca, X, X_scaled, X_pca, explained_var = aplicar_scaler_pca(df)
    logger.info("PCA varianza explicada: %.4f", explained_var)

    # 4. DBSCAN sobre coordenadas en radianes (haversine requiere radianes)
    eps_radianes = config.ML_EPS_METROS / 6_371_000
    modelo_dbscan = DBSCAN(
        eps=eps_radianes,
        min_samples=min_samples,
        metric="haversine",
    ).fit(X)

    labels = modelo_dbscan.labels_
    df["cluster_id"] = labels

    n_zones = len(set(labels)) - (1 if -1 in labels else 0)
    n_outliers = int((labels == -1).sum())
    logger.info("Zonas detectadas: %d | Outliers: %d / %d", n_zones, n_outliers, n_total)

    # 5. Calcular centroides (en grados decimales, no radianes)
    centroides = []
    for cid in sorted(set(labels)):
        if cid == -1:
            continue
        puntos = df[df["cluster_id"] == cid]
        centroides.append(
            {
                "zone_id": int(cid),
                "centroid_lat": float(puntos["lat"].mean()),
                "centroid_lng": float(puntos["lng"].mean()),
                "n_publications": len(puntos),
            }
        )

    # 6. Evaluar métricas
    metricas = calcular_metricas(X, labels, explained_var)
    logger.info(
        "Métricas — silhouette=%.4f pct_outliers=%.2f%% n_zones=%d",
        metricas["silhouette_score"],
        metricas["pct_outliers"] * 100,
        metricas["n_zones"],
    )

    # 7. Criterio de aprobación
    modelo_activo = get_active_model()
    # En cold_start no hay modelo previo contra el que comparar silhouette
    modelo_comparar = None if is_cold_start else modelo_activo
    aprobado, razon_rechazo = evaluar_aprobacion(metricas, modelo_comparar)

    if aprobado:
        logger.info("Modelo APROBADO — reemplazará al activo anterior")
    else:
        logger.warning("Modelo RECHAZADO — razón: %s", razon_rechazo)

    # 8. Serializar artefactos
    scaler_bytes, pca_bytes = serializar(scaler, pca)

    # 9. Registrar en BD Almacén
    version = "v1.0" if is_cold_start else get_next_version()
    registrar_modelo(
        version=version,
        metricas=metricas,
        criterion=criterion,
        scaler_bytes=scaler_bytes,
        pca_bytes=pca_bytes,
        aprobado=aprobado,
        rejection_reason=razon_rechazo,
        centroides=centroides if aprobado else [],
        batch_date=date.today(),
    )

    # 10. Notificar a Persona 3 si fue aprobado
    if aprobado:
        notificar_persona3()

    logger.info("=== Pipeline finalizado [%s] aprobado=%s ===", criterion, aprobado)
    return aprobado
