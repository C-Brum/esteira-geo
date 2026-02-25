#!/bin/bash
# Entrypoint script - Inicializa o ambiente antes de executar o pipeline

set -e

echo "🔧 Iniciando configuração do ambiente..."

# Inicializar buckets MinIO
echo "📦 Criando buckets MinIO..."
python /app/init_minio_buckets.py

if [ $? -eq 0 ]; then
    echo "✅ Buckets MinIO inicializados com sucesso"
else
    echo "⚠️  Aviso: Problema ao criar buckets MinIO"
fi

# Manter container rodando
echo "✅ Ambiente pronto. Container será mantido rodando..."
exec tail -f /dev/null
