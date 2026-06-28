"""
Daemon persistente de emergencia — reentrenamiento correctivo.

Escucha el canal PostgreSQL 'alerta_modelo' en la BD Transaccional.
Cuando recibe {"event": "degradation"} dispara el pipeline de entrenamiento
completo leyendo datos históricos de la BD Almacén.

La BD Transaccional debe tener un trigger configurado que emita:
    SELECT pg_notify('alerta_modelo', '{"event": "degradation"}');
cuando pct_sin_zona > 30 % en la última hora.
"""
import json
import logging
import select
import sys
import os
import threading

import psycopg2
import psycopg2.extensions

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config
from db.almacen import get_connection_trans
from training.train import ejecutar_pipeline_completo

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

# Flag para evitar entrenamientos simultáneos
_training_lock = threading.Lock()


def _procesar_notificacion(payload_str: str) -> None:
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.warning("Payload inválido recibido en canal: %r", payload_str)
        return

    if payload.get("event") != "degradation":
        logger.debug("Evento ignorado: %s", payload.get("event"))
        return

    if not _training_lock.acquire(blocking=False):
        logger.warning("Ya hay un entrenamiento en curso — notificación correctiva ignorada")
        return

    try:
        logger.info("Alerta de degradación recibida — iniciando reentrenamiento correctivo")
        ejecutar_pipeline_completo(criterion="corrective")
    finally:
        _training_lock.release()


def iniciar_observador_emergencias() -> None:
    """
    Abre una conexión persistente a la BD Transaccional y escucha el canal
    ML_NOTIFY_CHANNEL indefinidamente usando select() para no quemar CPU.
    """
    canal = config.ML_NOTIFY_CHANNEL
    logger.info("Observador iniciado — escuchando canal '%s'", canal)

    conn = get_connection_trans()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        cur.execute(f"LISTEN {canal};")

    logger.info("LISTEN activado en canal '%s'", canal)

    while True:
        # Bloquear eficientemente hasta 30 s; si no llega nada, continuar el loop
        readable, _, _ = select.select([conn], [], [], 30)
        if not readable:
            continue  # timeout keepalive — mantiene el socket activo

        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            logger.info(
                "Notificación recibida — canal=%s pid=%d payload=%s",
                notify.channel,
                notify.pid,
                notify.payload,
            )
            # Procesar en hilo separado para no bloquear el loop de escucha
            t = threading.Thread(
                target=_procesar_notificacion,
                args=(notify.payload,),
                daemon=True,
            )
            t.start()


if __name__ == "__main__":
    iniciar_observador_emergencias()
