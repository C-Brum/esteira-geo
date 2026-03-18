"""
PostGIS Loader - Importa dados processados no banco de dados PostgreSQL

Cria tabelas no PostGIS:
- flooding_areas - polígonos de enchentes
- citizens - pontos de cidadãos
- citizens_affected_by_flood - vista com cidadãos afetados
"""

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values
import logging
from pathlib import Path
from config import (
    LOCAL_GOLD_USE_CASE, LOCAL_SILVER_USE_CASE, USE_CASE,
    RDS_HOST, RDS_PORT, RDS_DATABASE, RDS_USER, RDS_PASSWORD,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE
)

logger = logging.getLogger(__name__)


def get_db_connection():
    """Cria conexão com PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=RDS_HOST,
            port=RDS_PORT,
            database=RDS_DATABASE,
            user=RDS_USER,
            password=RDS_PASSWORD
        )
        logger.info(f"✓ Conectado ao PostgreSQL: {RDS_HOST}:{RDS_PORT}/{RDS_DATABASE}")
        return conn
    except psycopg2.Error as e:
        logger.error(f"✗ Falha na conexão PostgreSQL: {e}")
        return None


def _table(use_case: str, base: str) -> str:
    """Retorna nome da tabela com prefixo do caso de uso: enchentes_poa_citizens"""
    return f"{use_case}_{base}"


def create_tables(conn, use_case: str):
    """Cria tabelas do caso de uso se não existirem, com migração de citizen_id se necessário"""
    cursor = conn.cursor()
    t_citizens = _table(use_case, 'citizens')
    t_areas = _table(use_case, 'flooding_areas')

    # Migrar citizen_id de INTEGER para VARCHAR se necessário
    cursor.execute("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = %s AND column_name = 'citizen_id'
    """, (t_citizens,))
    row = cursor.fetchone()
    if row and row[0] != 'character varying':
        logger.info(f"Migrando {t_citizens}.citizen_id de INTEGER para VARCHAR...")
        cursor.execute(f"DROP TABLE IF EXISTS {t_citizens} CASCADE")
        conn.commit()

    sql_commands = [
        f"""
        CREATE TABLE IF NOT EXISTS {t_areas} (
            area_id SERIAL PRIMARY KEY,
            area_name VARCHAR(255),
            flood_date DATE,
            severity VARCHAR(50),
            affected_population INTEGER,
            geometry GEOMETRY(POLYGON, 4326),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {t_citizens} (
            citizen_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(255),
            address TEXT,
            phone VARCHAR(20),
            registration_date DATE,
            geometry GEOMETRY(POINT, 4326),
            affected_by_flooding BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        f"CREATE INDEX IF NOT EXISTS idx_{use_case}_areas_geom ON {t_areas} USING GIST(geometry)",
        f"CREATE INDEX IF NOT EXISTS idx_{use_case}_citizens_geom ON {t_citizens} USING GIST(geometry)",
    ]

    for sql in sql_commands:
        try:
            cursor.execute(sql)
        except psycopg2.Error as e:
            logger.warning(f"⚠ Erro ao criar tabela: {e}")

    conn.commit()
    cursor.close()
    logger.info(f"✓ Tabelas {t_areas}, {t_citizens} criadas/verificadas")


def load_citizens_to_postgis(conn, filepath, affected: bool, use_case: str):
    """Carrega cidadãos (afetados ou não) na tabela do caso de uso"""
    label = 'afetados' if affected else 'não afetados'
    logger.info(f"Carregando cidadãos {label} para PostGIS...")

    gdf = gpd.read_parquet(filepath)
    t = _table(use_case, 'citizens')
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {t} WHERE affected_by_flooding = %s", (affected,))

    for _, row in gdf.iterrows():
        cursor.execute(
            f"""
            INSERT INTO {t} (citizen_id, name, address, phone, registration_date, geometry, affected_by_flooding)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
            ON CONFLICT (citizen_id) DO UPDATE SET affected_by_flooding = EXCLUDED.affected_by_flooding
            """,
            (
                str(row['citizen_id']),
                str(row['name']),
                str(row.get('address', 'N/A')),
                str(row.get('phone', 'N/A')),
                row.get('registration_date', None),
                f"POINT({row.geometry.x} {row.geometry.y})",
                affected,
            )
        )

    conn.commit()
    cursor.close()
    logger.info(f"✓ Carregados {len(gdf)} cidadãos {label}")


def query_statistics(conn, use_case: str):
    """Retorna estatísticas do caso de uso"""
    t = _table(use_case, 'citizens')
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    stats = {'total_citizens': cursor.fetchone()[0]}
    cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE affected_by_flooding = TRUE")
    stats['affected_citizens'] = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM {t} WHERE affected_by_flooding = FALSE")
    stats['unaffected_citizens'] = cursor.fetchone()[0]
    cursor.close()
    return stats


def load_flooding_areas_to_postgis(conn, use_case: str):
    """Carrega áreas de enchente da Silver para a tabela do caso de uso"""
    logger.info("Carregando áreas de enchente para PostGIS...")
    try:
        silver_path = Path(LOCAL_SILVER_USE_CASE) / "silver_flooding_areas_porto_alegre.parquet"
        gdf = gpd.read_parquet(str(silver_path))
        t = _table(use_case, 'flooding_areas')
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {t}")
        for idx, row in gdf.iterrows():
            cursor.execute(
                f"""
                INSERT INTO {t} (area_name, flood_date, severity, affected_population, geometry)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))
                """,
                (
                    str(row.get('area_name', f'Area_{idx}')),
                    row.get('flood_date', None),
                    str(row.get('severity', 'unknown')),
                    int(row.get('affected_population', 0)) if 'affected_population' in row else 0,
                    row.geometry.wkt,
                )
            )
        conn.commit()
        cursor.close()
        logger.info(f"✓ Carregadas {len(gdf)} áreas de enchente")
        return len(gdf)
    except Exception as e:
        logger.error(f"✗ Erro ao carregar áreas de enchente: {e}")
        return 0


def load_to_postgis():
    """Orquestrador: carrega dados do caso de uso no PostGIS"""
    logger.info("=" * 60)
    logger.info(f"POSTGIS LOADER - Caso de uso: {USE_CASE}")
    logger.info("=" * 60)

    conn = get_db_connection()
    if not conn:
        logger.error("✗ Não foi possível conectar ao banco de dados!")
        return False

    try:
        create_tables(conn, USE_CASE)
        load_flooding_areas_to_postgis(conn, USE_CASE)
        load_citizens_to_postgis(conn, str(Path(LOCAL_GOLD_USE_CASE) / AFFECTED_CITIZENS_FILE), True, USE_CASE)
        load_citizens_to_postgis(conn, str(Path(LOCAL_GOLD_USE_CASE) / UNAFFECTED_CITIZENS_FILE), False, USE_CASE)

        stats = query_statistics(conn, USE_CASE)
        logger.info("=" * 60)
        logger.info(f"✓ Dados carregados no PostGIS! (tabelas: {USE_CASE}_citizens, {USE_CASE}_flooding_areas)")
        logger.info(f"  Total: {stats['total_citizens']} | Afetados: {stats['affected_citizens']} | Não afetados: {stats['unaffected_citizens']}")
        logger.info("=" * 60)
        conn.close()
        return True
    except Exception as e:
        logger.error(f"✗ Erro ao carregar dados: {e}")
        conn.close()
        return False


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    load_to_postgis()
