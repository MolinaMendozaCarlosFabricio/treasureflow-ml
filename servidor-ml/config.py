import os
from dotenv import load_dotenv

load_dotenv()

# --- BD Almacén (entrenamiento histórico) ---
DB_ALMACEN_HOST = os.getenv("DB_ALMACEN_HOST", "localhost")
DB_ALMACEN_PORT = int(os.getenv("DB_ALMACEN_PORT", "5433"))
DB_ALMACEN_NAME = os.getenv("DB_ALMACEN_NAME", "treasureflow_almacen")
DB_ALMACEN_USER = os.getenv("DB_ALMACEN_USER", "postgres")
DB_ALMACEN_PASSWORD = os.getenv("DB_ALMACEN_PASSWORD", "")

# --- BD Transaccional (solo observer.py para LISTEN) ---
DB_TRANS_HOST = os.getenv("DB_TRANS_HOST", "localhost")
DB_TRANS_PORT = int(os.getenv("DB_TRANS_PORT", "5432"))
DB_TRANS_NAME = os.getenv("DB_TRANS_NAME", "treasureflow_db")
DB_TRANS_USER = os.getenv("DB_TRANS_USER", "postgres")
DB_TRANS_PASSWORD = os.getenv("DB_TRANS_PASSWORD", "")

# --- Hiperparámetros DBSCAN ---
ML_EPS_METROS = float(os.getenv("ML_EPS_METROS", "500"))
ML_MIN_SAMPLES = int(os.getenv("ML_MIN_SAMPLES", "4"))

# --- Umbrales de reentrenamiento ---
ML_UMBRAL_PUBLICACIONES_NUEVAS = int(os.getenv("ML_UMBRAL_PUBLICACIONES_NUEVAS", "100"))
ML_UMBRAL_PCT_SIN_ZONA = float(os.getenv("ML_UMBRAL_PCT_SIN_ZONA", "0.30"))
ML_UMBRAL_DIAS_SIN_ENTRENAR = int(os.getenv("ML_UMBRAL_DIAS_SIN_ENTRENAR", "30"))

# --- Integración con Persona 3 ---
ML_API_RELOAD_URL = os.getenv("ML_API_RELOAD_URL", "http://localhost:8000/reload-model")

# --- Canal PostgreSQL para corrective trigger ---
ML_NOTIFY_CHANNEL = os.getenv("ML_NOTIFY_CHANNEL", "alerta_modelo")

# --- Cold start ---
COLD_START_UMBRAL = 50
COLD_START_MIN_SAMPLES = 3
