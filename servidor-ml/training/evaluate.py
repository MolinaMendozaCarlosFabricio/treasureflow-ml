import numpy as np
from sklearn.metrics import silhouette_score


def calcular_metricas(X: np.ndarray, labels: np.ndarray, explained_var: float) -> dict:
    """
    Calcula las métricas del modelo entrenado.

    Args:
        X            - coordenadas en radianes [[lat_rad, lng_rad], ...]
        labels       - etiquetas DBSCAN (-1 = outlier, 0..n = zona)
        explained_var - varianza explicada acumulada del PCA

    Retorna dict con:
        silhouette_score, pca_explained_variance, n_zones, pct_outliers
    """
    n_total = len(labels)
    mask = labels != -1
    n_inliers = mask.sum()

    n_zones = len(set(labels[mask])) if n_inliers > 0 else 0
    pct_outliers = float((labels == -1).sum() / n_total)

    if n_inliers >= 2 and n_zones >= 2:
        score = float(silhouette_score(X[mask], labels[mask], metric="haversine"))
    else:
        score = -1.0

    return {
        "silhouette_score": score,
        "pca_explained_variance": explained_var,
        "n_zones": n_zones,
        "pct_outliers": pct_outliers,
        "n_training_points": n_total,
    }


def evaluar_aprobacion(metricas: dict, modelo_activo: dict | None) -> tuple[bool, str | None]:
    """
    Decide si el modelo nuevo reemplaza al activo.

    Reglas:
      - silhouette > anterior (omitida en cold_start cuando no hay modelo previo)
      - pca_explained_variance >= 0.80
      - pct_outliers < 0.20
      - 2 <= n_zones <= 10

    Retorna (aprobado: bool, razon_rechazo: str | None)
    """
    score = metricas["silhouette_score"]
    var = metricas["pca_explained_variance"]
    n_zones = metricas["n_zones"]
    pct_out = metricas["pct_outliers"]

    if n_zones < 2 or n_zones > 10:
        return False, f"n_zones={n_zones} fuera del rango [2, 10]"

    if pct_out >= 0.20:
        return False, f"pct_outliers={pct_out:.2%} supera el límite del 20%"

    if var < 0.80:
        return False, f"pca_explained_variance={var:.4f} por debajo de 0.80"

    if modelo_activo is not None:
        prev_score = float(modelo_activo.get("silhouette_score") or -1.0)
        if score <= prev_score:
            return False, f"silhouette={score:.4f} no supera al modelo activo ({prev_score:.4f})"

    return True, None
