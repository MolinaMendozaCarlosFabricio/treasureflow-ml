import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


def aplicar_scaler_pca(df: pd.DataFrame):
    """
    Escala lat_rad/lng_rad y aplica PCA de 2 componentes para evaluación.

    Retorna:
        scaler         - StandardScaler ajustado
        pca            - PCA ajustado
        X              - array original [[lat_rad, lng_rad], ...]  (radianes)
        X_scaled       - array escalado
        X_pca          - proyección en espacio PCA (solo para visualización/métricas)
        explained_var  - varianza explicada acumulada por los 2 componentes (0-1)
    """
    X = df[["lat_rad", "lng_rad"]].values.astype(float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_components = min(2, X_scaled.shape[1], X_scaled.shape[0])
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    explained_var = float(pca.explained_variance_ratio_.sum())

    return scaler, pca, X, X_scaled, X_pca, explained_var


def serializar(scaler: StandardScaler, pca: PCA) -> tuple[bytes, bytes]:
    """Serializa scaler y pca con pickle para almacenar como BYTEA."""
    return pickle.dumps(scaler), pickle.dumps(pca)
