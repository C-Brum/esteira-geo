"""
Configuração centralizada do pipeline
Suporta: AWS S3 real, MinIO local (Docker), e arquivo system local
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ====== STORAGE CONFIGURATION ======
# Detectar ambiente: AWS, MinIO (Docker local), ou File System
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL', None)
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# AWS S3 ou MinIO Buckets
AWS_S3_BRONZE_BUCKET = os.getenv('AWS_S3_BRONZE_BUCKET', 'bronze')
AWS_S3_SILVER_BUCKET = os.getenv('AWS_S3_SILVER_BUCKET', 'silver')
AWS_S3_GOLD_BUCKET = os.getenv('AWS_S3_GOLD_BUCKET', 'gold')

# AWS credentials
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

# Detectar se está usando MinIO (local Docker) ou S3 real
USE_MINIO = AWS_ENDPOINT_URL is not None
USE_S3 = AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and not USE_MINIO

# Local file system paths (fallback para desenvolvimento)
STORAGE_MODE = 'minio' if USE_MINIO else ('s3' if USE_S3 else 'local')
LOCAL_BRONZE_PATH = os.getenv('LOCAL_BRONZE_PATH', '/data/bronze')
LOCAL_SILVER_PATH = os.getenv('LOCAL_SILVER_PATH', '/data/silver')
LOCAL_GOLD_PATH = os.getenv('LOCAL_GOLD_PATH', '/data/gold')

# ====== USE CASE CONFIGURATION ======
# Subdiretório dentro de cada bucket/path para isolar o caso de uso
USE_CASE = os.getenv('USE_CASE', 'enchentes_poa')
LOCAL_BRONZE_USE_CASE = os.path.join(LOCAL_BRONZE_PATH, USE_CASE)
LOCAL_SILVER_USE_CASE = os.path.join(LOCAL_SILVER_PATH, USE_CASE)
LOCAL_GOLD_USE_CASE = os.path.join(LOCAL_GOLD_PATH, USE_CASE)
S3_BRONZE_USE_CASE_PREFIX = f'bronze/{USE_CASE}/'
S3_SILVER_USE_CASE_PREFIX = f'silver/{USE_CASE}/'
S3_GOLD_USE_CASE_PREFIX = f'gold/{USE_CASE}/'

# ====== DATABASE CONFIGURATION ======
RDS_HOST = os.getenv('RDS_HOST', 'localhost')
RDS_PORT = int(os.getenv('RDS_PORT', 5432))
RDS_DATABASE = os.getenv('RDS_NAME', os.getenv('RDS_DATABASE', 'esteira_geo'))
RDS_USER = os.getenv('RDS_USER', 'postgres')
RDS_PASSWORD = os.getenv('RDS_PASSWORD', 'postgrespw')

# ====== LOGGING CONFIGURATION ======
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'logs/pipeline.log')
os.makedirs(os.path.dirname(LOG_FILE) or '.', exist_ok=True)

# ====== PIPELINE STRUCTURE ======
SAMPLE_DATA_DIR = 'data'
os.makedirs(SAMPLE_DATA_DIR, exist_ok=True)
os.makedirs(LOCAL_BRONZE_USE_CASE, exist_ok=True)
os.makedirs(LOCAL_SILVER_USE_CASE, exist_ok=True)
os.makedirs(LOCAL_GOLD_USE_CASE, exist_ok=True)

# S3/MinIO paths (Medallion architecture)
S3_BRONZE_PREFIX = f'bronze/{USE_CASE}/'
S3_SILVER_PREFIX = f'silver/{USE_CASE}/'
S3_GOLD_PREFIX = f'gold/{USE_CASE}/'

# File names
FLOODING_AREAS_FILE = 'flooding_areas_porto_alegre.parquet'
CITIZENS_FILE = 'citizens_data.parquet'
AFFECTED_CITIZENS_FILE = 'affected_citizens.parquet'
UNAFFECTED_CITIZENS_FILE = 'unaffected_citizens.parquet'
ALL_CITIZENS_FILE = 'all_citizens_evaluated.parquet'

# ====== STATUS ======
print(f"✓ Configuration loaded (Mode: {STORAGE_MODE.upper()})")
print(f"  Storage: {STORAGE_MODE.upper()}")
if USE_MINIO:
    print(f"    MinIO: {AWS_ENDPOINT_URL}")
    print(f"    Buckets: {AWS_S3_BRONZE_BUCKET}/{USE_CASE}, {AWS_S3_SILVER_BUCKET}/{USE_CASE}, {AWS_S3_GOLD_BUCKET}/{USE_CASE}")
elif USE_S3:
    print(f"    AWS S3 Region: {AWS_S3_REGION_NAME}")
    print(f"    Buckets: {AWS_S3_BRONZE_BUCKET}/{USE_CASE}, {AWS_S3_SILVER_BUCKET}/{USE_CASE}, {AWS_S3_GOLD_BUCKET}/{USE_CASE}")
else:
    print(f"    Local paths:")
    print(f"      Bronze: {LOCAL_BRONZE_USE_CASE}")
    print(f"      Silver: {LOCAL_SILVER_USE_CASE}")
    print(f"      Gold: {LOCAL_GOLD_USE_CASE}")
print(f"  Use Case: {USE_CASE}")
print(f"  Database: {RDS_HOST}:{RDS_PORT}/{RDS_DATABASE}")
print(f"  Logging: {LOG_FILE}")
