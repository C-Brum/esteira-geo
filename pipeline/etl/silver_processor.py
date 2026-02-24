"""
Silver Processor - Normaliza dados da camada Bronze para Silver
- Validação de geometrias
- Remoção de duplicatas
- Padronização de tipos de dados
- Tratamento de valores nulos
"""

import geopandas as gpd
import pandas as pd
import logging
from config import (
    SAMPLE_DATA_DIR, FLOODING_AREAS_FILE, CITIZENS_FILE,
    AWS_S3_SILVER_BUCKET, S3_SILVER_PREFIX
)

logger = logging.getLogger(__name__)


def load_from_bronze(filename):
    """Carrega arquivos da camada Bronze (local ou S3)"""
    filepath = f"{SAMPLE_DATA_DIR}/{filename}"
    logger.info(f"Carregando: {filepath}")
    gdf = gpd.read_parquet(filepath)
    logger.info(f"✓ Carregado: {len(gdf)} registros")
    return gdf


def normalize_flooding_areas(gdf):
    """Normaliza dados de áreas de enchente"""
    logger.info("Normalizando áreas de enchente...")
    
    gdf = gdf.copy()
    
    # Validar geometrias
    gdf['geometry_valid'] = gdf.geometry.is_valid
    invalid_count = (~gdf['geometry_valid']).sum()
    
    if invalid_count > 0:
        logger.warning(f"  ⚠ Encontradas {invalid_count} geometrias inválidas")
        gdf = gdf[gdf['geometry_valid']].copy()
    
    # Remover duplicatas
    gdf = gdf.drop_duplicates(subset=['area_id'])
    
    # Padronizar tipos
    gdf['area_id'] = gdf['area_id'].astype('int64')
    gdf['flood_date'] = pd.to_datetime(gdf['flood_date'])
    gdf['affected_population'] = gdf['affected_population'].astype('int64')
    
    # Adicionar campos de controle
    gdf['normalized_date'] = pd.Timestamp.now()
    gdf['data_quality_score'] = 1.0
    
    logger.info(f"✓ Normalizado: {len(gdf)} registros válidos")
    return gdf


def normalize_citizens(gdf):
    """Normaliza dados de cidadãos"""
    logger.info("Normalizando dados de cidadãos...")
    
    gdf = gdf.copy()
    
    # Validar geometrias (pontos)
    gdf['geometry_valid'] = gdf.geometry.is_valid
    invalid_count = (~gdf['geometry_valid']).sum()
    
    if invalid_count > 0:
        logger.warning(f"  ⚠ Encontradas {invalid_count} geometrias inválidas")
        gdf = gdf[gdf['geometry_valid']].copy()
    
    # Remover duplicatas
    gdf = gdf.drop_duplicates(subset=['citizen_id'])
    
    # Tratar nulos
    gdf['phone'] = gdf['phone'].fillna('N/A')
    
    # Padronizar tipos
    gdf['citizen_id'] = gdf['citizen_id'].astype('int64')
    gdf['registration_date'] = pd.to_datetime(gdf['registration_date'])
    gdf['name'] = gdf['name'].str.strip() if gdf['name'].dtype == 'object' else gdf['name']
    gdf['address'] = gdf['address'].str.strip() if gdf['address'].dtype == 'object' else gdf['address']
    
    # Adicionar campos de controle
    gdf['normalized_date'] = pd.Timestamp.now()
    gdf['data_quality_score'] = 1.0
    
    logger.info(f"✓ Normalizado: {len(gdf)} registros válidos")
    return gdf


def save_to_silver(gdf, filename):
    """Salva dados normalizados na camada Silver (local ou S3)"""
    filepath = f"{SAMPLE_DATA_DIR}/{filename}"
    gdf.to_parquet(filepath)
    logger.info(f"✓ Salvo Silver: {filepath}")
    
    # Upload S3 (opcional)
    try:
        import boto3
        s3 = boto3.client('s3')
        s3_key = f"{S3_SILVER_PREFIX}{filename}"
        s3.upload_file(filepath, AWS_S3_SILVER_BUCKET, s3_key)
        logger.info(f"✓ Upload S3: s3://{AWS_S3_SILVER_BUCKET}/{s3_key}")
    except Exception as e:
        logger.warning(f"⚠ Upload S3 falhou: {e}")


def process_silver():
    """Orquestrador: normaliza todos os dados da Bronze"""
    logger.info("=" * 60)
    logger.info("SILVER PROCESSOR - Normalizando dados")
    logger.info("=" * 60)
    
    # Processar áreas de enchente
    flooding_bronze = load_from_bronze(FLOODING_AREAS_FILE)
    flooding_silver = normalize_flooding_areas(flooding_bronze)
    save_to_silver(flooding_silver, f"silver_{FLOODING_AREAS_FILE}")
    
    # Processar dados de cidadãos
    citizens_bronze = load_from_bronze(CITIZENS_FILE)
    citizens_silver = normalize_citizens(citizens_bronze)
    save_to_silver(citizens_silver, f"silver_{CITIZENS_FILE}")
    
    logger.info("=" * 60)
    logger.info("✓ Silver layer pronta!")
    logger.info("=" * 60)
    
    return flooding_silver, citizens_silver


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    process_silver()
