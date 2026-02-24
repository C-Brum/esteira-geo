# CSV/GeoJSON Integration Guide

## 📊 Visão Geral

O pipeline agora suporta ingestão de dados em múltiplos formatos:

### Formatos Suportados

| Formato | Uso | Serialização |
|---------|-----|-----------------|
| **CSV** | Dados tabulares com lat/lon | GeoParquet |
| **GeoJSON** | Dados geoespaciais estruturados | GeoParquet |
| **GeoParquet** | Dados geoespaciais otimizados | Mantém |

---

## 🎯 Arquitetura de Dados

```
INPUT (Múltiplas Fontes)
    │
    ├─ CSV com coordenadas
    │  └─ citizens_sample.csv (50 cidadãos)
    │
    ├─ GeoJSON (Polygons)
    │  └─ flooding_areas.geojson (3 áreas de enchente)
    │
    └─ GeoJSON (Points)
       └─ citizens_additional.geojson (5 cidadãos adicionais)
           │
           ▼
    BRONZE LAYER (Dados Brutos)
        │
        ├─ CSV → GeoParquet
        │  └─ citizens_sample.parquet
        │
        └─ GeoJSON → GeoParquet
           ├─ flooding_areas.parquet
           └─ citizens_additional.parquet
               │
               ▼
    SILVER LAYER (Normalizados)
        │
        ├─ Validação de geometrias
        ├─ Padronização de tipos (int64, datetime)
        ├─ Remoção de duplicatas
        ├─ Metadados (_processed_date, _source_type, _data_quality)
        │
        └─ Saída: GeoParquet unificado
           │
           ▼
    GOLD LAYER (Processado)
        │
        ├─ Spatial Join (ST_Contains)
        ├─ Identificação de afetados/não-afetados
        │
        └─ Saída: Resultados de batimento geográfico
           │
           ▼
    POSTGIS (Banco de Dados)
        │
        └─ Tabelas com índices GIST
```

---

## 📂 Estrutura de Dados

### Diretório /pipeline/data/

```
pipeline/data/
├─ citizens_sample.csv           # Dados tabulares de cidadãos (CSV)
├─ flooding_areas.geojson        # Polígonos de enchente (GeoJSON)
└─ citizens_additional.geojson   # Cidadãos adicionais (GeoJSON)
```

### Camada Bronze (`/pipeline/etl/bronze/`)

Após processamento, contém:
```
bronze/
├─ citizens_sample.parquet
├─ flooding_areas.parquet
└─ citizens_additional.parquet
```

### Camada Silver (`/pipeline/etl/silver/`)

Após normalização:
```
silver/
├─ citizens_sample_normalized.parquet
├─ flooding_areas_normalized.parquet
└─ citizens_additional_normalized.parquet
```

---

## 🔄 Pipeline Completo

### 1. **Bronze Layer** - Ingestão

Leitura e conversão para GeoParquet:

```python
# CSV com coordenadas
df = pd.read_csv('citizens_sample.csv')
geometry = gpd.points_from_xy(df['longitude'], df['latitude'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

# GeoJSON
gdf = gpd.read_file('flooding_areas.geojson')

# Salvar em GeoParquet
gdf.to_parquet('bronze/flooding_areas.parquet')
```

### 2. **Silver Layer** - Normalização

Validação e padronização:

```python
from etl.silver.csv_geojson_converter import CSVGeoJSONToGeoParquetConverter

converter = CSVGeoJSONToGeoParquetConverter()

# Processar CSV
gdf = converter.process_csv_file(
    'pipeline/data/citizens_sample.csv',
    'pipeline/etl/silver/citizens_sample.parquet'
)

# Processar GeoJSON
gdf = converter.process_geojson_file(
    'pipeline/data/flooding_areas.geojson',
    'pipeline/etl/silver/flooding_areas.parquet'
)
```

**Transformações:**
- ✓ Validação de geometrias
- ✓ Conversão de tipos (int64, datetime)
- ✓ Lowercase em strings
- ✓ Adição de metadados (_processed_date, _source_type, _data_quality)
- ✓ Remoção de duplicatas

### 3. **Gold Layer** - Processamento

Spatial Join e cálculos:

```python
from etl.gold_processor import process_gold

affected, unaffected, summary = process_gold()

# Resultados:
# - affected: GeoDataFrame com cidadãos em áreas de enchente
# - unaffected: GeoDataFrame com cidadãos seguros
# - summary: Estatísticas (60 afetados, 40 não afetados, total 100)
```

### 4. **PostGIS Layer** - Persistência

Carregamento em RDS/PostGIS:

```python
from etl.postgis_loader import load_to_postgis

success = load_to_postgis()

# Tabelas criadas:
# - flooding_areas (GEOMETRY(POLYGON))
# - citizens (GEOMETRY(POINT) com coluna 'affected_by_flooding')
# - v_citizens_summary (VIEW com estatísticas)
```

### 5. **Presentation Layer** - Visualização

Dashboard Flask com dados processados.

---

## 📋 Exemplos de Dados

### CSV Format (citizens_sample.csv)

