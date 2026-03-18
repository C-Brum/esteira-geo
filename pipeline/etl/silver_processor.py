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
from pathlib import Path
from config import (
    SAMPLE_DATA_DIR, FLOODING_AREAS_FILE, CITIZENS_FILE,
    AWS_S3_SILVER_BUCKET, S3_SILVER_PREFIX,
    LOCAL_BRONZE_USE_CASE, LOCAL_SILVER_USE_CASE, USE_MINIO,
    AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
)

logger = logging.getLogger(__name__)


def load_from_bronze(filename):
    """Carrega arquivos da camada Bronze (local ou S3)

    Usa os caminhos locais configurados (LOCAL_BRONZE_PATH) quando rodando
    em ambiente de desenvolvimento com MinIO/Docker.
    """
    # Preferir caminho local do volume bronze
    filepath = f"{LOCAL_BRONZE_USE_CASE}/{filename}"
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
    gdf['phone'] = gdf['phone'].fillna('N/A') if 'phone' in gdf.columns else 'N/A'

    # Padronizar citizen_id: aceitar int ou string (ex: 'C003')
    try:
        gdf['citizen_id'] = gdf['citizen_id'].astype('int64')
    except (ValueError, TypeError):
        # IDs string (ex: 'C003') — manter como string
        gdf['citizen_id'] = gdf['citizen_id'].astype(str)

    # Normalizar coluna de data (registered_date → registration_date)
    if 'registered_date' in gdf.columns and 'registration_date' not in gdf.columns:
        gdf.rename(columns={'registered_date': 'registration_date'}, inplace=True)
    if 'registration_date' in gdf.columns:
        gdf['registration_date'] = pd.to_datetime(gdf['registration_date'], errors='coerce')

    if 'name' in gdf.columns and gdf['name'].dtype == 'object':
        gdf['name'] = gdf['name'].str.strip()
    if 'address' in gdf.columns and gdf['address'].dtype == 'object':
        gdf['address'] = gdf['address'].str.strip()

    # Adicionar campos de controle
    gdf['normalized_date'] = pd.Timestamp.now()
    gdf['data_quality_score'] = 1.0

    logger.info(f"✓ Normalizado: {len(gdf)} registros válidos")
    return gdf


def save_to_silver(gdf, filename):
    """Salva dados normalizados na camada Silver (local ou S3)"""
    # Salvar localmente na pasta silver (volume)
    filepath = f"{LOCAL_SILVER_USE_CASE}/{filename}"
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(filepath)
    logger.info(f"✓ Salvo Silver: {filepath}")

    # Upload S3/MinIO (opcional) - somente quando configurado
    if USE_MINIO or (AWS_S3_SILVER_BUCKET and AWS_S3_SILVER_BUCKET != ''):
        try:
            import boto3
            # Construir kwargs do cliente boto3 com endpoint/credenciais quando aplicável
            client_kwargs = {}
            if USE_MINIO and AWS_ENDPOINT_URL:
                client_kwargs['endpoint_url'] = AWS_ENDPOINT_URL
            if AWS_ACCESS_KEY_ID:
                client_kwargs['aws_access_key_id'] = AWS_ACCESS_KEY_ID
            if AWS_SECRET_ACCESS_KEY:
                client_kwargs['aws_secret_access_key'] = AWS_SECRET_ACCESS_KEY

            logger.debug(f"boto3 client kwargs: {client_kwargs}")
            s3 = boto3.client('s3', **client_kwargs)
            s3_key = f"{S3_SILVER_PREFIX}{filename}"
            s3.upload_file(filepath, AWS_S3_SILVER_BUCKET, s3_key)
            logger.info(f"✓ Upload S3: s3://{AWS_S3_SILVER_BUCKET}/{s3_key}")
        except Exception as e:
            logger.warning(f"⚠ Upload S3 falhou: {e}")


def consolidate_citizens(silver_use_case_path):
    """
    Consolida todos os parquets de cidadãos externos do diretório silver do caso de uso.
    Processa qualquer arquivo .parquet que não tenha prefixo 'silver_' (gerados pelo conversor).
    Deduplica por citizen_id.
    """
    silver_dir = Path(silver_use_case_path)
    frames = []

    # Glob dinâmico: todos os parquets sem prefixo 'silver_' exceto os dados sintéticos
    SYNTHETIC_FILES = {FLOODING_AREAS_FILE, CITIZENS_FILE}
    for fp in sorted(silver_dir.glob('*.parquet')):
        if fp.name.startswith('silver_') or fp.name in SYNTHETIC_FILES:
            continue
        try:
            gdf = gpd.read_parquet(fp)
            if 'geometry' not in gdf.columns:
                logger.warning(f"⚠ {fp.name} sem coluna geometry, ignorado")
                continue
            gdf = normalize_citizens(gdf)
            frames.append(gdf)
            logger.info(f"✓ Consolidando {fp.name}: {len(gdf)} registros")
        except Exception as e:
            logger.warning(f"⚠ Erro ao consolidar {fp.name}: {e}")

    return frames


def process_silver():
    """Orquestrador: normaliza todos os dados da Bronze"""
    logger.info("=" * 60)
    logger.info("SILVER PROCESSOR - Normalizando dados")
    logger.info("=" * 60)

    # Processar áreas de enchente
    flooding_bronze = load_from_bronze(FLOODING_AREAS_FILE)
    flooding_silver = normalize_flooding_areas(flooding_bronze)
    save_to_silver(flooding_silver, f"silver_{FLOODING_AREAS_FILE}")

    # Processar cidadãos do bronze_loader
    citizens_bronze = load_from_bronze(CITIZENS_FILE)
    citizens_silver = normalize_citizens(citizens_bronze)

    # Consolidar com arquivos externos da silver (CSV/GeoJSON convertidos)
    extra_frames = consolidate_citizens(LOCAL_SILVER_USE_CASE)
    if extra_frames:
        import geopandas as gpd
        combined = gpd.GeoDataFrame(
            pd.concat([citizens_silver] + extra_frames, ignore_index=True),
            geometry='geometry', crs='EPSG:4326'
        )
        # Deduplicar: citizen_id pode ser int ou string — converter tudo para string para comparar
        combined['_cid_str'] = combined['citizen_id'].astype(str)
        combined = combined.drop_duplicates(subset=['_cid_str'], keep='first')
        combined = combined.drop(columns=['_cid_str'])
        # Remover colunas auxiliares com tipos mistos após concat
        combined = combined.drop(columns=[c for c in ['geometry_valid', '_processed_date', '_source_type', '_data_quality'] if c in combined.columns])
        # Uniformizar citizen_id como string quando há IDs mistos (int + string)
        if combined['citizen_id'].dtype == object:
            combined['citizen_id'] = combined['citizen_id'].astype(str)
        # Garantir tipos corretos em colunas com NaN após concat
        combined['normalized_date'] = pd.to_datetime(combined['normalized_date'])
        combined = gpd.GeoDataFrame(combined, geometry='geometry', crs='EPSG:4326')
        logger.info(f"✓ Total consolidado: {len(combined)} cidadãos ({len(citizens_silver)} sintéticos + {len(combined)-len(citizens_silver)} externos)")
        citizens_silver = combined

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
