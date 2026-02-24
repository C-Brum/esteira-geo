"""
Bronze Loader - Cria dados de exemplo e carrega no bucket Bronze


Caso de uso: Batimento geográfico de áreas atingidas por enchentes no Rio Grande do Sul
- Dados de áreas atingidas por enchente em Porto Alegre (polígonos)
- Dados de cidadãos com coordenadas (100 registros, alguns em área atingida)
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon
import numpy as np
import logging
from config import (
    SAMPLE_DATA_DIR, FLOODING_AREAS_FILE, CITIZENS_FILE,
    AWS_S3_BRONZE_BUCKET, S3_BRONZE_PREFIX,
    USE_MINIO, USE_S3, STORAGE_MODE,
    AWS_ENDPOINT_URL, LOCAL_BRONZE_PATH
)

logger = logging.getLogger(__name__)


def create_flooding_areas_geoparquet():
    """
    Cria GeoDataFrame com polígonos de áreas atingidas por enchente em Porto Alegre
    Coordenadas aproximadas de Porto Alegre: -30.0, -51.2
    """
    logger.info("Gerando dados de áreas de enchente (Porto Alegre)...")
    
    # Polígonos de exemplo (áreas atingidas por enchente)
    # Porto Alegre fica por volta de: -30.0326, -51.2093
    polygons = [
        # Área 1: Partenon (próximo ao Rio Grande do Sul)
        Polygon([
            (-30.05, -51.30),
            (-30.05, -51.20),
            (-29.95, -51.20),
            (-29.95, -51.30),
            (-30.05, -51.30)
        ]),
        # Área 2: Centro/Menino Deus
        Polygon([
            (-30.03, -51.22),
            (-30.03, -51.18),
            (-29.98, -51.18),
            (-29.98, -51.22),
            (-30.03, -51.22)
        ]),
        # Área 3: Zona Norte
        Polygon([
            (-29.92, -51.25),
            (-29.92, -51.15),
            (-29.88, -51.15),
            (-29.88, -51.25),
            (-29.92, -51.25)
        ]),
    ]
    
    gdf = gpd.GeoDataFrame(
        {
            'area_id': [1, 2, 3],
            'area_name': ['Partenon', 'Centro/Menino Deus', 'Zona Norte'],
            'flood_date': ['2024-06-10', '2024-06-10', '2024-06-10'],
            'severity': ['high', 'very_high', 'medium'],
            'affected_population': [2500, 5000, 1500]
        },
        geometry=polygons,
        crs='EPSG:4326'
    )
    
    logger.info(f"✓ Criado GeoDataFrame com {len(gdf)} áreas de enchente")
    return gdf


def create_citizens_geoparquet():
    """
    Cria GeoDataFrame com dados de cidadãos (100 registros)
    Alguns estão dentro de áreas atingidas, outros não
    """
    logger.info("Gerando dados de cidadãos (100 registros)...")
    
    np.random.seed(42)
    
    # Coordenadas base (Porto Alegre)
    base_lat = -30.0326
    base_lon = -51.2093
    
    # Gerar 60 cidadãos em área de risco (dentro dos polígonos de enchente)
    risk_coords = [
        (-30.01, -51.24),  # Área 1
        (-30.01, -51.22),  # Área 2
        (-29.90, -51.20),  # Área 3
    ]
    
    affected_points = []
    for _ in range(60):
        base = risk_coords[np.random.randint(0, len(risk_coords))]
        lat = base[0] + np.random.uniform(-0.02, 0.02)
        lon = base[1] + np.random.uniform(-0.02, 0.02)
        affected_points.append(Point(lon, lat))
    
    # Gerar 40 cidadãos fora de área de risco
    safe_coords = [
        (-29.80, -51.10),  # Zona sul (segura)
        (-30.15, -51.40),  # Zona leste (segura)
    ]
    
    safe_points = []
    for _ in range(40):
        base = safe_coords[np.random.randint(0, len(safe_coords))]
        lat = base[0] + np.random.uniform(-0.02, 0.02)
        lon = base[1] + np.random.uniform(-0.02, 0.02)
        safe_points.append(Point(lon, lat))
    
    all_points = affected_points + safe_points
    
    # Criar DataFrame
    names = [f"Citizen_{i:03d}" for i in range(100)]
    addresses = [f"Rua {i}, nº {np.random.randint(1, 1000)}, Porto Alegre" for i in range(100)]
    
    gdf = gpd.GeoDataFrame(
        {
            'citizen_id': range(100),
            'name': names,
            'address': addresses,
            'phone': [f"51 99999-{i:04d}" for i in range(100)],
            'registration_date': pd.date_range('2024-01-01', periods=100),
        },
        geometry=all_points,
        crs='EPSG:4326'
    )
    
    logger.info(f"✓ Criado GeoDataFrame com {len(gdf)} cidadãos")
    return gdf


def save_to_geoparquet(gdf, filename):
    """Salva GeoDataFrame como GeoParquet"""
    filepath = f"{SAMPLE_DATA_DIR}/{filename}"
    gdf.to_parquet(filepath)
    logger.info(f"✓ Salvo: {filepath}")
    return filepath


def upload_to_s3(local_path, s3_filename):
    """
    Upload para S3 (MinIO/AWS)
    Suporta: MinIO (Docker local) e AWS S3 real
    """
    if STORAGE_MODE == 'local':
        logger.info(f"  (Local mode - arquivo salvo em disco)")
        return
    
    try:
        import boto3
        
        # Configurar cliente S3/MinIO
        if USE_MINIO:
            # MinIO no Docker
            s3 = boto3.client(
                's3',
                endpoint_url=AWS_ENDPOINT_URL,
                aws_access_key_id='minioadmin',
                aws_secret_access_key='minioadmin123',
                region_name='us-east-1'
            )
            logger.info(f"  Uploading to MinIO: {AWS_ENDPOINT_URL}")
        else:
            # AWS S3 real
            s3 = boto3.client('s3')
            logger.info(f"  Uploading to AWS S3")
        
        s3_key = f"{S3_BRONZE_PREFIX}{s3_filename}"
        s3.upload_file(local_path, AWS_S3_BRONZE_BUCKET, s3_key)
        logger.info(f"✓ Upload: s3://{AWS_S3_BRONZE_BUCKET}/{s3_key}")
    except Exception as e:
        logger.warning(f"⚠ Upload failed: {e}")
        logger.info("  Files available locally")


def load_sample_data():
    """
    Orquestrador: cria dados de exemplo e carrega em Bronze
    """
    logger.info("=" * 60)
    logger.info("BRONZE LOADER - Criando dados de exemplo")
    logger.info("=" * 60)
    
    # Criar diretório de dados se não existir
    import os
    os.makedirs(SAMPLE_DATA_DIR, exist_ok=True)
    
    # Gerar dados de exemplo
    flooding_gdf = create_flooding_areas_geoparquet()
    citizens_gdf = create_citizens_geoparquet()
    
    # Salvar localmente
    flooding_path = save_to_geoparquet(flooding_gdf, FLOODING_AREAS_FILE)
    citizens_path = save_to_geoparquet(citizens_gdf, CITIZENS_FILE)
    
    # Upload para S3
    upload_to_s3(flooding_path, FLOODING_AREAS_FILE)
    upload_to_s3(citizens_path, CITIZENS_FILE)
    
    logger.info("=" * 60)
    logger.info("✓ Bronze layer pronta!")
    logger.info("=" * 60)
    
    return flooding_gdf, citizens_gdf


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    load_sample_data()
