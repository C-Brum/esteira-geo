# Docker Development Environment

Ambiente completo dockerizado para desenvolvimento e teste local da esteira de processamento geoespacial.

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────┐
│    Local Docker Environment (docker-compose)    │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │  PostgreSQL │  │  MinIO      │  │ Flask  │ │
│  │  + PostGIS  │  │  (S3 sim)   │  │  (Web) │ │
│  └─────────────┘  └─────────────┘  └────────┘ │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Pipeline ETL (Container)                │  │
│  │  ├─ Bronze Loader                        │  │
│  │  ├─ Silver Processor                     │  │
│  │  ├─ Gold Processor (Spatial Join)        │  │
│  │  └─ PostGIS Loader                       │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
     Volumes: bronze/, silver/, gold/, postgres/
```

## 📦 Serviços

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| PostgreSQL | 5432 | Database com PostGIS |
| MinIO | 9000 | API S3 compatível |
| MinIO Console | 9001 | UI para MinIO |
| Flask Web | 5000 | Dashboard com visualização |
| Pipeline | - | ETL (container sempre rodando) |

## 🚀 Quick Start

### 1. Iniciar o ambiente completo

```bash
docker-compose up -d
```

Aguarde ~30 segundos para todos os serviços ficarem saudáveis.

### 2. Verificar status

```bash
docker-compose ps
```

Você deve ver:
```
NAME              STATUS
esteira-postgis   healthy
esteira-minio     healthy
esteira-web       running
esteira-pipeline  running
```

### 3. Acessar serviços

- **Flask Dashboard**: http://localhost:5000
- **MinIO Console**: http://localhost:9001 (user: minioadmin / pass: minioadmin123)
- **PostgreSQL**: localhost:5432 (user: esteira_user / pass: esteira_local_2025)

## 🔄 Executar o Pipeline

### Opção 1: Executar dentro do container

```bash
# Acessar shell do pipeline
docker-compose exec pipeline bash

# Dentro do container:
cd /app
python pipeline/main.py
```

### Opção 2: Executar via docker-compose

```bash
docker-compose exec pipeline python pipeline/main.py
```

### Opção 3: Executar um estágio específico

```bash
# Apenas Bronze
docker-compose exec pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"

# Apenas Silver
docker-compose exec pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"

# Apenas Gold (Spatial Join)
docker-compose exec pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"

# Apenas PostGIS
docker-compose exec pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

## 📊 Verificar dados no MinIO

### Via Console (UI)

1. Abra http://localhost:9001
2. Login: minioadmin / minioadmin123
3. Navegue para os buckets:
   - `/bronze` - dados brutos (flooding_areas, citizens)
   - `/silver` - dados normalizados
   - `/gold` - dados processados (affected/unaffected)

### Via CLI

```bash
# Listar buckets
docker-compose exec minio mc ls myminio/

# Listar files no bronze bucket
docker-compose exec minio mc ls myminio/bronze/

# Download file
docker-compose exec minio mc cp myminio/bronze/flooding_areas_porto_alegre.parquet .
```

## 🗄️ Verificar dados no PostgreSQL

```bash
# Acessar psql
docker-compose exec postgis psql -U esteira_user -d esteira_geo

# Dentro do psql:
\dt                          # List tables
SELECT COUNT(*) FROM citizens;  # Count citizens
SELECT COUNT(*) FROM flooding_areas;  # Count flooding areas

# Query com spatial join
SELECT c.citizen_id, c.name, fa.area_name, c.geometry 
FROM citizens c 
LEFT JOIN flooding_areas fa ON ST_Contains(fa.geometry, c.geometry)
LIMIT 10;

# Statistics view
SELECT * FROM v_citizens_summary;

# Sair
\q
```

## 📝 Arquivos de Dados Locais

Os dados processados são salvos em volumes Docker:

```
projeto/
├─ .docker/     (volumes de dados)
│  ├─ bronze/   (dados brutos GeoParquet)
│  ├─ silver/   (dados normalizados)
│  └─ gold/     (dados processados)
├─ logs/
│  ├─ pipeline/
│  └─ flask/
```

Para acessar:

```bash
# Copiar arquivo do container para host
docker cp esteira-pipeline:/data/bronze/flooding_areas_porto_alegre.parquet ./

# Visualizar em Python
import geopandas as gpd
gdf = gpd.read_parquet('flooding_areas_porto_alegre.parquet')
print(gdf)
```

## 🧪 Testes Automatizados

Execute testes em diferentes camadas:

```bash
# Setup venv no pipeline container
docker-compose exec pipeline bash -c "python -m venv /app/venv && . /app/venv/bin/activate && pip install -r /app/pipeline/requirements.txt"

# Bronze layer test
docker-compose exec pipeline bash -c "cd /app && python -c 'from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()'"

# Validar dados Bronze -> Silver -> Gold
docker-compose exec pipeline bash -c "cd /app && python pipeline/main.py"
```

Ou use o arquivo de testes:

```bash
# Copiar arquivo de testes para working dir
docker cp pipeline/testes_e_validacoes.txt esteira-pipeline:/app/

# Executar linha por linha
docker-compose exec pipeline bash
```

## 🔧 Troubleshooting

### PostgreSQL não conecta

```bash
# Check health
docker-compose exec postgis pg_isready -U esteira_user

# Check logs
docker-compose logs postgis
```

### MinIO requer inicialização

```bash
# Forçar recriação do container minio
docker-compose up -d --force-recreate minio
```

### Pipeline container não executa

```bash
# Check logs
docker-compose logs pipeline

# Acessar e debugar
docker-compose exec pipeline bash
cd /app
python pipeline/main.py  # Executar manualmente
```

### Limpar tudo e recomeçar

```bash
# Parar todos containers
docker-compose down

# Remover volumes (cuidado: deleta dados!)
docker-compose down -v

# Reconstruir imagens
docker-compose build --no-cache

# Reiniciar
docker-compose up -d
```

## 📦 Dependências Docker

### Pipeline Container
- Python 3.9
- GeoPandas, Rasterio, Fiona, Shapely
- Psycopg2 (PostgreSQL client)
- Boto3 (S3 client)
- GDAL, GEOS, PROJ (libs geoespaciais)

### Web Container
- Python 3.9
- Flask
- Gunicorn
- Psycopg2
- GeoPandas (readonly queries)

## 🌍 Próximos passos

1. **Dev Local**: Use este setup Docker para desenvolvimento
2. **Testes**: Execute testes com dados reais ou mocked
3. **Deploy Cloud**: Use Terraform quando pronto (`terraform apply -var-file=envs/huawei-sp.tfvars`)
4. **Produção**: Adapte python-env.yml do Ansible para os containers

## 📚 Arquivos Relacionados

- `docker-compose.yml` - Orquestração de containers
- `pipeline/Dockerfile` - Imagem do pipeline ETL
- `pipeline/Dockerfile.web` - Imagem da Flask app
- `.env.docker` - Variáveis de ambiente padrão
- `pipeline/config.py` - Detecta modo storage (local/minio/s3)
- `testes_e_validacoes.txt` - Guia de testes completo
