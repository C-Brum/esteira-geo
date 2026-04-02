# Diagramas de Arquitetura - Esteira Geo

Visualizações em Mermaid da arquitetura do projeto em diferentes contextos.

---

## 🏗️ Diagrama 1: Arquitetura Terraform/Ansible

**Uso**: Deploy em **nuvem pública** (AWS ou Huawei Cloud)

### Componentes

```
Developer/Admin
    ↓
    ├─ Terraform (IaC)
    └─ Ansible (Configuration Management)
        ↓
        ├─ AWS Cloud
        │  ├─ S3 Buckets (Bronze/Silver/Gold)
        │  ├─ EC2 Processing VM (Airflow Scheduler + Pipeline ETL + DAGs)
        │  ├─ EC2 Presentation VM (Flask + Nginx + Leaflet)
        │  └─ RDS PostgreSQL + PostGIS (pipeline + Airflow metadata)
        │
        └─ Huawei Cloud (São Paulo)
           ├─ OBS Buckets (Bronze/Silver/Gold)
           ├─ ECS Processing VM (Airflow Scheduler + Pipeline ETL + DAGs)
           ├─ ECS Presentation VM (Flask + Nginx + Leaflet)
           └─ RDS PostgreSQL + PostGIS (pipeline + Airflow metadata)
```

### Fluxo de Deployment

1. **Terraform**: Provisiona infraestrutura (VPCs, buckets, VMs, RDS)
2. **Ansible**: Configura VMs (Airflow, Python geoespacial, Flask, Nginx)
3. **Airflow DAGs**: Orquestram o pipeline automaticamente
   - `esteira_geo_watcher`: detecta arquivos no bronze a cada 30s
   - `esteira_geo`: silver → branch → gold → postgis
   - `esteira_geo_manutencao`: limpeza diária do histórico (30 dias)

---

## 🐳 Diagrama 2: Arquitetura Docker Local

**Uso**: **Desenvolvimento e testes locais** (sem credenciais de nuvem)

### Componentes

```
Host Machine
    ↓
    Docker Compose
        ↓
        Docker Network (esteira-network)
            ├─ PostgreSQL 13 + PostGIS
            │  ├─ Pipeline data (use_case_citizens, use_case_flooding_areas)
            │  └─ Airflow metadata (dag_run, task_instance, xcom...)
            │
            ├─ MinIO (S3 simulado)
            │  ├─ bronze/automatizado/<use_case>/
            │  ├─ silver/<use_case>/
            │  └─ gold/<use_case>/
            │
            ├─ Apache Airflow
            │  ├─ airflow-init  (migra DB + cria admin, roda uma vez)
            │  ├─ airflow-scheduler  (LocalExecutor)
            │  │   ├─ volumes bind: ./airflow/dags + ./pipeline/etl + config.py
            │  │   ├─ DAG: esteira_geo_watcher  (30s)
            │  │   ├─ DAG: esteira_geo          (trigger)
            │  │   └─ DAG: esteira_geo_manutencao (diário, 30 dias)
            │  └─ airflow-webserver  (port 8080, admin/admin)
            │
            ├─ Pipeline ETL Container (idle, testes manuais)
            ├─ Flask Web (port 5000, Leaflet + SVG markers)
            └─ JupyterLab (port 8888, token: esteira)
                ├─ esteira_geo.ipynb   (fluxo interativo)
                └─ utilitarios.ipynb  (manutenção)
```

### Volumes bind (editáveis ao vivo, sem rebuild)

```
./airflow/dags/       → /opt/airflow/dags          (DAGs)
./pipeline/etl/       → /opt/airflow/pipeline/etl  (código ETL no scheduler)
./pipeline/config.py  → /opt/airflow/pipeline/config.py
./pipeline/web/app.py → /app/app.py                (Flask)
./pipeline/web/templates/ → /app/templates
./pipeline/           → /app/pipeline_src           (Jupyter)
```

### Fluxo de Execução

```
docker compose up -d
    ↓
Airflow init → scheduler → watcher ativo
    ↓
Upload arquivo em bronze/automatizado/<use_case>/
    ↓ (detectado em até 30s)
DAG esteira_geo disparada com conf={use_case}
    ↓
Task: silver → normaliza + acumula (_safe_concat)
    ↓
Task: branch_gold → verifica silver acumulado total
    ↓
    ├─ áreas + cidadãos → gold → postgis (completo)
    ├─ só áreas         → gold_areas_only → postgis_areas_only
    └─ bronze vazio     → skip_gold (encerra sem retry)
    ↓
Flask Dashboard → http://localhost:5000
```

