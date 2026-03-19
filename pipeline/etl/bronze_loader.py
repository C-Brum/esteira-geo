#!/usr/bin/env python3
"""
Bronze Loader — Script auxiliar para upload de arquivos de teste no bucket bronze.

NÃO faz parte do pipeline. Use para popular o bucket bronze com dados de teste
e validar o fluxo completo (watcher → pipeline → silver/gold).

Uso:
    python etl/bronze_loader.py                        # sobe dados sintéticos gerados
    python etl/bronze_loader.py --file meu_arquivo.csv # sobe arquivo específico
"""

import argparse
import logging
import os
import io
import geopandas as gpd
import pandas as pd
import numpy as np
import boto3
from shapely.geometry import Point, Polygon
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração via env (mesmas variáveis do pipeline)
BRONZE_BUCKET = os.getenv('AWS_S3_BRONZE_BUCKET', 'bronze')
USE_CASE      = os.getenv('USE_CASE', 'enchentes_poa')
ENDPOINT_URL  = os.getenv('AWS_ENDPOINT_URL')
ACCESS_KEY    = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
SECRET_KEY    = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123')
REGION        = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')


def _s3():
    kwargs = {'region_name': REGION, 'aws_access_key_id': ACCESS_KEY, 'aws_secret_access_key': SECRET_KEY}
    if ENDPOINT_URL:
        kwargs['endpoint_url'] = ENDPOINT_URL
    return boto3.client('s3', **kwargs)


def upload_file(local_path: str, filename: str = None):
    """Faz upload de um arquivo local para <use_case>/ no bucket bronze."""
    s3 = _s3()
    filename = filename or Path(local_path).name
    key = f"{USE_CASE}/{filename}"
    s3.upload_file(local_path, BRONZE_BUCKET, key)
    logger.info(f"✓ Upload: s3://{BRONZE_BUCKET}/{key}")


def upload_bytes(data: bytes, filename: str):
    """Faz upload de bytes para <use_case>/ no bucket bronze."""
    s3 = _s3()
    key = f"{USE_CASE}/{filename}"
    s3.put_object(Bucket=BRONZE_BUCKET, Key=key, Body=data)
    logger.info(f"✓ Upload: s3://{BRONZE_BUCKET}/{key}")


def generate_flooding_areas() -> gpd.GeoDataFrame:
    """Gera GeoDataFrame com 3 áreas de enchente em Porto Alegre."""
    polygons = [
        Polygon([(-51.30,-30.05),(-51.20,-30.05),(-51.20,-29.95),(-51.30,-29.95),(-51.30,-30.05)]),
        Polygon([(-51.22,-30.03),(-51.18,-30.03),(-51.18,-29.98),(-51.22,-29.98),(-51.22,-30.03)]),
        Polygon([(-51.25,-29.92),(-51.15,-29.92),(-51.15,-29.88),(-51.25,-29.88),(-51.25,-29.92)]),
    ]
    return gpd.GeoDataFrame({
        'area_id': [1, 2, 3],
        'area_name': ['Partenon', 'Centro/Menino Deus', 'Zona Norte'],
        'flood_date': ['2024-06-10', '2024-06-10', '2024-06-10'],
        'severity': ['high', 'very_high', 'medium'],
        'affected_population': [2500, 5000, 1500],
    }, geometry=polygons, crs='EPSG:4326')


def generate_citizens(n_affected=60, n_safe=40, id_offset=0) -> gpd.GeoDataFrame:
    """Gera GeoDataFrame com cidadãos dentro e fora das áreas de enchente."""
    np.random.seed(42 + id_offset)
    risk_bases  = [(-51.24,-30.01), (-51.22,-30.01), (-51.20,-29.90)]
    safe_bases  = [(-51.10,-29.80), (-51.40,-30.15)]

    def rand_points(bases, n, scale):
        pts = []
        for _ in range(n):
            b = bases[np.random.randint(len(bases))]
            pts.append(Point(np.random.normal(b[0], scale), np.random.normal(b[1], scale)))
        return pts

    points = rand_points(risk_bases, n_affected, 0.03) + rand_points(safe_bases, n_safe, 0.05)
    total  = n_affected + n_safe
    ids    = list(range(id_offset, id_offset + total))

    return gpd.GeoDataFrame({
        'citizen_id': ids,
        'name': [f"Citizen_{i:03d}" for i in ids],
        'address': [f"Rua {i}, Porto Alegre" for i in ids],
        'phone': [f"51 99999-{i:04d}" for i in ids],
        'registration_date': pd.date_range('2024-01-01', periods=total),
    }, geometry=points, crs='EPSG:4326')


def upload_synthetic_data():
    """Gera e faz upload dos dados sintéticos de teste para o bucket bronze."""
    logger.info("Gerando e enviando dados sintéticos para o bucket bronze...")

    # Áreas de enchente → GeoJSON
    flooding = generate_flooding_areas()
    buf = io.BytesIO()
    flooding.to_file(buf, driver='GeoJSON')
    upload_bytes(buf.getvalue(), 'flooding_areas_porto_alegre.geojson')

    # Cidadãos → CSV
    citizens = generate_citizens()
    buf = io.BytesIO()
    df = citizens.copy()
    df['longitude'] = df.geometry.x
    df['latitude']  = df.geometry.y
    df.drop(columns=['geometry']).to_csv(buf, index=False)
    upload_bytes(buf.getvalue(), 'citizens_data.csv')

    logger.info("✓ Dados sintéticos enviados. O watcher deve detectar e disparar o pipeline.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload de arquivos de teste para o bucket bronze')
    parser.add_argument('--file', help='Arquivo local para upload (opcional)')
    args = parser.parse_args()

    if args.file:
        upload_file(args.file)
    else:
        upload_synthetic_data()
