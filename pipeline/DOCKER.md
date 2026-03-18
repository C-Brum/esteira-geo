# Docker Development Environment

Ambiente completo dockerizado para desenvolvimento e teste local da esteira de processamento geoespacial.

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│       Local Docker Environment (docker compose)     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │  PostgreSQL │  │    MinIO    │  │   Flask    │  │
│  │  + PostGIS  │  │  (S3 sim)   │  │   (Web)    │  │
│  └─────────────┘  └─────────────┘  └────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Pipeline ETL (Container)                    │   │
│  │  ├─ Bronze Loader                            │   │
│  │  ├─ CSV/GeoJSON Converter (Silver)           │   │
│  │  ├─ Silver Processor (+ consolidação)        │   │
│  │  ├─ Gold Processor (Spatial Join + dedup)    │   │
│  │  └─ PostGIS Loader                           │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Pipeline Watcher                            │   │
│  │  └─ Polling /data/bronze/enchentes_poa (5s)  │   │
│  │     Dispara main.py ao detectar mudanças     │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
  Volumes: ./data/bronze (bind), silver/, gold/, postgres/
```

## Serviços

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `postgis` | 5432 | PostgreSQL + PostGIS |
| `minio` | 9000 | API S3 compatível |
| `minio` console | 9001 | UI MinIO |
| `web` | 5000 | Flask dashboard |
| `pipeline` | — | ETL (standby para execução manual) |
| `pipeline-watcher` | — | Monitora `data/bronze/enchentes_poa/` e dispara pipeline |

## Quick Start

### 1. Iniciar o ambiente completo

```bash
docker compose up -d
```

Aguarde ~30 segundos para todos os serviços ficarem saudáveis.

### 2. Verificar status

```bash
docker compose ps
```

Saída esperada:
```
NAME                       STATUS
esteira-postgis            healthy
esteira-minio              healthy
esteira-web                running
esteira-pipeline           running
esteira-pipeline-watcher   running
```

### 3. Acessar serviços

- **Flask Dashboard**: http://localhost:5000
- **MinIO Console**: http://localhost:9001 (user: `minioadmin` / pass: `minioadmin123`)
- **PostgreSQL**: localhost:5432 (user: `esteira_user` / pass: `esteira_local_2025` / db: `esteira_geo`)

## Executar o Pipeline

### Manualmente

```bash
docker compose exec pipeline python /app/main.py
```

### Automaticamente (Watcher)

Qualquer arquivo CSV ou GeoJSON copiado para `data/bronze/enchentes_poa/` dispara o pipeline em até 5 segundos:

```bash
cp meus_cidadaos.csv data/bronze/enchentes_poa/
# pipeline-watcher detecta e executa main.py automaticamente
```

Se o arquivo já existia antes do container subir, use `touch` para forçar detecção:

```bash
touch data/bronze/enchentes_poa/meu_arquivo.csv
```

### Etapa individual

```bash
# Bronze
docker compose exec pipeline python -c "from etl.bronze_loader import load_sample_data; load_sample_data()"

# Silver (conversão CSV/GeoJSON)
docker compose exec pipeline python -c "from etl.silver.csv_geojson_converter import run_conversion; run_conversion()"

# Silver (normalização)
docker compose exec pipeline python -c "from etl.silver_processor import process_silver; process_silver()"

# Gold
docker compose exec pipeline python -c "from etl.gold_processor import process_gold; process_gold()"

# PostGIS
docker compose exec pipeline python -c "from etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

## Volumes e Dados

| Path no host | Path no container | Tipo | Descrição |
|---|---|---|---|
| `./data/bronze/` | `/data/bronze` | bind mount | Arquivos externos CSV/GeoJSON + dados gerados |
| — | `/data/silver` | volume nomeado | Dados normalizados (subdir por caso de uso) |
| — | `/data/gold` | volume nomeado | Dados processados (subdir por caso de uso) |
| `postgres_data` | `/var/lib/postgresql/data` | volume nomeado | Banco de dados |

> `data/bronze/` é um **bind mount** — arquivos colocados no host ficam imediatamente visíveis no container e no watcher.

### Estrutura de subdiretórios por caso de uso

```
/data/bronze/enchentes_poa/    ← bind mount (./data/bronze/enchentes_poa/)
/data/silver/enchentes_poa/    ← volume nomeado
/data/gold/enchentes_poa/      ← volume nomeado
```

Tabelas PostGIS correspondentes: `enchentes_poa_citizens`, `enchentes_poa_flooding_areas`.

### Inspecionar dados nos volumes

```bash
# Listar arquivos bronze
docker compose exec pipeline find /data/bronze/enchentes_poa -type f

# Listar arquivos silver
docker compose exec pipeline find /data/silver/enchentes_poa -type f

# Inspecionar parquet gold
docker compose exec pipeline python -c "
import geopandas as gpd
gdf = gpd.read_parquet('/data/gold/enchentes_poa/all_citizens_evaluated.parquet')
print(f'Total: {len(gdf)}')
print(gdf[['citizen_id','name','affected_by_flooding']].head())
"
```

## Verificar dados no PostgreSQL

```bash
docker compose exec postgis psql -U esteira_user -d esteira_geo

# Dentro do psql:
\dt                                                        -- listar tabelas
SELECT COUNT(*) FROM enchentes_poa_citizens;               -- total cidadãos
SELECT COUNT(*) FROM enchentes_poa_flooding_areas;         -- áreas de enchente
SELECT citizen_id, name, affected_by_flooding FROM enchentes_poa_citizens LIMIT 5;
\q
```

## Verificar dados no MinIO

1. Abra http://localhost:9001
2. Login: `minioadmin` / `minioadmin123`
3. Buckets disponíveis:
   - `bronze/` — dados brutos
   - `silver/` — dados normalizados
   - `gold/` — dados processados (affected/unaffected/all)

## Troubleshooting

### Rebuild após mudanças no código

```bash
docker compose build pipeline pipeline-watcher
docker compose up -d pipeline pipeline-watcher
```

### Limpar tudo e recomeçar

```bash
docker compose down -v        # para containers e remove volumes (apaga dados!)
docker compose build --no-cache
docker compose up -d
```

### Ver logs

```bash
docker compose logs -f pipeline          # logs do ETL
docker compose logs -f pipeline-watcher  # logs do watcher
docker compose logs -f web               # logs do Flask
docker compose logs -f postgis           # logs do PostgreSQL
```

### PostGIS não atualiza após pipeline rodar

Verifique se `pipeline-watcher` tem as variáveis de banco no `docker-compose.yml`:

```yaml
pipeline-watcher:
  environment:
    RDS_HOST: postgis
    RDS_PORT: 5432
    RDS_DB: esteira_geo
    RDS_USER: esteira_user
    RDS_PASSWORD: esteira_local_2025
```

Sem `RDS_HOST`, o loader tenta conectar em `localhost` e falha silenciosamente.

### Pipeline falha silenciosamente

```bash
docker compose exec pipeline python /app/main.py 2>&1
```

### PostgreSQL não conecta

```bash
docker compose exec postgis pg_isready -U esteira_user
docker compose logs postgis
```

## Dependências

### Pipeline Container (`Dockerfile`)
- Python 3.9, GeoPandas, Shapely, Fiona, Rasterio
- Psycopg2, Boto3, PyArrow, python-dotenv
- GDAL, GEOS, PROJ

### Web Container (`Dockerfile.web`)
- Python 3.9, Flask, Gunicorn, Psycopg2, Folium
- GDAL, GEOS, PROJ
