FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema para geospatial
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libffi-dev \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Definir variáveis de ambiente para GDAL
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Copiar requirements
COPY pipeline/requirements.txt .

# Instalar Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do pipeline (copia conteúdo, não a pasta)
COPY pipeline/*.py ./
COPY pipeline/etl ./etl
COPY pipeline/init_minio_buckets.py ./
COPY pipeline/entrypoint.sh ./
COPY pipeline/watchers ./watchers

# Dar permissão de execução ao entrypoint
RUN chmod +x /app/entrypoint.sh

# Criar diretórios para dados e logs
RUN mkdir -p /data/bronze /data/silver /data/gold /app/logs /app/data && \
    chmod -R 755 /app/logs /app/data

# Def user para rodar pipeline
RUN useradd -m -u 1000 esteira && \
    chown -R esteira:esteira /app /data

USER esteira

# Volumes: data layers
VOLUME ["/data/bronze", "/data/silver", "/data/gold"]

# Entrypoint: inicializa buckets e mantém container rodando
ENTRYPOINT ["/app/entrypoint.sh"]
