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

# Copiar código do pipeline
COPY pipeline /app/pipeline
COPY pipeline/etl /app/pipeline/etl

# Criar diretórios para dados
RUN mkdir -p /data/bronze /data/silver /data/gold /app/logs

# Def user para rodar pipeline
RUN useradd -m -u 1000 esteira && chown -R esteira:esteira /app /data

USER esteira

# Volume para logs
VOLUME ["/app/logs", "/data/bronze", "/data/silver", "/data/gold"]

# Default command: manter container rodando
CMD ["tail", "-f", "/dev/null"]
