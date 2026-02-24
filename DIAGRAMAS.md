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
        │  ├─ VPC + Security Groups
        │  ├─ S3 Buckets (Bronze/Silver/Gold)
        │  ├─ EC2 Processing VM (Python pipeline)
        │  ├─ EC2 Presentation VM (Flask)
        │  └─ RDS PostgreSQL + PostGIS
        │
        └─ Huawei Cloud (São Paulo)
           ├─ VPC + Security Groups
           ├─ OBS Buckets (Bronze/Silver/Gold)
           ├─ ECS Processing VM (Python pipeline)
           ├─ ECS Presentation VM (Flask)
           └─ RDS PostgreSQL + PostGIS
```

### Fluxo de Deployment

1. **Terraform**: Provisiona toda infraestrutura em nuvem
   - Cria VPCs e networking
   - Provisiona buckets (S3/OBS)
   - Cria VMs (EC2/ECS)
   - Cria banco de dados (RDS)

2. **Ansible**: Configura VMs após provisionamento
   - Instala geospatial libraries (GDAL, GeoPandas, etc)
   - Cria Python virtual environments
   - Deploy pipeline ETL
   - Deploy Flask web application
   - Configura Nginx + Gunicorn
   - Setup cron jobs para execução automática

3. **Medallion Pipeline**: Processa dados em camadas
   - Bronze: dados brutos em S3/OBS
   - Silver: dados normalizados e validados
   - Gold: dados processados (spatial join)
   - PostGIS: persistência com índices espaciais

### Quando Usar

✅ Deploy em produção  
✅ Infraestrutura em nuvem pública  
✅ Multi-cloud (AWS + Huawei)  
✅ Escalabilidade automática  
✅ Infraestrutura as Code  

---

## 🐳 Diagrama 2: Arquitetura Docker Local

**Uso**: **Desenvolvimento e testes locais** (sem credenciais de nuvem)

### Componentes

```
Host Machine (Windows/Linux/macOS)
    ↓
    ├─ Scripts (docker.sh, debug.sh, setup.sh)
    ├─ Docker Compose
    └─ Makefile
        ↓
        Docker Network (esteira-network)
            ├─ PostgreSQL 13 + PostGIS
            │  ├─ Database: esteira_geo
            │  ├─ PostGIS Extension
            │  ├─ Spatial Indexes (GIST)
            │  └─ Health Check
            │
            ├─ MinIO (S3 Simulado)
            │  ├─ MinIO Server (port 9000)
            │  ├─ MinIO Console (port 9001)
            │  └─ Buckets: bronze, silver, gold
            │
            ├─ Pipeline ETL Container
            │  ├─ Python 3.9
            │  ├─ GDAL, GeoPandas, Rasterio
            │  └─ ETL Pipeline (Bronze → Silver → Gold → PostGIS)
            │
            └─ Flask Web Container
               ├─ Flask Server (port 5000)
               ├─ Gunicorn (4 workers)
               ├─ Nginx (reverse proxy)
               └─ REST APIs + Dashboard
```

### Volumes Docker

```
postgres_data/   → Armazena banco de dados PostgreSQL
minio_data/      → Armazena buckets MinIO (S3 simulado)
pipeline_bronze/ → Bronze layer (dados brutos GeoParquet)
pipeline_silver/ → Silver layer (dados normalizados)
pipeline_gold/   → Gold layer (dados processados)
```

### Fluxo de Execução

```
./docker.sh up           → Inicia containers
    ↓
Aguarda health checks (PostgreSQL, MinIO)
    ↓
./docker.sh pipeline     → Executa ETL pipeline
    ↓
    Bronze Loader     → Gera dados de exemplo (3 áreas + 100 cidadãos)
    ↓
    Silver Processor  → Valida e normaliza dados
    ↓
    Gold Processor    → Spatial join (cidadãos atingidos por enchente)
    ↓
    PostGIS Loader    → Insere geometrias no banco
    ↓
    Flask Dashboard   → Visualiza resultados em http://localhost:5000
```

### Quando Usar

✅ Desenvolvimento local  
✅ Testes antes de deploy em nuvem  
✅ Sem credenciais AWS/Huawei  
✅ Ambiente isolado e reproduzível  
✅ Feedback rápido (sem esperar provisioning)  

---

## 📊 Diagrama 3: Fluxo Medallion (Bronze → Silver → Gold)

**Uso**: Entender o **fluxo de dados** e transformações

### Camadas

```
INPUT
  ├─ 3 Flood Areas (Polygons)
  └─ 100 Citizens (Point Features)
       ↓

BRONZE LAYER (Raw Data)
  ├─ flooding_areas.parquet (3 records)
  ├─ citizens.parquet (100 records)
  ├─ Storage: S3/OBS or Local
  └─ Format: GeoParquet (CRS: EPSG:4326)
       ↓

SILVER LAYER (Normalized)
  ├─ Validação de geometrias
  ├─ Remoção de duplicatas
  ├─ Padronização de tipos (int64, datetime)
  ├─ Parsing de datas
  ├─ data_quality_score adicionado
  └─ Storage: S3/OBS or Local
       ↓

