"""
PostGIS Loader - Espelho do Gold

O PostGIS reflete exatamente o conteúdo do gold:
- Cada execução faz TRUNCATE + INSERT (não acumula)
- Se o gold não existir (bucket apagado), as tabelas são esvaziadas
"""

import geopandas as gpd
import psycopg2
import logging
from pathlib import Path
from config import (
    LOCAL_GOLD_USE_CASE, LOCAL_SILVER_USE_CASE, USE_CASE,
    AWS_S3_SILVER_BUCKET, AWS_S3_GOLD_BUCKET,
    AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME,
    RDS_HOST, RDS_PORT, RDS_DATABASE, RDS_USER, RDS_PASSWORD,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, FLOODING_AREAS_FILE,
)

logger = logging.getLogger(__name__)


def _conn():
    try:
        c = psycopg2.connect(host=RDS_HOST, port=RDS_PORT, database=RDS_DATABASE,
                             user=RDS_USER, password=RDS_PASSWORD)
        logger.info(f"✓ Conectado: {RDS_HOST}:{RDS_PORT}/{RDS_DATABASE}")
        return c
    except psycopg2.Error as e:
        logger.error(f"✗ Falha na conexão: {e}")
        return None


def _t(base: str) -> str:
    return f"{USE_CASE}_{base}"


def _ensure_tables(conn):
    t_areas    = _t('flooding_areas')
    t_citizens = _t('citizens')
    cur = conn.cursor()

    # Recriar se schema desatualizado (citizen_id não-VARCHAR ou coluna updated_at ausente)
    cur.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = %s AND column_name IN ('citizen_id', 'updated_at')
    """, (t_citizens,))
    cols = {r[0]: r[1] for r in cur.fetchall()}
    if cols.get('citizen_id') != 'character varying' or 'updated_at' not in cols:
        cur.execute(f"DROP TABLE IF EXISTS {t_citizens} CASCADE")
        conn.commit()
        logger.info(f"Tabela {t_citizens} recriada (migração de schema)")

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {t_areas} (
            area_id SERIAL PRIMARY KEY,
            area_name VARCHAR(255),
            flood_date DATE,
            severity VARCHAR(50),
            affected_population INTEGER,
            geometry GEOMETRY(POLYGON, 4326),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {t_citizens} (
            citizen_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255),
            address TEXT,
            phone VARCHAR(20),
            registration_date DATE,
            geometry GEOMETRY(POINT, 4326),
            affected_by_flooding BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{USE_CASE}_areas_geom    ON {t_areas}    USING GIST(geometry)")
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{USE_CASE}_citizens_geom ON {t_citizens} USING GIST(geometry)")
    conn.commit()
    cur.close()


def _s3_client():
    kwargs = {'region_name': AWS_S3_REGION_NAME}
    if AWS_ENDPOINT_URL:      kwargs['endpoint_url']         = AWS_ENDPOINT_URL
    if AWS_ACCESS_KEY_ID:     kwargs['aws_access_key_id']    = AWS_ACCESS_KEY_ID
    if AWS_SECRET_ACCESS_KEY: kwargs['aws_secret_access_key']= AWS_SECRET_ACCESS_KEY
    import boto3
    return boto3.client('s3', **kwargs)


def _sync_areas(conn, gold_key: str):
    """TRUNCATE + INSERT das áreas a partir do gold S3. Se não existir, esvazia."""
    import io as _io
    s3 = _s3_client()
    t = _t('flooding_areas')
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {t}")
    try:
        obj = s3.get_object(Bucket=AWS_S3_GOLD_BUCKET, Key=gold_key)
        gdf = gpd.read_parquet(_io.BytesIO(obj['Body'].read()))
        for idx, row in gdf.iterrows():
            cur.execute(
                f"""INSERT INTO {t} (area_name, flood_date, severity, affected_population, geometry)
                    VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))""",
                (
                    str(row.get('area_name', f'Area_{idx}')),
                    row.get('flood_date', None),
                    str(row.get('severity', 'unknown')),
                    int(row.get('affected_population', 0)) if 'affected_population' in row else 0,
                    row.geometry.wkt,
                )
            )
        conn.commit()
        logger.info(f"✓ {t}: {len(gdf)} áreas sincronizadas")
    except Exception:
        conn.commit()
        logger.info(f"✓ {t}: esvaziada (silver não existe no S3)")
    cur.close()


def _sync_citizens(conn, gold_keys: dict):
    """TRUNCATE + INSERT dos cidadãos a partir do gold S3. Se não existir, esvazia."""
    import io as _io
    s3 = _s3_client()
    t = _t('citizens')
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {t}")
    total = 0
    for s3_key, affected in gold_keys.items():
        try:
            obj = s3.get_object(Bucket=AWS_S3_GOLD_BUCKET, Key=s3_key)
            gdf = gpd.read_parquet(_io.BytesIO(obj['Body'].read()))
        except Exception:
            continue
        for _, row in gdf.iterrows():
            cur.execute(
                f"""INSERT INTO {t} (citizen_id, name, address, phone, registration_date, geometry, affected_by_flooding)
                    VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
                    ON CONFLICT (citizen_id) DO UPDATE
                    SET affected_by_flooding = EXCLUDED.affected_by_flooding,
                        updated_at = CURRENT_TIMESTAMP""",
                (
                    str(row['citizen_id']),
                    str(row.get('name', '')),
                    str(row.get('address', '')),
                    str(row.get('phone', '')),
                    row.get('registration_date', None),
                    f"POINT({row.geometry.x} {row.geometry.y})",
                    affected,
                )
            )
        total += len(gdf)
    conn.commit()
    cur.close()
    if total > 0:
        logger.info(f"✓ {t}: {total} cidadãos sincronizados")
    else:
        logger.info(f"✓ {t}: esvaziada (gold não existe no S3)")


def load_to_postgis(sync_areas: bool = True, sync_citizens: bool = True) -> bool:
    """
    Sincroniza PostGIS com o estado atual do gold/silver.
    TRUNCATE + INSERT — o banco reflete exatamente o que está nos arquivos.
    Se os arquivos não existirem, as tabelas são esvaziadas.
    """
    logger.info("=" * 60)
    logger.info(f"POSTGIS SYNC - {USE_CASE}")
    logger.info("=" * 60)

    conn = _conn()
    if not conn:
        return False

    try:
        _ensure_tables(conn)

        if sync_areas:
            gold_key = f"{USE_CASE}/{FLOODING_AREAS_FILE}"
            _sync_areas(conn, gold_key)

        if sync_citizens:
            gold_keys = {
                f"{USE_CASE}/{AFFECTED_CITIZENS_FILE}": True,
                f"{USE_CASE}/{UNAFFECTED_CITIZENS_FILE}": False,
            }
            _sync_citizens(conn, gold_keys)
        else:
            # Sem gold — esvaziar cidadãos para refletir estado atual
            _sync_citizens(conn, {})

        # Estatísticas finais
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {_t('flooding_areas')}")
        n_areas = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {_t('citizens')}")
        n_citizens = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {_t('citizens')} WHERE affected_by_flooding = TRUE")
        n_affected = cur.fetchone()[0]
        cur.close()

        logger.info(f"✓ PostGIS sincronizado: {n_areas} áreas | {n_citizens} cidadãos ({n_affected} afetados)")
        logger.info("=" * 60)
        conn.close()
        return True

    except Exception as e:
        logger.error(f"✗ Erro na sincronização: {e}", exc_info=True)
        conn.close()
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    load_to_postgis()
