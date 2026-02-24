# 🐳 Docker Setup - Quick Start

Ambiente completo dockerizado para **desenvolvimento e teste local** da esteira geoespacial.

## ⚡ Início Rápido (2 minutos)

### 1️⃣ Iniciar o Ambiente

```bash
# Clone ou navegue para o projeto
cd esteira-geo

# Inicie todos os serviços
docker-compose up -d

# Aguarde inicialização (~30 segundos)
docker-compose ps
```

**Status esperado**:
```
NAME              STATUS              PORTS
esteira-postgis   Up (healthy)        5432
esteira-minio     Up (healthy)        9000, 9001
esteira-pipeline  Up                  -
esteira-web       Up                  5000
```

### 2️⃣ Acessar Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Flask Dashboard** | http://localhost:5000 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 |
| **PostgreSQL** | localhost:5432 | esteira_user / esteira_local_2025 |

### 3️⃣ Executar Pipeline ETL

```bash
# Opção 1: Usar script helper (Windows)
.\docker.ps1 pipeline

# Opção 2: Docker direto
docker-compose exec pipeline python /app/pipeline/main.py

# Resultado esperado:
# ✓ PIPELINE CONCLUÍDO COM SUCESSO!
#   Cidadãos Atingidos: 60
#   Cidadãos Não Atingidos: 40
#   Total Avaliado: 100
```

## 🛠️ Windows PowerShell Helper

Script convienente para gerenciar Docker:

```bash
# Ver status
.\docker.ps1 status

# Executar pipeline
.\docker.ps1 pipeline

# Acessar shell (para debugging)
.\docker.ps1 shell

# Ver logs em tempo real
.\docker.ps1 logs pipeline
.\docker.ps1 logs postgis
.\docker.ps1 logs web

# Acessar banco de dados (psql interativo)
.\docker.ps1 db

# Abrir MinIO UI
.\docker.ps1 minio

# Executar testes
.\docker.ps1 test

# Parar ambiente
.\docker.ps1 down

# Limpar tudo (remover volumes)
.\docker.ps1 clean
```

## 🐧 Linux/macOS Shell Helper

Para desenvolvimento em Linux ou macOS, use scripts bash:

```bash
# Fazer scripts executáveis
chmod +x docker.sh debug.sh setup.sh

# Ver status
./docker.sh status

# Executar pipeline
./docker.sh pipeline

# Acessar shell
./docker.sh shell

# Ver logs
./docker.sh logs pipeline
./docker.sh logs postgis

# Banco de dados
./docker.sh db

# Abrir MinIO
./docker.sh minio

# Testes
./debug.sh test-all
./debug.sh validate

# Parar
./docker.sh down
```

**OU use Makefile (mais padrão)**:

```bash
# Status
make status

# Pipeline
make pipeline

# Testes
make test

# Logs
make logs-pipeline

# Banco
make db

# Parar
make down
```

Veja [SCRIPTS_BASH.md](./SCRIPTS_BASH.md) para documentação completa dos scripts bash

## 📊 Verificar Dados

### Em MinIO (S3 simulado)

```bash
# Via UI: http://localhost:9001
# Buckets disponíveis:
# - bronze/    → dados brutos (GeoParquet)
# - silver/    → dados normalizados
# - gold/      → dados processados (spatial join result)
```

### Em PostgreSQL (PostGIS)

```bash
# Via helper
.\docker.ps1 db

# Dentro do psql:
esteira_geo=# SELECT COUNT(*) FROM citizens;
esteira_geo=# SELECT COUNT(*) FROM citizens WHERE affected_by_flooding = TRUE;
esteira_geo=# SELECT * FROM v_citizens_summary;
\q  # Sair
```

## 🧪 Testes Específicos por Camada

```bash
# Bronze (geração de dados)
docker-compose exec pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"

# Silver (normalização)
docker-compose exec pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"

# Gold (spatial join - a magia acontece aqui!)
docker-compose exec pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"

# PostGIS (carrega dados no banco)
docker-compose exec pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

## 📁 Estrutura de Volumes

Dados persistem em volumes Docker:

```bash
# Acessar arquivos locais
docker cp esteira-pipeline:/data/bronze/flooding_areas_porto_alegre.parquet .

