import psycopg2
import psycopg2.extras
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config


def get_connection():
    return psycopg2.connect(
        host=config.DB_TRANS_HOST,
        port=config.DB_TRANS_PORT,
        database=config.DB_TRANS_NAME,
        user=config.DB_TRANS_USER,
        password=config.DB_TRANS_PASSWORD,
    )


def fetch_daily_zone_stats(target_date) -> dict:
    """
    Consulta publicaciones de residuos completadas del día anterior en BD Transaccional.
    Retorna {total, without_zone}.
    """
    sql = """
        SELECT
            COUNT(*) FILTER (WHERE zone_id IS NULL) AS without_zone,
            COUNT(*) AS total
        FROM publications
        WHERE publication_type = 'waste'
          AND status = 'completed'
          AND publication_date >= %s::date
          AND publication_date <  %s::date + INTERVAL '1 day'
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (target_date, target_date))
            row = cur.fetchone()

    return {
        "total": int(row["total"]) if row else 0,
        "without_zone": int(row["without_zone"]) if row else 0,
    }