GOLD LAYER (Processed)
  ├─ Spatial Join
  │  └─ ST_Contains (citizen point within flood polygon)
  │
  ├─ 60 Affected Citizens
  │  ├─ Identified by flood area
  │  ├─ Severity level
  │  └─ Risk category
  │
  ├─ 40 Unaffected Citizens
  │  ├─ Safe zones
  │  └─ No flood risk
  │
  └─ 100 Total Summary
     └─ Statistics aggregated
          ↓

PostGIS (Spatial Database)
  ├─ flooding_areas table
  │  ├─ GEOMETRY(POLYGON, 4326)
  │  └─ GIST spatial index
  │
  ├─ citizens table
  │  ├─ GEOMETRY(POINT, 4326)
  │  └─ affected_by_flooding BOOLEAN
  │  └─ GIST spatial index
  │
  └─ Spatial Queries
     ├─ ST_Contains()
     ├─ ST_Distance()
     ├─ ST_Buffer()
     └─ v_citizens_summary VIEW
          ↓

VISUALIZATION (Flask Dashboard)
  ├─ REST APIs
  │  ├─ /api/geometries
  │  ├─ /api/stats
  │  └─ /health
  │
  ├─ Web UI (HTML/CSS/JS)
  │  ├─ Real-time cards
  │  ├─ Status indicators
  │  └─ Data tables
  │
  └─ Map Integration (opcional)
     ├─ Flood area polygons
     ├─ Citizens location points
     └─ Risk zones highlight
```

### Estatísticas Esperadas

```
Input: 100 citizens
  ├─ 60 within flood polygons → AFFECTED
  └─ 40 outside flood zones → UNAFFECTED

Output:
  ├─ affected_citizens.parquet (60 rows)
  ├─ unaffected_citizens.parquet (40 rows)
  ├─ all_citizens_evaluated.parquet (100 rows)
  └─ PostgreSQL tables with spatial indexes
```

---

## 🔄 Comparação: Terraform vs Docker

| Aspecto | Terraform/Ansible | Docker |
|---------|---|---|
| **Environment** | Nuvem (AWS/Huawei) | Local (Linux/macOS/Windows) |
| **Custo** | Pago (credenciais necessárias) | Grátis (local) |
| **Setup Time** | 10-30 min (provisionamento) | 2-3 min (containers) |
| **VMs** | Real (EC2/ECS) | Simulado (containers) |
| **Storage** | S3/OBS real | MinIO simulado |
| **Database** | RDS real | PostgreSQL container |
| **Ideal Para** | Produção | Desenvolvimento/Testes |
| **Escalabilidade** | Automática (cloud) | Manual (host limits) |
| **Persistência** | Cloud volumes | Docker volumes |

---

## 📚 Arquivos Relacionados

### Diagrama 1 (Terraform/Ansible)
- [terraform/main.tf](../terraform/main.tf)
- [terraform/modules/aws/](../terraform/modules/aws/)
- [terraform/modules/huawei/](../terraform/modules/huawei/)
- [ansible/processing.yml](../ansible/processing.yml)
- [ansible/presentation.yml](../ansible/presentation.yml)

### Diagrama 2 (Docker)
- [docker-compose.yml](../docker-compose.yml)
- [pipeline/Dockerfile](../pipeline/Dockerfile)
- [pipeline/Dockerfile.web](../pipeline/Dockerfile.web)
- [docker.sh](../docker.sh)
- [Makefile](../Makefile)

### Diagrama 3 (Medallion)
- [pipeline/etl/bronze_loader.py](../pipeline/etl/bronze_loader.py)
- [pipeline/etl/silver_processor.py](../pipeline/etl/silver_processor.py)
- [pipeline/etl/gold_processor.py](../pipeline/etl/gold_processor.py)
- [pipeline/etl/postgis_loader.py](../pipeline/etl/postgis_loader.py)
- [pipeline/main.py](../pipeline/main.py)

---

## 🎯 Fluxo de Trabalho Recomendado

```
1. Desenvolvimento Local (Docker)
   └─ ./docker.sh up && ./docker.sh pipeline
      └─ Testa lógica, valida dados

2. Testes Integrados (Docker + Makefile)
   └─ make test
      └─ Verifica todas as camadas (Bronze/Silver/Gold)

3. Deploy Cloud (Terraform)
   └─ terraform apply -var-file=envs/huawei-sp.tfvars
      └─ Provisiona infraestrutura real

4. Configuração Automática (Ansible)
   └─ ansible-playbook -i inventory.ini processing.yml
      └─ Configura VMs, instala dependências

5. Produção
   └─ Pipeline executa em cron (processing VM)
      └─ Dashboard acessível via web (presentation VM)
```

---

## 💡 Notas

- **Diagrama 1** é para quando você tem credenciais de nuvem e quer escalabilidade
- **Diagrama 2** é para quando você quer desenvolver localmente sem custos
- **Diagrama 3** é para entender como os dados fluem em ambos os casos

Os três diagramas podem coexistir: desenvolvedor usa Docker localmente, depois deploy com Terraform/Ansible em produção!
