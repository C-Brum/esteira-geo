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
    LOCAL_GOLD_PATH, RDS_HOST, RDS_PORT, RDS_DATABASE,
    RDS_USER, RDS_PASSWORD,
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


def create_tables(conn):
    """Cria tabelas if not exists"""
    cursor = conn.cursor()
    
    sql_commands = [
        # Tabela de áreas de enchente
        """
        CREATE TABLE IF NOT EXISTS flooding_areas (
            area_id SERIAL PRIMARY KEY,
            area_name VARCHAR(255),
            flood_date DATE,
            severity VARCHAR(50),
            affected_population INTEGER,
            geometry GEOMETRY(POLYGON, 4326),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Tabela de cidadãos
        """
        CREATE TABLE IF NOT EXISTS citizens (
            citizen_id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            address TEXT,
            phone VARCHAR(20),
            registration_date DATE,
            geometry GEOMETRY(POINT, 4326),
            affected_by_flooding BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Índices espaciais
        "CREATE INDEX IF NOT EXISTS idx_flooding_areas_geom ON flooding_areas USING GIST(geometry)",
        "CREATE INDEX IF NOT EXISTS idx_citizens_geom ON citizens USING GIST(geometry)",
    ]
    
    for sql in sql_commands:
        try:
            cursor.execute(sql)
            logger.info(f"✓ Tabela criada/verificada")
        except psycopg2.Error as e:
            logger.warning(f"⚠ Erro ao criar tabela: {e}")
    
    conn.commit()
    cursor.close()


def load_affected_citizens_to_postgis(conn, filepath):
    """Carrega cidadãos afetados no PostGIS"""
    logger.info(f"Carregando cidadãos afetados para PostGIS...")
    
    gdf = gpd.read_parquet(filepath)
    cursor = conn.cursor()
    
    # Limpar dados antigos
    cursor.execute("DELETE FROM citizens WHERE affected_by_flooding = TRUE")
    
    for idx, row in gdf.iterrows():
        sql = """
            INSERT INTO citizens (citizen_id, name, address, phone, registration_date, geometry, affected_by_flooding)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
            ON CONFLICT (citizen_id) DO UPDATE SET affected_by_flooding = TRUE
        """
        
        geom_wkt = f"POINT({row.geometry.x} {row.geometry.y})"
        
        cursor.execute(sql, (
            int(row['citizen_id']),
            str(row['name']),
            str(row['address']),
            str(row['phone']),
            row['registration_date'],
            geom_wkt,
            True
        ))
    
    conn.commit()
    cursor.close()
    logger.info(f"✓ Carregados {len(gdf)} cidadãos afetados")


def load_unaffected_citizens_to_postgis(conn, filepath):
    """Carrega cidadãos não afetados no PostGIS"""
    logger.info(f"Carregando cidadãos não afetados para PostGIS...")
    
    gdf = gpd.read_parquet(filepath)
    cursor = conn.cursor()
    
    # Limpar dados antigos (não afetados)
    cursor.execute("DELETE FROM citizens WHERE affected_by_flooding = FALSE")
    
    for idx, row in gdf.iterrows():
        sql = """
            INSERT INTO citizens (citizen_id, name, address, phone, registration_date, geometry, affected_by_flooding)
            VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
            ON CONFLICT (citizen_id) DO UPDATE SET affected_by_flooding = FALSE
        """
        
        geom_wkt = f"POINT({row.geometry.x} {row.geometry.y})"
        
        cursor.execute(sql, (
            int(row['citizen_id']),
            str(row['name']),
            str(row['address']),
            str(row['phone']),
            row['registration_date'],
            geom_wkt,
            False
        ))
    
    conn.commit()
    cursor.close()
    logger.info(f"✓ Carregados {len(gdf)} cidadãos não afetados")


def query_statistics(conn):
    """Retorna estatísticas do banco de dados"""
    cursor = conn.cursor()
    
    stats = {}
    
    # Total de cidadãos
    cursor.execute("SELECT COUNT(*) FROM citizens")
    stats['total_citizens'] = cursor.fetchone()[0]
    
    # Cidadãos afetados
    cursor.execute("SELECT COUNT(*) FROM citizens WHERE affected_by_flooding = TRUE")
    stats['affected_citizens'] = cursor.fetchone()[0]
    
    # Cidadãos não afetados
    cursor.execute("SELECT COUNT(*) FROM citizens WHERE affected_by_flooding = FALSE")
    stats['unaffected_citizens'] = cursor.fetchone()[0]
    
    cursor.close()
    return stats


def load_flooding_areas_to_postgis(conn):
    """Carrega áreas de enchente da Silver para PostGIS"""
    logger.info("Carregando áreas de enchente para PostGIS...")
    
    try:
        # Carregar GeoDataFrame da Silver
        from config import LOCAL_SILVER_PATH
        silver_path = Path(LOCAL_SILVER_PATH) / "silver_flooding_areas_porto_alegre.parquet"
        
        gdf = gpd.read_parquet(str(silver_path))
        cursor = conn.cursor()
        
        # Limpar dados antigos
        cursor.execute("DELETE FROM flooding_areas")
        
        for idx, row in gdf.iterrows():
            # Converter geometria para WKT
            geom_wkt = row.geometry.wkt
            
            sql = """
                INSERT INTO flooding_areas (area_name, flood_date, severity, affected_population, geometry)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))
            """
            
            cursor.execute(sql, (
                str(row.get('area_name', f'Area_{idx}')),
                row.get('flood_date', None),
                str(row.get('severity', 'unknown')),
                int(row.get('affected_population', 0)) if 'affected_population' in row else 0,
                geom_wkt
            ))
        
        conn.commit()
        cursor.close()
        logger.info(f"✓ Carregadas {len(gdf)} áreas de enchente")
        return len(gdf)
        
    except Exception as e:
        logger.error(f"✗ Erro ao carregar áreas de enchente: {e}")
        return 0


def load_to_postgis():
    """Orquestrador: carrega dados no PostGIS"""
    logger.info("=" * 60)
    logger.info("POSTGIS LOADER - Importando dados no banco")
    logger.info("=" * 60)
    
    # Conectar
    conn = get_db_connection()
    if not conn:
        logger.error("✗ Não foi possível conectar ao banco de dados!")
        return False
    
    try:
        # Criar tabelas
        create_tables(conn)
        
        # Carregar dados de enchentes PRIMEIRO
        load_flooding_areas_to_postgis(conn)
        
        # Carregar dados de cidadãos
        affected_path = Path(LOCAL_GOLD_PATH) / AFFECTED_CITIZENS_FILE
        unaffected_path = Path(LOCAL_GOLD_PATH) / UNAFFECTED_CITIZENS_FILE
        
        load_affected_citizens_to_postgis(conn, str(affected_path))
        load_unaffected_citizens_to_postgis(conn, str(unaffected_path))
        
        # Retornar estatísticas
        stats = query_statistics(conn)
        logger.info("=" * 60)
        logger.info("✓ Dados carregados no PostGIS!")
        logger.info(f"  Total: {stats['total_citizens']} cidadãos")
        logger.info(f"  Afetados: {stats['affected_citizens']}")
        logger.info(f"  Não afetados: {stats['unaffected_citizens']}")
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
