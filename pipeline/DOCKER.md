# Docker Development Environment

Ambiente completo dockerizado para desenvolvimento e teste local da esteira de processamento geoespacial com **Apache Airflow** como orquestrador.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────┐
│              Local Docker Environment (docker compose)       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │  PostgreSQL │  │    MinIO    │  │   Flask (Web)        │ │
│  │  + PostGIS  │  │  (S3 sim)   │  │   port 5000          │ │
│  │  + Airflow  │  │  port 9000  │  │   Leaflet + SVG      │ │
│  │  metadata   │  │  port 9001  │  │   markers            │ │
│  └─────────────┘  └─────────────┘  └──────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Apache Airflow                                      │    │
│  │  ├─ airflow-init    (migra DB + cria admin)          │    │
│  │  ├─ airflow-scheduler  (LocalExecutor, port 8080)    │    │
│  │  │   volumes: ./airflow/dags + ./pipeline/etl        │    │
│  │  │   DAGs:                                           │    │
│  │  │   ├─ esteira_geo_watcher  (30s, detecta bronze)   │    │
│  │  │   ├─ esteira_geo          (trigger, processa)     │    │
│  │  │   └─ esteira_geo_manutencao (diário, 30 dias)     │    │
│  │  └─ airflow-webserver  (UI, port 8080)               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Pipeline ETL Container (idle)                       │    │
│  │  ├─ bronze_loader.py   (upload de dados de teste)    │    │
│  │  ├─ silver_processor.py (_safe_concat, acumulativo)  │    │
│  │  ├─ gold_processor.py  (spatial join + areas_only)   │    │
│  │  └─ postgis_loader.py  (TRUNCATE + INSERT do gold)   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  JupyterLab (port 8888)                              │    │
│  │  ├─ esteira_geo.ipynb   (fluxo interativo)           │    │
│  │  └─ utilitarios.ipynb   (manutenção do ambiente)     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
  Volumes bind: ./airflow/dags, ./pipeline/etl, ./pipeline/config.py
  Volumes bind: ./pipeline/web/app.py, ./pipeline/web/templates
  Volumes nomeados: postgres_data, minio_data, pipeline_silver, pipeline_gold
```

## Serviços

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `postgis` | 5432 | PostgreSQL + PostGIS + Airflow metadata |
| `minio` | 9000/9001 | S3 simulado + Console UI |
| `airflow-webserver` | 8080 | Airflow UI (admin/admin) |
| `airflow-scheduler` | — | Executa DAGs (LocalExecutor) |
| `pipeline` | — | ETL standby (testes manuais) |
| `web` | 5000 | Flask dashboard + Leaflet map |
| `jupyter` | 8888 | JupyterLab (token: esteira) |

> O `pipeline-watcher` original está disponível via `docker compose --profile watcher up` mas é substituído pelo `esteira_geo_watcher` do Airflow.

## Quick Start

### 1. Iniciar o ambiente

```bash
docker compose up -d
```

Aguarde ~60 segundos para o Airflow init completar.

### 2. Verificar status

```bash
docker compose ps
```

### 3. Acessar serviços

- **Airflow UI**: http://localhost:8080 (admin/admin)
- **Flask Dashboard**: http://localhost:5000
- **JupyterLab**: http://localhost:8888/lab?token=esteira
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)

## Executar o Pipeline

### Via Airflow (recomendado)

```bash
# Upload de dados sintéticos — watcher detecta em até 30s
docker compose exec pipeline python /app/etl/bronze_loader.py

# Trigger manual com use_case específico
docker compose exec airflow-scheduler \
  airflow dags trigger esteira_geo --conf '{"use_case": "enchentes_poa"}'

# Acompanhar na UI: http://localhost:8080
```

### Via CLI (sem Airflow)

```bash
docker compose exec -e USE_CASE=enchentes_poa pipeline python /app/main.py
```

### Etapa individual

```bash
# Silver
docker compose exec pipeline python -c \
  "from etl.silver_processor import process_silver; process_silver()"

# Gold completo (áreas + cidadãos)
docker compose exec pipeline python -c \
  "from etl.gold_processor import process_gold; process_gold()"

# Gold só áreas
docker compose exec pipeline python -c \
  "from etl.gold_processor import process_gold_areas_only; process_gold_areas_only()"

# PostGIS
docker compose exec pipeline python -c \
  "from etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

