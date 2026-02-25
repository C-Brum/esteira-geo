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
    LOCAL_SILVER_PATH, LOCAL_GOLD_PATH,
    AWS_S3_GOLD_BUCKET, S3_GOLD_PREFIX,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE
)

logger = logging.getLogger(__name__)


def load_from_silver(filename):
    """Carrega arquivos da camada Silver"""
    filepath = Path(LOCAL_SILVER_PATH) / filename
    logger.info(f"Carregando Silver: {filepath}")
    gdf = gpd.read_parquet(filepath)
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
    all_citizens['processing_date'] = pd.Timestamp.now()
    
    # Adicionar estatísticas
    logger.info(f"  Total avaliado: {len(all_citizens)}")
    logger.info(f"  Afetados: {all_citizens['affected_by_flooding'].sum()}")
    logger.info(f"  Não afetados: {(~all_citizens['affected_by_flooding']).sum()}")
    
    return all_citizens


def save_to_gold(gdf, filename):
    """Salva dados processados na camada Gold"""
    filepath = Path(LOCAL_GOLD_PATH) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(str(filepath))
    logger.info(f"✓ Salvo Gold: {filepath}")
    
    # Upload S3 (opcional)
    try:
        import boto3
        s3 = boto3.client('s3')
        s3_key = f"{S3_GOLD_PREFIX}{filename}"
        s3.upload_file(filepath, AWS_S3_GOLD_BUCKET, s3_key)
        logger.info(f"✓ Upload S3: s3://{AWS_S3_GOLD_BUCKET}/{s3_key}")
    except Exception as e:
        logger.warning(f"⚠ Upload S3 falhou: {e}")


def process_gold():
    """
    Orquestrador: processamento geoespacial completo
    """
    logger.info("=" * 60)
    logger.info("GOLD PROCESSOR - Batimento geográfico")
    logger.info("=" * 60)
    
    # Carregar dados normalizados da Silver
    flooding_silver = load_from_silver(f"silver_flooding_areas_porto_alegre.parquet")
    citizens_silver = load_from_silver(f"silver_citizens_data.parquet")
    
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
