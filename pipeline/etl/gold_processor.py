"""
Gold Processor - Processamento geoespacial e batimento de dados
- Spatial join entre cidadãos e áreas de enchente
- Geração de 3 arquivos output:
  1. affected_citizens.parquet - cidadãos em área atingida
  2. unaffected_citizens.parquet - cidadãos fora de área atingida
  3. all_citizens_evaluated.parquet - todos os avaliados com status
"""

import geopandas as gpd
import pandas as pd
import logging
from pathlib import Path
from config import (
    LOCAL_SILVER_USE_CASE, LOCAL_GOLD_USE_CASE,
    AWS_S3_SILVER_BUCKET, AWS_S3_GOLD_BUCKET, S3_SILVER_PREFIX, S3_GOLD_PREFIX,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE,
    FLOODING_AREAS_FILE, CITIZENS_FILE,
    AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME,
)

logger = logging.getLogger(__name__)


def load_from_silver(filename):
    """Carrega arquivos da camada Silver (S3 como fonte de verdade)"""
    import io, boto3
    from config import AWS_S3_SILVER_BUCKET, S3_SILVER_PREFIX
    s3 = _s3()
    key = f"{S3_SILVER_PREFIX}{filename}"
    logger.info(f"Carregando Silver S3: s3://{AWS_S3_SILVER_BUCKET}/{key}")
    obj = s3.get_object(Bucket=AWS_S3_SILVER_BUCKET, Key=key)
    gdf = gpd.read_parquet(io.BytesIO(obj['Body'].read()))
    logger.info(f"✓ Carregado: {len(gdf)} registros")
    return gdf


def perform_spatial_join(flooding_gdf, citizens_gdf):
    """
    Batimento geográfico: identifica cidadãos em áreas atingidas
    Utiliza sjoin com geometria de polígonos (flooding) e pontos (cidadãos)
    """
    logger.info("Realizando spatial join (batimento geográfico)...")
    
    # Spatial join: cidadãos dentro de polígonos de enchente
    sjoin_result = gpd.sjoin(
        citizens_gdf,
        flooding_gdf,
        how='left',
        predicate='within'
    )
    
    logger.info(f"✓ Spatial join completado: {len(sjoin_result)} registros")
    return sjoin_result


def classify_citizens(spatial_join_result, flooding_gdf):
    """
    Classifica cidadãos como afetados ou não
    """
    logger.info("Classificando cidadãos...")
    
    gdf = spatial_join_result.copy()
    
    # Identifica afetados: têm index_right (correspondem a uma área de enchente)
    gdf['affected_by_flooding'] = gdf['index_right'].notna()
    gdf['affected_area_id'] = gdf['index_right'].astype('Int64')
    
    affected_count = gdf['affected_by_flooding'].sum()
    unaffected_count = (~gdf['affected_by_flooding']).sum()
    
    logger.info(f"  Cidadãos afetados: {affected_count}")
    logger.info(f"  Cidadãos não afetados: {unaffected_count}")
    
    return gdf


def generate_affected_citizens(gdf):
    """
    Extrai cidadãos afetados com informações de área atingida
    """
    logger.info("Gerando arquivo de cidadãos AFETADOS...")
    
    affected = gdf[gdf['affected_by_flooding']].copy()
    
    # Selecionar colunas relevantes
    columns_to_keep = [
        'citizen_id', 'name', 'address', 'phone', 'registration_date',
        'geometry', 'affected_by_flooding', 'affected_area_id',
        'area_name', 'flood_date', 'severity',
        'normalized_date', 'data_quality_score'
    ]
    
    affected = affected[[col for col in columns_to_keep if col in affected.columns]]
    affected = affected.drop_duplicates(subset=['citizen_id'], keep='first')
    affected['processing_date'] = pd.Timestamp.now()
    
    logger.info(f"✓ Gerado: {len(affected)} cidadãos afetados")
    return affected


def generate_unaffected_citizens(gdf):
    """
    Extrai cidadãos não afetados
    """
    logger.info("Gerando arquivo de cidadãos NÃO AFETADOS...")
    
    unaffected = gdf[~gdf['affected_by_flooding']].copy()
    
    # Selecionar colunas relevantes
    columns_to_keep = [
        'citizen_id', 'name', 'address', 'phone', 'registration_date',
        'geometry', 'affected_by_flooding', 'normalized_date',
        'data_quality_score'
    ]
    
    unaffected = unaffected[[col for col in columns_to_keep if col in unaffected.columns]]
    unaffected = unaffected.drop_duplicates(subset=['citizen_id'], keep='first')
    unaffected['processing_date'] = pd.Timestamp.now()
    
    logger.info(f"✓ Gerado: {len(unaffected)} cidadãos não afetados")
    return unaffected


