"""
Silver Processor - Lê arquivos do bucket bronze (S3/MinIO) e normaliza para Silver.

Cenários suportados:
  - Só áreas    → salva silver de áreas
  - Só cidadãos → salva silver de cidadãos
  - Ambos       → salva ambos

Retorna dict com chaves 'flooding' e/ou 'citizens' (GeoDataFrames presentes).
"""

import io
import geopandas as gpd
import pandas as pd
import boto3
import logging
from pathlib import Path
from config import (
    AWS_S3_BRONZE_BUCKET, AWS_S3_SILVER_BUCKET,
    AWS_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_REGION_NAME,
    USE_CASE, LOCAL_SILVER_USE_CASE,
    FLOODING_AREAS_FILE, CITIZENS_FILE,
)

logger = logging.getLogger(__name__)

PROCESSED_PREFIX = f"automatizado/{USE_CASE}/processados/"
BRONZE_PREFIX    = f"automatizado/{USE_CASE}/"
SILVER_PREFIX    = f"{USE_CASE}/"
WATCHED_EXTS     = {'.csv', '.geojson', '.parquet'}


def _s3():
    kwargs = {'region_name': AWS_S3_REGION_NAME}
    if AWS_ENDPOINT_URL:
        kwargs['endpoint_url'] = AWS_ENDPOINT_URL
    if AWS_ACCESS_KEY_ID:
        kwargs['aws_access_key_id'] = AWS_ACCESS_KEY_ID
    if AWS_SECRET_ACCESS_KEY:
        kwargs['aws_secret_access_key'] = AWS_SECRET_ACCESS_KEY
    return boto3.client('s3', **kwargs)


def _list_bronze(s3) -> list[str]:
    resp = s3.list_objects_v2(Bucket=AWS_S3_BRONZE_BUCKET, Prefix=BRONZE_PREFIX)
    keys = []
    for obj in resp.get('Contents', []):
        key = obj['Key']
        if PROCESSED_PREFIX and key.startswith(PROCESSED_PREFIX):
            continue
        filename = key.split('/')[-1]
        if not filename:
            continue
        if Path(filename).suffix.lower() in WATCHED_EXTS:
            keys.append(key)
    return keys


def _read_from_s3(s3, key: str) -> gpd.GeoDataFrame:
    logger.info(f"Lendo s3://{AWS_S3_BRONZE_BUCKET}/{key}")
    data = s3.get_object(Bucket=AWS_S3_BRONZE_BUCKET, Key=key)['Body'].read()
    ext  = Path(key).suffix.lower()

    if ext == '.csv':
        df = pd.read_csv(io.BytesIO(data), dtype={'citizen_id': str, 'document_number': str})
        df.rename(columns={'registered_date': 'registration_date', 'data_registro': 'registration_date'}, inplace=True)
        if 'latitude' not in df.columns or 'longitude' not in df.columns:
            raise ValueError(f"CSV {key} sem colunas latitude/longitude")
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['longitude'], df['latitude']), crs='EPSG:4326')
        gdf = gdf.drop(columns=['latitude', 'longitude'])
    elif ext == '.geojson':
        gdf = gpd.read_file(io.BytesIO(data))
    elif ext == '.parquet':
        gdf = gpd.read_parquet(io.BytesIO(data))
    else:
        raise ValueError(f"Formato não suportado: {ext}")

    logger.info(f"✓ Lido: {len(gdf)} registros")
    return gdf


def _is_flooding_file(filename: str) -> bool:
    name = filename.lower()
    return 'flooding' in name or 'areas' in name or 'enchente' in name


