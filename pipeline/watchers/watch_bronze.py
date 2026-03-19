"""
Watcher S3/MinIO — Esteira Geo

Monitora TODO o bucket bronze (sem prefix fixo).
Detecta o use_case pelo prefixo do arquivo: <use_case>/arquivo.csv
Dispara o pipeline com USE_CASE correto para cada grupo de arquivos.
"""

import os
import time
import logging
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '10'))
BRONZE_BUCKET = os.getenv('AWS_S3_BRONZE_BUCKET', 'bronze')
WATCHED_EXTS  = {'.csv', '.geojson', '.parquet'}


def get_s3_client():
    kwargs = {
        'aws_access_key_id':     os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123'),
        'region_name':           os.getenv('AWS_S3_REGION_NAME', 'us-east-1'),
    }
    endpoint = os.getenv('AWS_ENDPOINT_URL')
    if endpoint:
        kwargs['endpoint_url'] = endpoint
    return boto3.client('s3', **kwargs)


def list_pending(s3) -> dict[str, list[str]]:
    """
    Lista arquivos pendentes agrupados por use_case.
    Ignora qualquer key que contenha /processados/.
    Retorna: { 'enchentes_poa': ['enchentes_poa/file.csv', ...], ... }
    """
    try:
        resp = s3.list_objects_v2(Bucket=BRONZE_BUCKET)
    except ClientError as e:
        logger.error(f"Erro ao listar bucket: {e}")
        return {}

    grouped = defaultdict(list)
    for obj in resp.get('Contents', []):
        key = obj['Key']
        parts = key.split('/')
        # Precisa ter pelo menos use_case/filename e não estar em processados/
        if len(parts) < 2 or 'processados' in parts:
            continue
        filename = parts[-1]
        if not filename:
            continue
        if os.path.splitext(filename)[1].lower() not in WATCHED_EXTS:
            continue
        use_case = parts[0]
        grouped[use_case].append(key)

    return dict(grouped)


def run_pipeline(use_case: str):
    logger.info(f"[{use_case}] Disparando pipeline...")
    result = subprocess.run(
        [sys.executable, '/app/main.py'],
        cwd='/app',
        env={**os.environ, 'USE_CASE': use_case, 'PYTHONUNBUFFERED': '1'},
    )
    if result.returncode == 0:
        logger.info(f"[{use_case}] Pipeline concluído com sucesso")
    else:
        logger.error(f"[{use_case}] Pipeline falhou com código {result.returncode}")


def main():
    logger.info(f"Watcher S3 iniciado: bucket={BRONZE_BUCKET}, poll={POLL_INTERVAL}s (multi-use-case)")
    s3 = get_s3_client()

    # Processar arquivos já existentes ao iniciar
    pending = list_pending(s3)
    if pending:
        logger.info(f"Arquivos encontrados no início: {dict(pending)}")
        for use_case in pending:
            run_pipeline(use_case)

    known = set()

    while True:
        time.sleep(POLL_INTERVAL)
        pending = list_pending(s3)
        current = {key for keys in pending.values() for key in keys}
        new_files = current - known

        if new_files:
            # Agrupar novos arquivos por use_case e disparar um pipeline por grupo
            new_by_use_case = defaultdict(list)
            for key in new_files:
                use_case = key.split('/')[0]
                new_by_use_case[use_case].append(key)

            for use_case, files in new_by_use_case.items():
                logger.info(f"[{use_case}] Novos arquivos: {files}")
                run_pipeline(use_case)

            known = set()
        else:
            known = current


if __name__ == '__main__':
    main()