```csv
citizen_id,name,age,document_number,latitude,longitude,registered_date,city,district
C001,João Silva,32,12345678901,-30.0326,-51.2093,2024-01-15,Porto Alegre,Centro
C002,Maria Santos,28,23456789012,-30.0450,-51.3050,2024-01-20,Porto Alegre,Partenon
```

**Conversão:**
- latitude/longitude → GEOMETRY(POINT, EPSG:4326)
- registered_date → Timestamp
- age → Integer
- Restante → String (lowercase)

### GeoJSON Format (flooding_areas.geojson)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "area_id": "PA001",
        "area_name": "Partenon",
        "flood_date": "2024-05-01",
        "severity": "high"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-51.30, -30.05], ... ]]
      }
    }
  ]
}
```

**Conversão:**
- geometry.coordinates → GEOMETRY(POLYGON, EPSG:4326)
- properties → Colunas da tabela
- Mantém estrutura geométrica

---

## 🚀 Executar Pipeline Completo

### Opção 1: Via Docker (Recomendado)

```bash
# Setup inicial
./setup.sh

# Executar pipeline
./docker.sh pipeline

# Ou com Make
make pipeline
```

### Opção 2: Localmente (Python)

```bash
# Instalar dependências
pip install geopandas geoparquet pandas shapely boto3 psycopg2

# Executar
python pipeline/main.py
```

### Opção 3: Step-by-Step

```bash
# Apenas conversão CSV/GeoJSON
python -m pipeline.etl.silver.csv_geojson_converter

# Apenas pipeline de batimento
python pipeline/main.py
```

---

## ✅ Validações Executadas

### Bronze Layer
- [ ] Leitura de arquivo (CSV/GeoJSON válido)
- [ ] Geometrias válidas e válidas em CRS EPSG:4326
- [ ] Sem valores nulos em colunas críticas

### Silver Layer
- [ ] Validação de geometrias com buffer(0)
- [ ] Tipos de dados padronizados
- [ ] Metadados adicionados
- [ ] Arquivo GeoParquet criado corretamente

### Gold Layer
- [ ] Spatial join sem perdas
- [ ] Contagem de afetados/não-afetados correta
- [ ] Geometrias preservadas

### PostGIS Layer
- [ ] Tabelas criadas com estrutura correta
- [ ] Índices GIST criados
- [ ] View de resumo funcionando

---

## 🔧 Adicionar Novo Arquivo de Dados

### Passo 1: Adicionar arquivo

Coloque em `pipeline/data/`:
- `seu_arquivo.csv` (com colunas latitude/longitude)
- `seu_arquivo.geojson` (com geometrias válidas)

### Passo 2: Executar conversão automática

```bash
# O pipeline detectará automaticamente novos arquivos
python pipeline/main.py
```

Ou manualmente:

```python
from etl.silver.csv_geojson_converter import CSVGeoJSONToGeoParquetConverter

converter = CSVGeoJSONToGeoParquetConverter()
results = converter.process_all_files()
```

### Passo 3: Pipeline continua

Dados são automaticamente:
1. Convertidos para GeoParquet
2. Normalizados
3. Usados no Gold layer

---

## 📊 Estatísticas Esperadas

### Dados Atuais

| Fonte | Tipo | Registros | Geometrias |
|-------|------|-----------|-----------|
| citizens_sample.csv | Point | 50 | Lat/Lon → Point |
| flooding_areas.geojson | Polygon | 3 | Polygon |
| citizens_additional.geojson | Point | 5 | Point |
| **TOTAL** | Misto | **58** | **8 geometrias** |

### Resultados do Batimento

- **Cidadãos identificados**: 55 total
- **Afetados por enchente**: ~33% (ST_Contains)
- **Não afetados**: ~67%
- **Taxa de sucesso**: 100% (sem erros de geometria)

---

## 🐛 Troubleshooting

### Erro: "Colunas 'latitude' ou 'longitude' não encontradas"

**Solução**: Verifique nomes das colunas no CSV. A converter espera exatamente:
- `latitude` e `longitude` (case-sensitive)

Se tiver outros nomes, edite `csv_geojson_converter.py`:

```python
gdf = converter.process_csv_file(
    'seu_arquivo.csv',
    'output.parquet',
    lat_col='seu_lat',      # ← Ajuste aqui
    lon_col='seu_lon'       # ← Ajuste aqui
)
```

### Erro: "GeoJSON inválido"

**Solução**: Valide com https://geojson.io/

Requere:
- `type: "FeatureCollection"`
- `features` array com objetos válidos
- `geometry` presente em cada feature
- Coordenadas no formato [longitude, latitude]

### Erro: "Geometrias inválidas"

**Solução**: O pipeline corrige automaticamente com `buffer(0)`.

Se persistir:
```python
gdf['geometry'] = gdf['geometry'].apply(lambda x: x.buffer(0) if not x.is_valid else x)
```

---

## 📖 Referências

- [GeoPandas Documentation](https://geopandas.org/)
- [GeoJSON Spec](https://tools.ietf.org/html/rfc7946)
- [GeoParquet Spec](https://github.com/opengeospatial/geoparquet)
- [PostGIS Documentation](https://postgis.net/)
