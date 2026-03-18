# Pipeline - Esteira de Processamento Geoespacial

## 📋 Caso de Uso

**Batimento Geográfico de Áreas Atingidas por Enchentes - Rio Grande do Sul**

Objetivo: Identificar quais cidadãos estão em áreas atingidas por enchentes em Porto Alegre através de operações geoespaciais.

### Dados de Entrada

O pipeline suporta múltiplas fontes de dados:

#### 1. Dados gerados sinteticamente (bronze_loader)
- 3 áreas de enchente (polígonos) em Porto Alegre
- 100 cidadãos com coordenadas geradas via `numpy.random`

#### 2. CSV com coordenadas (`data/bronze/*.csv`)
- Exemplo: `citizens_sample.csv` (50 registros reais)
- Colunas obrigatórias: `latitude`, `longitude`
- `citizen_id` aceita inteiros ou strings (`C003`, `C004`...)
- `registered_date` é automaticamente renomeado para `registration_date`

#### 3. GeoJSON (`data/bronze/*.geojson`)
- Polígonos (áreas de enchente) ou pontos (cidadãos)
- Convertido automaticamente para GeoParquet na Silver

**Total processado com `citizens_sample.csv` presente:**
- Bronze: 3 áreas + 100 cidadãos sintéticos + 50 externos
- Silver consolidada: 150 cidadãos únicos
- Gold: 89 afetados + 61 não afetados

### Fluxo de Processamento

```
data/bronze/ (CSV/GeoJSON externos)
    ↓
[1/6] Bronze Layer  — gera dados sintéticos + salva CSV/GeoJSON adicionais
    ↓
[2/6] Silver — converte CSV/GeoJSON → GeoParquet (csv_geojson_converter)
    ↓
[2b/6] Silver — normaliza dados sintéticos + consolida com externos (silver_processor)
    ↓
[3/6] Gold — spatial join, classifica afetados/não afetados, deduplica por citizen_id
    ↓
[4/6] PostGIS — carrega tabelas citizens e flooding_areas (citizen_id como VARCHAR)
    ↓
[5/6] Resumo final
```

### Saída

Arquivos GeoParquet em `/data/gold/`:
1. `affected_citizens.parquet` — cidadãos em área atingida
2. `unaffected_citizens.parquet` — cidadãos fora de área atingida
3. `all_citizens_evaluated.parquet` — todos com status

---

## 🚀 Como Executar

### Via Docker (recomendado)

```bash
# Iniciar ambiente
docker compose up -d

# Executar pipeline
docker compose exec pipeline python /app/main.py

# Ver logs em tempo real
docker compose logs -f pipeline
```

### Localmente

```bash
cd pipeline
python -m venv venv
source venv/bin/activate  # Linux/macOS
# ou: .\venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt

# Configurar .env (copiar de .env.example)
cp ../.env.example .env

python main.py
```

### Executar etapa individual

```bash
docker compose exec pipeline python -c "from etl.bronze_loader import load_sample_data; load_sample_data()"
docker compose exec pipeline python -c "from etl.silver_processor import process_silver; process_silver()"
docker compose exec pipeline python -c "from etl.gold_processor import process_gold; process_gold()"
docker compose exec pipeline python -c "from etl.postgis_loader import load_to_postgis; load_to_postgis()"
```

---

## 📂 Estrutura de Arquivos

```
pipeline/
├── main.py                          # Orquestrador principal
├── config.py                        # Configurações centralizadas (storage, DB, paths)
├── requirements.txt
├── Dockerfile                       # Imagem ETL
├── Dockerfile.web                   # Imagem Flask
├── entrypoint.sh                    # Inicializa buckets MinIO e executa CMD
├── init_minio_buckets.py            # Cria buckets bronze/silver/gold no MinIO
├── postgis_init.sql                 # Extensões PostGIS (executado na inicialização do container)
├── etl/
│   ├── bronze_loader.py             # Gera dados sintéticos + exporta CSV/GeoJSON
│   ├── silver_processor.py          # Normaliza + consolida todas as fontes
│   ├── gold_processor.py            # Spatial join + deduplicação por citizen_id
│   ├── postgis_loader.py            # Carrega no PostgreSQL (citizen_id VARCHAR)
│   └── silver/
│       └── csv_geojson_converter.py # Converte CSV/GeoJSON → GeoParquet
├── watchers/
│   └── watch_bronze.py              # Polling em /data/bronze, dispara pipeline ao detectar mudanças
└── ansible/
    └── roles/presentation/files/
        ├── app.py                   # Flask app
        └── templates/index.html
```

---

## ⚙️ Configuração (`config.py`)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `AWS_ENDPOINT_URL` | `None` | URL do MinIO (ex: `http://minio:9000`) |
| `AWS_S3_BRONZE_BUCKET` | `bronze` | Bucket bronze |
| `LOCAL_BRONZE_PATH` | `/data/bronze` | Path local bronze |
| `LOCAL_SILVER_PATH` | `/data/silver` | Path local silver |
| `LOCAL_GOLD_PATH` | `/data/gold` | Path local gold |
| `RDS_HOST` | `localhost` | Host PostgreSQL |
| `RDS_DATABASE` | `esteira_geo` | Nome do banco |

O modo de storage é detectado automaticamente: `minio` → `s3` → `local`.

---

## 🗄️ Schema PostGIS

```sql
-- Áreas de enchente
CREATE TABLE flooding_areas (
    area_id SERIAL PRIMARY KEY,
    area_name VARCHAR(255),
    flood_date DATE,
    severity VARCHAR(50),
    affected_population INTEGER,
    geometry GEOMETRY(POLYGON, 4326)
);

-- Cidadãos (citizen_id VARCHAR para suportar IDs alfanuméricos como C003)
CREATE TABLE citizens (
    citizen_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    address TEXT,
    phone VARCHAR(20),
    registration_date DATE,
    geometry GEOMETRY(POINT, 4326),
    affected_by_flooding BOOLEAN DEFAULT FALSE
);

-- Índices espaciais
CREATE INDEX idx_flooding_areas_geom ON flooding_areas USING GIST(geometry);
CREATE INDEX idx_citizens_geom ON citizens USING GIST(geometry);
```

---

## 🔄 Watcher Automático

O serviço `pipeline-watcher` monitora `/data/bronze` por polling (a cada 5s) e dispara `main.py` automaticamente ao detectar novos arquivos:

```bash
# Ver logs do watcher
docker compose logs -f pipeline-watcher

# Testar: copiar arquivo para bronze
cp data/bronze/citizens_sample.csv data/bronze/novos_cidadaos.csv
# → pipeline dispara automaticamente em até 5 segundos
```

---

## 🌐 Flask Dashboard

| Endpoint | Descrição |
|----------|-----------|
| `/` | Dashboard com estatísticas |
| `/map` | Mapa interativo (Folium) |
| `/api/stats` | Estatísticas JSON |
| `/api/geojson` | Todos os dados em GeoJSON |
| `/health` | Health check |

---

## 📚 Documentação

- [CSV_GEOJSON_GUIDE.md](CSV_GEOJSON_GUIDE.md) — Como usar CSV/GeoJSON no pipeline
- [DOCKER.md](DOCKER.md) — Instruções detalhadas de Docker
- [testes_e_validacoes.txt](testes_e_validacoes.txt) — Comandos de teste e validação