## Volumes e Dados

| Path no host | Path no container | Tipo | Descrição |
|---|---|---|---|
| `./airflow/dags/` | `/opt/airflow/dags` | bind | DAGs editáveis ao vivo |
| `./pipeline/etl/` | `/opt/airflow/pipeline/etl` | bind | Código ETL editável ao vivo |
| `./pipeline/config.py` | `/opt/airflow/pipeline/config.py` | bind | Config editável ao vivo |
| `./pipeline/web/app.py` | `/app/app.py` | bind | Flask editável ao vivo |
| `./pipeline/web/templates/` | `/app/templates` | bind | Templates editáveis ao vivo |
| `./data/bronze/` | `/data/bronze` | bind | Dados de teste locais |
| `postgres_data` | `/var/lib/postgresql/data` | volume | Banco + Airflow metadata |
| `minio_data` | `/data` | volume | Buckets MinIO |
| `pipeline_silver` | `/data/silver` | volume | Silver layer |
| `pipeline_gold` | `/data/gold` | volume | Gold layer |

> Alterações em DAGs, código ETL, Flask e templates são refletidas **imediatamente** sem rebuild.

## Verificar dados no PostgreSQL

```bash
docker compose exec postgis psql -U esteira_user -d esteira_geo

\dt                                                    -- listar tabelas
SELECT tablename FROM pg_tables WHERE tablename LIKE '%_citizens';
SELECT COUNT(*) FROM enchentes_poa_citizens;
SELECT COUNT(*) FROM enchentes_poa_citizens WHERE affected_by_flooding = TRUE;
\q
```

## Verificar dados no MinIO

Acesse http://localhost:9001 — estrutura dos buckets:

```
bronze/
└── automatizado/
    ├── enchentes_poa/
    │   ├── arquivo.csv          ← pendente (watcher vai processar)
    │   └── processados/         ← já processado com sucesso
    └── enchentes_mg/

silver/
└── enchentes_poa/
    ├── silver_citizens_data.parquet
    └── silver_flooding_areas.parquet

gold/
└── enchentes_poa/
    ├── flooding_areas.parquet
    ├── affected_citizens.parquet
    ├── unaffected_citizens.parquet
    └── all_citizens_evaluated.parquet
```

## Notebooks Jupyter

### esteira_geo.ipynb — Fluxo interativo

Replica o pipeline completo em modo exploratório (não move arquivos para `processados/`):

```python
# Célula 0: configurar use_case
os.environ['USE_CASE'] = 'enchentes_poa'  # ou enchentes_mg, enchentes_rj

# Célula 2: silver exploratório
silver = process_silver(bronze_prefix='exploratorio/enchentes_poa/', move_files=False)

# Célula 3: gold
affected, unaffected, all_citizens = process_gold()
```

### utilitarios.ipynb — Manutenção

```python
# Dry-run (preview sem executar)
limpar_banco()
limpar_silver_gold()
mover_processados()
apagar_use_case('enchentes_poa')

# Executar
limpar_banco(confirmar=True)
limpar_silver_gold(use_case='enchentes_poa', confirmar=True)
mover_processados(use_case='enchentes_poa', confirmar=True)
apagar_use_case('enchentes_poa', confirmar=True)
```

## Troubleshooting

### Airflow não inicia

```bash
docker compose logs airflow-init
docker compose logs airflow-scheduler
```

### DAG não detecta arquivos no bronze

- Arquivo deve estar em `automatizado/<use_case>/` (não em `processados/`)
- Aguarde até 30s (intervalo do watcher)
- Verifique se `esteira_geo_watcher` está ativa: http://localhost:8080

### Arquivo foi para `processados/` mas não apareceu no frontend

```python
# No notebook utilitarios.ipynb:
mover_processados(use_case='enchentes_poa', confirmar=True)
```

### Rebuild após mudanças no Dockerfile

```bash
docker compose build airflow-scheduler airflow-webserver pipeline web
docker compose up -d
```

### Limpar tudo e recomeçar

```bash
docker compose down -v        # remove volumes (apaga dados!)
docker compose build --no-cache
docker compose up -d
```

### Ver logs

```bash
docker compose logs -f airflow-scheduler   # logs das DAGs
docker compose logs -f pipeline            # logs do ETL
docker compose logs -f web                 # logs do Flask
```