def generate_all_citizens_summary(gdf):
    """
    Resume todos os cidadãos com status
    """
    logger.info("Gerando arquivo de RESUMO total...")
    
    all_citizens = gdf.copy()
    
    # Selecionar colunas principais
    columns_to_keep = [
        'citizen_id', 'name', 'address', 'phone', 'registration_date',
        'geometry', 'affected_by_flooding', 'affected_area_id',
        'normalized_date', 'data_quality_score'
    ]
    
    all_citizens = all_citizens[[col for col in columns_to_keep if col in all_citizens.columns]]
    
    # Deduplicar: manter afetado se cidadão caiu em mais de uma área
    all_citizens = all_citizens.sort_values('affected_by_flooding', ascending=False)
    all_citizens = all_citizens.drop_duplicates(subset=['citizen_id'], keep='first')
    
    all_citizens['processing_date'] = pd.Timestamp.now()
    
    # Adicionar estatísticas
    logger.info(f"  Total avaliado: {len(all_citizens)}")
    logger.info(f"  Afetados: {all_citizens['affected_by_flooding'].sum()}")
    logger.info(f"  Não afetados: {(~all_citizens['affected_by_flooding']).sum()}")
    
    return all_citizens


def _s3():
    import boto3
    kwargs = {'region_name': AWS_S3_REGION_NAME}
    if AWS_ENDPOINT_URL:
        kwargs['endpoint_url'] = AWS_ENDPOINT_URL
    if AWS_ACCESS_KEY_ID:
        kwargs['aws_access_key_id'] = AWS_ACCESS_KEY_ID
    if AWS_SECRET_ACCESS_KEY:
        kwargs['aws_secret_access_key'] = AWS_SECRET_ACCESS_KEY
    return boto3.client('s3', **kwargs)


def save_to_gold(gdf, filename):
    """Salva dados processados na camada Gold (local + S3)."""
    filepath = Path(LOCAL_GOLD_USE_CASE) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(str(filepath))
    logger.info(f"✓ Salvo Gold: {filepath}")
    try:
        s3 = _s3()
        s3_key = f"{S3_GOLD_PREFIX}{filename}"
        s3.upload_file(str(filepath), AWS_S3_GOLD_BUCKET, s3_key)
        logger.info(f"✓ Upload S3: s3://{AWS_S3_GOLD_BUCKET}/{s3_key}")
    except Exception as e:
        logger.warning(f"⚠ Upload S3 falhou: {e}")


def silver_ready() -> tuple[bool, bool]:
    """Verifica se silver de áreas e cidadãos existem no bucket S3."""
    import boto3, os
    from config import AWS_S3_SILVER_BUCKET, AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME, USE_CASE
    kwargs = {'region_name': AWS_S3_REGION_NAME}
    if AWS_ENDPOINT_URL:
        kwargs['endpoint_url'] = AWS_ENDPOINT_URL
    if AWS_ACCESS_KEY_ID:
        kwargs['aws_access_key_id'] = AWS_ACCESS_KEY_ID
    if AWS_SECRET_ACCESS_KEY:
        kwargs['aws_secret_access_key'] = AWS_SECRET_ACCESS_KEY
    s3 = boto3.client('s3', **kwargs)
    try:
        keys = {o['Key'] for o in s3.list_objects_v2(Bucket=AWS_S3_SILVER_BUCKET, Prefix=f"{USE_CASE}/").get('Contents', [])}
    except Exception:
        keys = set()
    has_areas    = any(f"silver_{FLOODING_AREAS_FILE}" in k for k in keys)
    has_citizens = any(f"silver_{CITIZENS_FILE}"       in k for k in keys)
    return has_areas, has_citizens


def process_gold():
    """
    Orquestrador: processamento geoespacial completo
    """
    logger.info("=" * 60)
    logger.info("GOLD PROCESSOR - Batimento geográfico")
    logger.info("=" * 60)
    
    # Carregar dados normalizados da Silver
    flooding_silver = load_from_silver(f"silver_{FLOODING_AREAS_FILE}")
    citizens_silver = load_from_silver(f"silver_{CITIZENS_FILE}")
    
    # Realizar batimento geográfico
    spatial_joined = perform_spatial_join(flooding_silver, citizens_silver)
    classified = classify_citizens(spatial_joined, flooding_silver)
    
    # Gerar outputs
    affected = generate_affected_citizens(classified)
    unaffected = generate_unaffected_citizens(classified)
    all_summary = generate_all_citizens_summary(classified)
    
    # Salvar em Gold
    save_to_gold(affected, AFFECTED_CITIZENS_FILE)
    save_to_gold(unaffected, UNAFFECTED_CITIZENS_FILE)
    save_to_gold(all_summary, ALL_CITIZENS_FILE)
    
    logger.info("=" * 60)
    logger.info("✓ Gold layer pronta!")
    logger.info("=" * 60)
    
    return affected, unaffected, all_summary


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    process_gold()
