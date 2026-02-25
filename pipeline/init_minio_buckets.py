#!/usr/bin/env python3
"""
Script de inicialização - Cria buckets no MinIO automaticamente
Executado uma única vez na inicialização do pipeline
"""
import boto3
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações do MinIO
MINIO_CONFIG = {
    'endpoint_url': os.getenv('AWS_ENDPOINT_URL', 'http://minio:9000'),
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID', 'minioadmin'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY', 'minioadmin123'),
    'region_name': os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
}

BUCKETS = ['bronze', 'silver', 'gold']
MAX_RETRIES = 5
RETRY_DELAY = 3

def create_buckets():
    """Cria buckets no MinIO com retry logic"""
    
    for attempt in range(MAX_RETRIES):
        try:
            s3_client = boto3.client('s3', **MINIO_CONFIG)
            
            # Listar buckets existentes
            response = s3_client.list_buckets()
            existing_buckets = [b['Name'] for b in response.get('Buckets', [])]
            
            logger.info(f"Buckets existentes: {existing_buckets if existing_buckets else 'NENHUM'}")
            
            # Criar buckets faltantes
            for bucket_name in BUCKETS:
                if bucket_name not in existing_buckets:
                    try:
                        s3_client.create_bucket(Bucket=bucket_name)
                        logger.info(f"✅ Bucket '{bucket_name}' criado com sucesso")
                    except Exception as e:
                        logger.warning(f"⚠️  Erro ao criar bucket '{bucket_name}': {e}")
                else:
                    logger.info(f"✓ Bucket '{bucket_name}' já existe")
            
            # Listar buckets finais
            response = s3_client.list_buckets()
            final_buckets = [b['Name'] for b in response.get('Buckets', [])]
            logger.info(f"✅ Buckets finais: {final_buckets}")
            
            return True
            
        except Exception as e:
            logger.warning(f"Tentativa {attempt + 1}/{MAX_RETRIES} falhou: {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Aguardando {RETRY_DELAY}s antes de tentar novamente...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"❌ Falha ao criar buckets após {MAX_RETRIES} tentativas")
                return False
    
    return False

if __name__ == '__main__':
    logger.info("Iniciando criação de buckets MinIO...")
    success = create_buckets()
    exit(0 if success else 1)