---

## 📊 Diagrama 3: Fluxo Medallion (Bronze → Silver → Gold)

**Uso**: Entender o **fluxo de dados** e transformações

### Camadas

```
INPUT
  ├─ CSV com latitude/longitude
  └─ GeoJSON (pontos ou polígonos)
       ↓

AIRFLOW — esteira_geo_watcher (30s) → esteira_geo
  ├─ Detecta use_cases com arquivos em automatizado/
  ├─ Não dispara se já há run ativo para o use_case
  └─ Dispara esteira_geo com conf={use_case}
       ↓

SILVER LAYER (Normalizado + Acumulativo)
  ├─ _safe_concat: geometria WKT + datetime str antes do concat
  ├─ Tolerante a schemas diferentes entre arquivos
  ├─ Acumula por citizen_id / area_id (keep last)
  ├─ Move para processados/ SOMENTE após salvar no S3
  └─ Storage: S3 — prefix: <use_case>/
       ↓

GOLD LAYER (Processado — fonte exclusiva do PostGIS)
  ├─ Cenário completo: spatial join (sjoin within)
  │   ├─ affected_citizens.parquet
  │   ├─ unaffected_citizens.parquet
  │   └─ all_citizens_evaluated.parquet
  ├─ Cenário só áreas: process_gold_areas_only()
  │   └─ flooding_areas.parquet (gerado mesmo sem cidadãos)
  └─ Storage: S3 — prefix: <use_case>/
       ↓

PostGIS (Espelho do Gold)
  ├─ <use_case>_flooding_areas  GEOMETRY(POLYGON, 4326)  GIST index
  ├─ <use_case>_citizens        GEOMETRY(POINT, 4326)    GIST index
  └─ TRUNCATE + INSERT a cada execução
       ↓

FLASK DASHBOARD
  ├─ /api/stats?use_case=    (fallback automático para use_case disponível)
  ├─ /api/geojson?use_case=
  ├─ /api/use_cases
  └─ /map  (Leaflet + SVG markers coloridos + fitBounds em áreas)
```

---

## 🔄 Comparação: Terraform vs Docker

| Aspecto | Terraform/Ansible | Docker |
|---------|---|---|
| **Environment** | Nuvem (AWS/Huawei) | Local |
| **Orquestração** | Airflow em VM dedicada | Airflow em container |
| **Storage** | S3/OBS real | MinIO simulado |
| **Database** | RDS real | PostgreSQL container |
| **Airflow UI** | `http://<processing_ip>:8080` | `http://localhost:8080` |
| **Ideal Para** | Produção | Desenvolvimento/Testes |

---

## 📚 Arquivos Relacionados

### Diagrama 1 (Terraform/Ansible)
- [terraform/](../terraform/)
- [ansible/](../ansible/)

### Diagrama 2 (Docker)
- [docker-compose.yml](../docker-compose.yml)
- [airflow/Dockerfile](../airflow/Dockerfile)
- [airflow/dags/](../airflow/dags/)

### Diagrama 3 (Medallion)
- [pipeline/etl/silver_processor.py](../pipeline/etl/silver_processor.py)
- [pipeline/etl/gold_processor.py](../pipeline/etl/gold_processor.py)
- [pipeline/etl/postgis_loader.py](../pipeline/etl/postgis_loader.py)
- [airflow/dags/esteira_geo_dag.py](../airflow/dags/esteira_geo_dag.py)

---

## 🎯 Fluxo de Trabalho Recomendado

```
1. docker compose up -d
   └─ Acesse Airflow UI: http://localhost:8080 (admin/admin)

2. Depositar arquivo em bronze/automatizado/<use_case>/
   └─ Watcher detecta em até 30s e dispara automaticamente

3. Acompanhar na UI
   └─ Logs por task, histórico, retries automáticos

4. Ver resultado no Flask
   └─ http://localhost:5000

5. (Se deploy) Usar Terraform + Ansible
   └─ Mesma lógica, buckets S3/OBS reais
```