def _normalize_citizens(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf['geometry'] = gdf['geometry'].apply(lambda x: x if x.is_valid else x.buffer(0))
    gdf = gdf[gdf['geometry'].is_valid].copy()
    try:
        gdf['citizen_id'] = gdf['citizen_id'].astype(str)
    except (ValueError, TypeError, KeyError):
        pass
    if 'registered_date' in gdf.columns and 'registration_date' not in gdf.columns:
        gdf.rename(columns={'registered_date': 'registration_date'}, inplace=True)
    if 'registration_date' in gdf.columns:
        gdf['registration_date'] = pd.to_datetime(gdf['registration_date'], errors='coerce')
    gdf = gdf.drop_duplicates(subset=['citizen_id'])
    gdf['normalized_date']    = pd.Timestamp.now()
    gdf['data_quality_score'] = 1.0
    return gdf


def _normalize_flooding(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf['geometry'] = gdf['geometry'].apply(lambda x: x if x.is_valid else x.buffer(0))
    gdf = gdf[gdf['geometry'].is_valid].copy()
    if 'area_id' in gdf.columns:
        gdf = gdf.drop_duplicates(subset=['area_id'])
        gdf['area_id'] = gdf['area_id'].astype('int64')
    if 'flood_date' in gdf.columns:
        gdf['flood_date'] = pd.to_datetime(gdf['flood_date'], errors='coerce')
    if 'affected_population' in gdf.columns:
        gdf['affected_population'] = pd.to_numeric(gdf['affected_population'], errors='coerce').fillna(0).astype('int64')
    gdf['normalized_date']    = pd.Timestamp.now()
    gdf['data_quality_score'] = 1.0
    return gdf


def _save_to_silver(s3, gdf: gpd.GeoDataFrame, filename: str):
    local_path = Path(LOCAL_SILVER_USE_CASE) / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(str(local_path))
    s3_key = f"{SILVER_PREFIX}{filename}"
    s3.upload_file(str(local_path), AWS_S3_SILVER_BUCKET, s3_key)
    logger.info(f"✓ Silver salvo: s3://{AWS_S3_SILVER_BUCKET}/{s3_key}")


def _move_to_processed(s3, key: str):
    if not PROCESSED_PREFIX:
        logger.info(f"→ Modo exploratório: {key.split('/')[-1]} mantido no lugar")
        return
    filename = key.split('/')[-1]
    dest = f"{PROCESSED_PREFIX}{filename}"
    s3.copy_object(Bucket=AWS_S3_BRONZE_BUCKET,
                   CopySource={'Bucket': AWS_S3_BRONZE_BUCKET, 'Key': key},
                   Key=dest)
    s3.delete_object(Bucket=AWS_S3_BRONZE_BUCKET, Key=key)
    logger.info(f"→ Movido para processados/: {filename}")


def silver_exists(filename: str) -> bool:
    """Verifica se um arquivo silver existe no bucket S3."""
    try:
        s3 = _s3()
        s3.head_object(Bucket=AWS_S3_SILVER_BUCKET, Key=f"{SILVER_PREFIX}{filename}")
        return True
    except Exception:
        return False


def process_silver(bronze_prefix: str = None, move_files: bool = True) -> dict:
    """
    bronze_prefix: sobrescreve BRONZE_PREFIX (usado pelo Jupyter para apontar para exploratorio/)
    move_files: se False, não move arquivos para processados/ (modo exploratório)
    """
    """
    Lê arquivos pendentes do bronze, normaliza e salva no silver.

    Retorna dict com as chaves presentes após o processamento:
      - 'flooding': GeoDataFrame de áreas (se processado ou já existia no silver)
      - 'citizens': GeoDataFrame de cidadãos (se processado nesta execução)
    """
    logger.info("=" * 60)
    logger.info("SILVER PROCESSOR")
    logger.info("=" * 60)

    # Suporte a modo exploratório: sobrescreve prefixos sem alterar variáveis de módulo
    global BRONZE_PREFIX, PROCESSED_PREFIX
    _bronze_prefix    = bronze_prefix or BRONZE_PREFIX
    _processed_prefix = PROCESSED_PREFIX if move_files else None

    # Aplica temporariamente
    _orig_bronze, _orig_processed = BRONZE_PREFIX, PROCESSED_PREFIX
    BRONZE_PREFIX    = _bronze_prefix
    PROCESSED_PREFIX = _processed_prefix

    s3   = _s3()
    keys = _list_bronze(s3)

    if not keys:
        BRONZE_PREFIX, PROCESSED_PREFIX = _orig_bronze, _orig_processed
        raise RuntimeError("Nenhum arquivo encontrado no bucket bronze para processar.")

    flooding_frames = []
    citizen_frames  = []

    for key in keys:
        filename = key.split('/')[-1]
        try:
            gdf = _read_from_s3(s3, key)
            if _is_flooding_file(filename):
                flooding_frames.append(_normalize_flooding(gdf))
                logger.info(f"✓ Áreas de enchente: {filename}")
            else:
                citizen_frames.append(_normalize_citizens(gdf))
                logger.info(f"✓ Cidadãos: {filename}")
            _move_to_processed(s3, key)
        except Exception as e:
            logger.error(f"✗ Erro ao processar {filename}: {e}")

    result = {}

    # Áreas de enchente
    if flooding_frames:
        new_flooding = gpd.GeoDataFrame(
            pd.concat(flooding_frames, ignore_index=True), geometry='geometry', crs='EPSG:4326'
        )
        # Mesclar com silver existente (acumulativo)
        silver_key = f"{SILVER_PREFIX}silver_{FLOODING_AREAS_FILE}"
        try:
            obj = s3.get_object(Bucket=AWS_S3_SILVER_BUCKET, Key=silver_key)
            existing = gpd.read_parquet(io.BytesIO(obj['Body'].read()))
            combined = gpd.GeoDataFrame(
                pd.concat([existing, new_flooding], ignore_index=True),
                geometry='geometry', crs='EPSG:4326'
            )
            logger.info(f"✓ Mesclando {len(existing)} áreas existentes + {len(new_flooding)} novas")
        except Exception:
            combined = new_flooding
        if 'area_id' in combined.columns:
            combined['area_id'] = combined['area_id'].astype(str)
            combined = combined.drop_duplicates(subset=['area_id'], keep='last')
        flooding_silver = gpd.GeoDataFrame(combined, geometry='geometry', crs='EPSG:4326')
        _save_to_silver(s3, flooding_silver, f"silver_{FLOODING_AREAS_FILE}")
        result['flooding'] = flooding_silver
        logger.info(f"✓ Áreas salvas no silver: {len(flooding_silver)} registros")
    elif silver_exists(f"silver_{FLOODING_AREAS_FILE}"):
        obj = _s3().get_object(Bucket=AWS_S3_SILVER_BUCKET, Key=f"{SILVER_PREFIX}silver_{FLOODING_AREAS_FILE}")
        result['flooding'] = gpd.read_parquet(io.BytesIO(obj['Body'].read()))
        logger.info(f"✓ Áreas reutilizadas do silver: {len(result['flooding'])} registros")

    # Cidadãos
    if citizen_frames:
        new_citizens = gpd.GeoDataFrame(
            pd.concat(citizen_frames, ignore_index=True), geometry='geometry', crs='EPSG:4326'
        )
        # Mesclar com silver existente (acumulativo)
        silver_key = f"{SILVER_PREFIX}silver_{CITIZENS_FILE}"
        try:
            obj = s3.get_object(Bucket=AWS_S3_SILVER_BUCKET, Key=silver_key)
            existing = gpd.read_parquet(io.BytesIO(obj['Body'].read()))
            combined = gpd.GeoDataFrame(
                pd.concat([existing, new_citizens], ignore_index=True),
                geometry='geometry', crs='EPSG:4326'
            )
            logger.info(f"✓ Mesclando {len(existing)} existentes + {len(new_citizens)} novos")
        except Exception:
            combined = new_citizens
        combined['citizen_id'] = combined['citizen_id'].astype(str)
        combined = combined.drop_duplicates(subset=['citizen_id'], keep='last')
        citizens_silver = gpd.GeoDataFrame(combined, geometry='geometry', crs='EPSG:4326')
        _save_to_silver(s3, citizens_silver, f"silver_{CITIZENS_FILE}")
        result['citizens'] = citizens_silver
        logger.info(f"✓ Cidadãos salvos no silver: {len(citizens_silver)} registros")

    if not result:
        BRONZE_PREFIX, PROCESSED_PREFIX = _orig_bronze, _orig_processed
        raise RuntimeError("Nenhum arquivo válido processado do bronze.")

    BRONZE_PREFIX, PROCESSED_PREFIX = _orig_bronze, _orig_processed
    logger.info("=" * 60)
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    process_silver()
