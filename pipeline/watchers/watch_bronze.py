"""
Watcher S3/MinIO — Esteira Geo

Monitora o bucket bronze via polling S3 (boto3).
Ao detectar arquivos novos em <bucket>/<use_case>/, dispara o pipeline
e move os arquivos processados para <bucket>/<use_case>/processados/.

Funciona com MinIO (Docker local) e AWS S3 real — sem dependência de filesystem.
"""

import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

# Configuração via variáveis de ambiente
POLL_INTERVAL  = int(os.getenv('POLL_INTERVAL', '10'))
USE_CASE       = os.getenv('USE_CASE', 'enchentes_poa')
BRONZE_BUCKET  = os.getenv('AWS_S3_BRONZE_BUCKET', 'bronze')
PREFIX         = f"{USE_CASE}/"
PROCESSED_PREFIX = f"{USE_CASE}/processados/"

# Extensões monitoradas
WATCHED_EXTS = {'.csv', '.geojson', '.parquet'}


def get_s3_client():
    kwargs = {}
    endpoint = os.getenv('AWS_ENDPOINT_URL')
    if endpoint:
        kwargs['endpoint_url'] = endpoint
    kwargs['aws_access_key_id']     = os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin')
    kwargs['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123')
    kwargs['region_name']           = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    return boto3.client('s3', **kwargs)


def list_pending(s3) -> list[str]:
    """Lista objetos no prefix do caso de uso que não estão em processados/."""
    try:
        resp = s3.list_objects_v2(Bucket=BRONZE_BUCKET, Prefix=PREFIX)
    except ClientError as e:
        logger.error(f"Erro ao listar bucket: {e}")
        return []

    pending = []
    for obj in resp.get('Contents', []):
        key = obj['Key']
        # Ignorar subdiretórios (processados/, etc.) e arquivos sintéticos
        if key.startswith(PROCESSED_PREFIX):
            continue
        filename = key.split('/')[-1]
        if not filename:
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in WATCHED_EXTS:
            continue
        pending.append(key)

    return pending


def move_to_processed(s3, key: str):
    """Move objeto para <use_case>/processados/ dentro do mesmo bucket."""
    filename = key.split('/')[-1]
    dest_key = f"{PROCESSED_PREFIX}{filename}"
    try:
        s3.copy_object(
            Bucket=BRONZE_BUCKET,
            CopySource={'Bucket': BRONZE_BUCKET, 'Key': key},
            Key=dest_key,
        )
        s3.delete_object(Bucket=BRONZE_BUCKET, Key=key)
        logger.info(f"→ Movido para processados/: {filename}")
    except ClientError as e:
        logger.error(f"Erro ao mover {key}: {e}")


def run_pipeline():
    logger.info("Mudança detectada no bucket bronze — disparando pipeline...")
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, '/app/main.py'],
        cwd='/app',
        env={**os.environ, 'PYTHONUNBUFFERED': '1'},
    )
    if result.returncode == 0:
        logger.info("Pipeline concluído com sucesso")
    else:
        logger.error(f"Pipeline falhou com código {result.returncode}")


def main():
    logger.info(f"Watcher S3 iniciado: bucket={BRONZE_BUCKET}, prefix={PREFIX}, poll={POLL_INTERVAL}s")
    s3 = get_s3_client()

    # Processar arquivos já existentes no bucket ao iniciar
    pending = list_pending(s3)
    if pending:
        logger.info(f"Arquivos encontrados no início: {pending}")
        run_pipeline()
        for key in list_pending(s3):
            move_to_processed(s3, key)

    known = set()  # após processar (ou se vazio), bucket está limpo

    while True:
        time.sleep(POLL_INTERVAL)
        current = set(list_pending(s3))
        new_files = current - known

        if new_files:
            logger.info(f"Novos arquivos detectados: {new_files}")
            run_pipeline()
            for key in list_pending(s3):
                move_to_processed(s3, key)
            known = set()
        else:
            known = current


if __name__ == '__main__':
    main()
