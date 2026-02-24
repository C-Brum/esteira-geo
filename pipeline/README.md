# Pipeline - Esteira de Processamento Geoespacial

## 📋 Caso de Uso

**Batimento Geográfico de Áreas Atingidas por Enchentes - Rio Grande do Sul**

Objetivo: Identificar quais cidadãos estão em áreas atingidas por enchentes em Porto Alegre através de operações geoespaciais.

### Dados de Entrada

O pipeline suporta múltiplos formatos de entrada:

#### 1. **CSV com Coordenadas** (recomendado para dados tabulares)
   - `pipeline/data/citizens_sample.csv` (50 registros)
   - Colunas: citizen_id, name, age, latitude, longitude, registered_date, city, district
   - Convertido para: GEOMETRY(POINT, EPSG:4326)

#### 2. **GeoJSON com Polígonos** (para áreas geográficas)
   - `pipeline/data/flooding_areas.geojson` (3 áreas de enchente)
   - Geometrias: Polygon (são de enchente)
   - Convertido automaticamente para GeoParquet

#### 3. **GeoJSON com Pontos** (para dados localizados)
   - `pipeline/data/citizens_additional.geojson` (5 cidadãos extra)
   - Geometrias: Point (localizações de cidadãos)
   - Convertido automaticamente para GeoParquet

#### 4. **Dados Gerados** (para testes sem fontes externas)
   - Polígonos de enchente: 3 registros
   - Cidadãos (gerados): 100 registros

**Total de Dados Processados:**
- Registros CSV: 50
- Registros GeoJSON Polygons: 3
- Registros GeoJSON Points: 5
- Registros Gerados: 100
- **Total: 158 registros geoespaciais**

### Processamento

```
INPUT (CSV/GeoJSON/Gerado)
    ↓
Bronze Layer (conversão para GeoParquet + ingestão)
    ↓
Silver Layer (normalização + validação + metadados)
    ↓
Gold Layer (spatial join + processamento)
    ↓
PostGIS (persistência em RDS)
    ↓
Flask Dashboard (visualização + APIs)
```

**Detalhes:**
- **Bronze**: Carrega dados brutos (CSV → Point, GeoJSON → preserva geometria)
- **Silver**: Normaliza tipos, valida geometrias, adiciona metadados
- **Gold**: Executa ST_Contains para identificar cidadãos em áreas de enchente
- **PostGIS**: Armazena com índices GIST para consultas rápidas
- **Flask**: Expõe APIs REST e dashboard interativo

### Saída

GeoParquets processados + dados em PostGIS:

1. `affected_citizens.parquet` - Cidadãos em área atingida (ST_Contains)
2. `unaffected_citizens.parquet` - Cidadãos fora de área atingida
3. `all_citizens_evaluated.parquet` - Todos os cidadãos com status

---

## 🚀 Como Executar

### 1. Setup Inicial

```bash
cd pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env na raiz do pipeline
cat > .env << EOF
AWS_S3_BRONZE_BUCKET=esteira-geo-bronze-xxxxx
AWS_S3_SILVER_BUCKET=esteira-geo-silver-xxxxx
AWS_S3_GOLD_BUCKET=esteira-geo-gold-xxxxx
RDS_HOST=esteira-geo-postgres.xxxxx.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=esteira-geo
RDS_USER=postgres
RDS_PASSWORD=postgrespw
EOF
```

### 3. Executar Pipeline Completo

```bash
python main.py
```

### 4. Testes Unitários

Veja documentação de testes:

```bash
# Teste da conversão CSV/GeoJSON → GeoParquet
python -m etl.silver.csv_geojson_converter

# Teste individual Bronze
python etl/bronze_loader.py

# Teste individual Silver
python etl/silver_processor.py

# Teste individual Gold
python etl/gold_processor.py

# Teste PostGIS (requer banco online)
python etl/postgis_loader.py
```

## 📚 Documentação

### Guias Principais

- **[CSV_GEOJSON_GUIDE.md](CSV_GEOJSON_GUIDE.md)** - Como usar CSV/GeoJSON no pipeline
- **[TESTES_CSV_GEOJSON.md](TESTES_CSV_GEOJSON.md)** - Testes e validações dos novos formatos
- **[DOCKER.md](DOCKER.md)** - Instruções de execução em Docker
- **[testes_e_validacoes.txt](testes_e_validacoes.txt)** - Logs de testes anteriores

---

## 📊 Estrutura de Arquivos

```
pipeline/
├── main.py                      # Orquestrador principal
├── config.py                    # Configurações centralizadas
├── requirements.txt             # Dependências Python
├── postgis_setup.sql            # Setup do banco de dados
├── testes_e_validacoes.txt      # Comandos de teste
├── etl/
│   ├── __init__.py
│   ├── bronze_loader.py         # Geração de dados exemplo
│   ├── silver_processor.py      # Normalização
│   ├── gold_processor.py        # Batimento geoespacial
│   └── postgis_loader.py        # Importação em RDS
├── data/                        # Arquivos de dados (local)
└── logs/                        # Logs de execução
    └── pipeline.log
```

---

## 📞 Próximas Etapas

1. Customizar dados (trocar polígonos/cidadãos)
2. Adicionar mais transformações em Silver
3. Integrar com Grafana para monitoramento
4. Implementar versionamento (MLflow/DVC)
