# 🐳 Docker Setup - Quick Start

Ambiente completo dockerizado para **desenvolvimento e teste local** da esteira geoespacial com **Apache Airflow**.

## ⚡ Início Rápido

### 1️⃣ Iniciar o Ambiente

```bash
cd esteira-geo
docker compose up -d

# Aguarde ~60 segundos (Airflow init + health checks)
docker compose ps
```

**Status esperado:**
```
NAME                        STATUS
esteira-postgis             Up (healthy)
esteira-minio               Up (healthy)
esteira-airflow-webserver   Up (healthy)
esteira-airflow-scheduler   Up
esteira-pipeline            Up
esteira-web                 Up
esteira-jupyter             Up
```

### 2️⃣ Acessar Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Airflow UI** | http://localhost:8080 | admin / admin |
| **Flask Dashboard** | http://localhost:5000 | — |
| **JupyterLab** | http://localhost:8888/lab?token=esteira | — |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin123 |
| **PostgreSQL** | localhost:5432 | esteira_user / esteira_local_2025 |

### 3️⃣ Ingerir Dados e Executar Pipeline

```bash
# Opção A: Upload via bronze_loader (dados sintéticos)
docker compose exec pipeline python /app/etl/bronze_loader.py
# → O watcher detecta em até 30s e dispara automaticamente

# Opção B: Trigger manual via Airflow CLI
docker compose exec airflow-scheduler \
  airflow dags trigger esteira_geo --conf '{"use_case": "enchentes_poa"}'

# Opção C: Pipeline direto sem Airflow
docker compose exec -e USE_CASE=enchentes_poa pipeline python /app/main.py
```

---

## 🔄 Fluxo do Pipeline

```
bronze/automatizado/<use_case>/
         ↓ (detectado pelo esteira_geo_watcher a cada 30s)
DAG: esteira_geo
  ├── Task: silver       → normaliza CSV/GeoJSON, acumula por citizen_id/area_id
  ├── Task: branch_gold  → decide próximo passo baseado no silver acumulado
  ├── Task: gold         → spatial join (áreas + cidadãos)  ─┐
  ├── Task: postgis      → TRUNCATE + INSERT no PostGIS      ─┘ caminho completo
  ├── Task: postgis_areas_only → só áreas (sem cidadãos)    ─── só áreas
  └── Task: skip_gold    → encerra (bronze vazio)            ─── sem dados
         ↓
Flask Dashboard (http://localhost:5000)
```

### Cenários suportados

| Bronze contém | Branch | PostGIS atualizado com |
|---|---|---|
| Áreas + cidadãos | `gold` → `postgis` | Polígonos + cidadãos classificados |
| Só áreas | `postgis_areas_only` | Polígonos visíveis no mapa |
| Só cidadãos | `skip_gold` | Nada (aguarda áreas) |
| Vazio | encerra | Nada |

---

## 🗂️ DAGs Airflow

| DAG | Schedule | Função |
|-----|----------|--------|
| `esteira_geo_watcher` | 30s | Monitora `bronze/automatizado/`, dispara `esteira_geo` por use_case detectado |
| `esteira_geo` | trigger | Executa silver → branch → gold/postgis |
| `esteira_geo_manutencao` | diário | Limpa histórico do banco (mantém 30 dias) |

---

## 🛠️ Scripts de Gerenciamento

### Linux/macOS

```bash
chmod +x setup.sh docker.sh debug.sh
./setup.sh        # Setup inicial (primeira vez)
./docker.sh up    # Iniciar ambiente
./docker.sh down  # Parar ambiente
./docker.sh logs pipeline
./docker.sh db    # Acessar PostgreSQL
```

### Windows PowerShell

```powershell
.\docker.ps1 status
.\docker.ps1 pipeline
.\docker.ps1 logs pipeline
.\docker.ps1 db
.\docker.ps1 down
```

### Makefile

```bash
make up       # Iniciar
make pipeline # Executar pipeline
make down     # Parar
make db       # Banco de dados
```

---

## 📊 Verificar Dados

### Airflow UI

Acesse http://localhost:8080 (admin/admin) para:
- Ver histórico de runs e status de cada task
- Disparar DAGs manualmente com `use_case` específico
- Ver logs detalhados por task

### PostgreSQL

```bash
docker compose exec postgis psql -U esteira_user -d esteira_geo

-- Use_cases disponíveis
SELECT tablename FROM pg_tables WHERE tablename LIKE '%_citizens';

-- Estatísticas
SELECT COUNT(*) as total,
       SUM(CASE WHEN affected_by_flooding THEN 1 ELSE 0 END) as afetados
FROM enchentes_poa_citizens;
\q
```

### MinIO (S3 simulado)

Acesse http://localhost:9001 — buckets disponíveis:
- `bronze/automatizado/<use_case>/` — arquivos pendentes
- `bronze/automatizado/<use_case>/processados/` — processados com sucesso
- `silver/<use_case>/` — parquet normalizado
- `gold/<use_case>/` — parquet do spatial join

### Flask APIs

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/use_cases
curl "http://localhost:5000/api/stats?use_case=enchentes_poa"
```

---

## 🧪 Executar Etapas Individuais

```bash
# Silver
docker compose exec pipeline python -c \
  "from etl.silver_processor import process_silver; print(process_silver())"

# Gold (completo)
docker compose exec pipeline python -c \
  "from etl.gold_processor import process_gold; process_gold()"

# Gold (só áreas)
docker compose exec pipeline python -c \
  "from etl.gold_processor import process_gold_areas_only; process_gold_areas_only()"

# PostGIS
docker compose exec pipeline python -c \
  "from etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

---

## 🔧 Troubleshooting

### Airflow não sobe

```bash
docker compose logs airflow-init
docker compose logs airflow-scheduler
```

### DAG não detecta arquivos

- Verifique se o arquivo está em `automatizado/<use_case>/` (não em `processados/`)
- Aguarde até 30s (intervalo do watcher)
- Confirme que `esteira_geo_watcher` está ativa na UI

### Arquivo foi para `processados/` mas não apareceu no frontend

Use o notebook `utilitarios.ipynb` → `mover_processados()` para reprocessar.

### Rebuild após mudanças no código

```bash
# Pipeline e web usam volumes bind — mudanças são imediatas
# Airflow usa volumes bind para dags/ e pipeline/ — mudanças são imediatas
# Para mudanças no Dockerfile:
docker compose build airflow-scheduler airflow-webserver
docker compose up -d airflow-scheduler airflow-webserver
```

### Limpar tudo e recomeçar

```bash
docker compose down -v   # remove volumes (apaga dados!)
docker compose build --no-cache
docker compose up -d
```

### Ver logs

```bash
docker compose logs -f airflow-scheduler
docker compose logs -f pipeline
docker compose logs -f web
```

---

## 📦 Imagens Docker

| Serviço | Base | Extras |
|---------|------|--------|
| `airflow-scheduler/webserver` | `apache/airflow:2.9.1-python3.12` | GDAL, geopandas, boto3, psycopg2 |
| `pipeline` | `python:3.12-slim` | GDAL, geopandas, rasterio, boto3 |
| `web` | `python:3.12-slim` | Flask, psycopg2, GDAL |
| `jupyter` | `python:3.9-slim` | JupyterLab, geopandas, boto3 |
| `postgis` | `postgis/postgis:13-3.2` | PostGIS extension |
| `minio` | `minio/minio:latest` | S3-compatible storage |