# Ou dentro do container
docker-compose exec pipeline bash
ls -la /data/bronze/
ls -la /data/silver/
ls -la /data/gold/
```

## 🔄 Pipeline Flow

```
┌─────────────────┐
│ Bronze Layer    │  generating data/fetching from sources
│ (raw data)      │  3 flooding areas + 100 citizens
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Silver Layer        │  normalizing/validating
│ (normalized data)   │  geometry validation, type standardization
└────────┬────────────┘
         │
         ▼
┌──────────────────────────┐
│ Gold Layer               │  processing
│ (processed + analyzed)   │  **Spatial Join**: citizen points within flood polygons
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ PostGIS                  │  persistence
│ (RDS + spatial indexes)  │  INSERT with ST_GeomFromText
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Flask Dashboard          │  visualization
│ (API + web UI)           │  querying PostGIS + rendering results
└──────────────────────────┘

Output:
  ✓ affected_citizens.parquet (60)
  ✓ unaffected_citizens.parquet (40)  
  ✓ all_citizens_evaluated.parquet (100)
  ✓ PostgreSQL tables with spatial indexes
```

## 🐛 Troubleshooting

### PostgreSQL não conecta

```bash
# Verificar saúde
docker-compose exec postgis pg_isready -U esteira_user

# Ver logs
docker-compose logs postgis

# Forçar recriação
docker-compose down postgis
docker-compose up -d postgis
```

### MinIO não inicializa

```bash
# Verificar buckets foram criados
docker-compose logs minio-init

# Tentar reconectar
docker-compose down minio minio-init
docker-compose up -d minio minio-init
```

### Pipeline container não executa

```bash
# Acessar shell
.\docker.ps1 shell
cd /app
python pipeline/main.py  # Rodar manualmente

# Ver erros detalhados
docker-compose logs pipeline
```

### Limpar e recomeçar

```bash
# Parar tudo
docker-compose down

# Remover volumes (cuidado: deleta dados!)
docker-compose down -v

# Reconstruir imagens
docker-compose build --no-cache

# Reiniciar
docker-compose up -d
```

## 📦 Serviços & Imagens

| Serviço | Imagem | Descrição |
|---------|--------|-----------|
| **postgis** | postgis:13-3.2 | PostgreSQL com extensão PostGIS |
| **minio** | minio/minio:latest | S3-compatible object storage |
| **minio-init** | minio/mc:latest | Cliente para criar buckets |
| **pipeline** | Custom (Dockerfile) | ETL Python com gdal/geopandas |
| **web** | Custom (Dockerfile.web) | Flask app com Gunicorn |

## 🔐 Credenciais Padrão

```
PostgreSQL:
  Host: postgis (ou localhost:5432)
  User: esteira_user
  Pass: esteira_local_2025
  Database: esteira_geo

MinIO:
  Endpoint: http://minio:9000 (ou localhost:9001 para UI)
  Access Key: minioadmin
  Secret Key: minioadmin123
```

## 📚 Arquivos Importantes

- `docker-compose.yml` - Orquestração de containers
- `pipeline/Dockerfile` - Imagem do pipeline ETL
- `pipeline/Dockerfile.web` - Imagem da Flask app
- `.env.docker` - Variáveis de ambiente
- `pipeline/DOCKER.md` - Documentação completa
- `docker.ps1` - Helper script para Windows

## 🚀 Próximos Passos

1. ✅ Ambiente Docker rodando
2. ✅ Pipeline ETL funcionando
3. ▶️ **Modificar dados de entrada** (customize bronze_loader.py)
4. ▶️ **Integrar suas queries PostGIS** (customize postgis_loader.py)
5. ▶️ **Adicionar endpoints Flask** (customize app.py)
6. ▶️ **Deploy em cloud** (usar Terraform + Ansible)

## 📖 Documentação Completa

- [pipeline/DOCKER.md](./pipeline/DOCKER.md) - Guia detalhado
- [pipeline/README.md](./pipeline/README.md) - Documentação do pipeline
- [README.md](./README.md) - Documentação principal do projeto
