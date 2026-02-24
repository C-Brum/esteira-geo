# 🧪 Testes e Validações - CSV/GeoJSON Integration

## Resumo de Testes

### ✅ Dados Disponíveis

```
📂 pipeline/data/
├─ citizens_sample.csv           (50 cidadãos, CSV com lat/lon)
├─ flooding_areas.geojson        (3 áreas de enchente, GeoJSON Polygon)
└─ citizens_additional.geojson   (5 cidadãos extra, GeoJSON Point)
```

### 📊 Estatísticas

| Arquivo | Formato | Registros | Geometria | CRS |
|---------|---------|-----------|-----------|-----|
| citizens_sample.csv | CSV | 50 | Point (lat/lon) | EPSG:4326 |
| flooding_areas.geojson | GeoJSON | 3 | Polygon | EPSG:4326 |
| citizens_additional.geojson | GeoJSON | 5 | Point | EPSG:4326 |
| **TOTAL** | **Misto** | **58** | **8 geometrias** | **EPSG:4326** |

---

## 🧪 Teste 1: Validação de Dados de Entrada

### CSV Validation (citizens_sample.csv)

```bash
# Verificar estrutura
head -5 pipeline/data/citizens_sample.csv

# Esperado:
# citizen_id,name,age,document_number,latitude,longitude,registered_date,city,district
# C001,João Silva,32,12345678901,-30.0326,-51.2093,2024-01-15,Porto Alegre,Centro
# C002,Maria Santos,28,23456789012,-30.0450,-51.3050,2024-01-20,Porto Alegre,Partenon
# ...50 registros
```

**Validações:**
- ✓ 9 colunas presentes
- ✓ 50 registros de dados (sem header)
- ✓ Colunas latitude/longitude parecem válidas
- ✓ Datas em formato ISO (YYYY-MM-DD)

### GeoJSON Validation (flooding_areas.geojson)

```bash
# Verificar estrutura
cat pipeline/data/flooding_areas.geojson | python -m json.tool

# Esperado:
# {
#   "type": "FeatureCollection",
#   "features": [
#     {
#       "type": "Feature",
#       "properties": {...},
#       "geometry": {
#         "type": "Polygon",
#         "coordinates": [[[lon, lat], ...]]
#       }
#     }
#   ]
# }
```

**Validações:**
- ✓ Válido JSON format
- ✓ type = "FeatureCollection"
- ✓ 3 features
- ✓ geometry.type = "Polygon"
- ✓ coordinates em formato [longitude, latitude]

---

## 🧪 Teste 2: Conversão CSV → GeoParquet

### Python Test

```python
import geopandas as gpd
import pandas as pd
from pathlib import Path

# Testar leitura de CSV
csv_file = 'pipeline/data/citizens_sample.csv'
df = pd.read_csv(csv_file)

print(f"✓ CSV lido: {len(df)} registros")
print(f"✓ Colunas: {df.columns.tolist()}")
print(f"✓ Tipos:\n{df.dtypes}")

# Testar conversão para GeoDataFrame
geometry = gpd.points_from_xy(df['longitude'], df['latitude'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')

print(f"✓ GeoDataFrame criado: {len(gdf)} geometrias")
print(f"✓ Geometrias válidas: {gdf.geometry.is_valid.all()}")
print(f"✓ Bounds: {gdf.total_bounds}")

# Salvar em GeoParquet
output = 'pipeline/etl/bronze/citizens_sample.parquet'
Path(output).parent.mkdir(parents=True, exist_ok=True)
gdf.to_parquet(output)
print(f"✓ GeoParquet salvo: {output}")
```

### Comando Shell

```bash
# Via Python
python -c "
import geopandas as gpd
import pandas as pd

csv_file = 'pipeline/data/citizens_sample.csv'
df = pd.read_csv(csv_file)
geometry = gpd.points_from_xy(df['longitude'], df['latitude'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
gdf.to_parquet('pipeline/etl/bronze/citizens_sample.parquet')
print(f'✓ Convertido: {len(gdf)} registros')
"
```

---

## 🧪 Teste 3: Conversão GeoJSON → GeoParquet

### Python Test

```python
import geopandas as gpd

# Testar leitura de GeoJSON
geojson_file = 'pipeline/data/flooding_areas.geojson'
gdf = gpd.read_file(geojson_file)

print(f"✓ GeoJSON lido: {len(gdf)} registros")
print(f"✓ Colunas: {gdf.columns.tolist()}")
print(f"✓ Geometrias válidas: {gdf.geometry.is_valid.all()}")
print(f"✓ Tipo de geometria: {gdf.geometry.type.unique()}")

# Salvar em GeoParquet
output = 'pipeline/etl/bronze/flooding_areas.parquet'
gdf.to_parquet(output)
print(f"✓ GeoParquet salvo: {output}")
```

---

## 🧪 Teste 4: Normalização Silver Layer

### Python Test - CSV

```python
from etl.silver.csv_geojson_converter import CSVGeoJSONToGeoParquetConverter

converter = CSVGeoJSONToGeoParquetConverter()

# Processar arquivo CSV
gdf = converter.process_csv_file(
    'pipeline/data/citizens_sample.csv',
    'pipeline/etl/silver/citizens_sample.parquet'
)

print(f"✓ CSV normalizado: {len(gdf)} registros")
print(f"✓ Colunas adicionadas: {[c for c in gdf.columns if c.startswith('_')]}")
print(f"✓ Arquivo GeoParquet salvo")

# Verificar dados normalizados
print(f"\nDados de exemplo:")
print(gdf.head())
```

### Python Test - GeoJSON

```python
from etl.silver.csv_geojson_converter import CSVGeoJSONToGeoParquetConverter

converter = CSVGeoJSONToGeoParquetConverter()

# Processar arquivo GeoJSON
gdf = converter.process_geojson_file(
    'pipeline/data/flooding_areas.geojson',
    'pipeline/etl/silver/flooding_areas.parquet'
)

print(f"✓ GeoJSON normalizado: {len(gdf)} registros")
print(f"✓ Propriedades preservadas: {[c for c in gdf.columns if c != 'geometry']}")
print(f"✓ Arquivo GeoParquet salvo")

print(f"\nDados de exemplo:")
print(gdf.head())
```

### Teste Automático Completo

```bash
# Via pipeline
cd pipeline
python -c "
from etl.silver.csv_geojson_converter import CSVGeoJSONToGeoParquetConverter

converter = CSVGeoJSONToGeoParquetConverter()
results = converter.process_all_files()

print(f'✓ Total de arquivos: {results[\"total_files\"]}')
print(f'✓ Sucesso: {results[\"successful\"]}')
print(f'✓ Registros processados: {results[\"total_records\"]}')

for filename, result in results['details'].items():
    if result['status'] == 'success':
        print(f'  ✓ {filename}: {result[\"records\"]} registros')
    else:
        print(f'  ✗ {filename}: {result[\"error\"]}')
"
```

---

## 🧪 Teste 5: Spatial Join (Gold Layer)

### Python Test

```python
import geopandas as gpd

# Carregar dados normalizados da Silver
citizens = gpd.read_parquet('pipeline/etl/silver/citizens_*.parquet')
flooding_areas = gpd.read_parquet('pipeline/etl/silver/flooding_areas.parquet')

print(f"✓ Carregados: {len(citizens)} cidadãos + {len(flooding_areas)} áreas")

# Spatial Join
affected = gpd.sjoin(citizens, flooding_areas, how='inner', predicate='within')

print(f"✓ ST_Contains: {len(affected)} cidadãos dentro de áreas de enchente")

# Não afetados
all_citizen_ids = set(citizens['citizen_id'].unique())
affected_ids = set(affected['citizen_id'].unique())
unaffected_ids = all_citizen_ids - affected_ids

print(f"✓ Cidadãos seguros: {len(unaffected_ids)}")
print(f"✓ Total: {len(all_citizen_ids)}")
```

---

## 🧪 Teste 6: Pipeline Completo

### Executar via Docker

```bash
# Setup (primeira vez)
./setup.sh

# Executar pipeline completo
./docker.sh pipeline

# Esperado:
# [1/6] BRONZE - Carregando dados...
# ✓ Bronze: 3 áreas + 100 cidadãos
#
# [2/6] SILVER - Convertendo CSV/GeoJSON → GeoParquet...
# ✓ Conversão: 3 arquivo(s) processado(s)
#   Total de registros convertidos: 58
#
# [2b/6] SILVER - Normalizando dados gerados...
# ✓ Silver: 3 áreas + 100 cidadãos
#
# [3/6] GOLD - Batimento geográfico...
# ✓ Gold: 60+ afetados + 40- não afetados
#
# [4/6] POSTGIS - Importar dados...
# ✓ PostGIS carregado
#
# [5/6] RESUMO FINAL
# ✓ PIPELINE CONCLUÍDO COM SUCESSO!
```

### Executar via CLI

```bash
# Setup
pip install geopandas geoparquet pandas shapely boto3 psycopg2

# Run
cd pipeline
python main.py

# Esperado: Saída idêntica
```

### Executar apenas Conversão

```bash
cd pipeline
python -m etl.silver.csv_geojson_converter

# Esperado:
# ================================================================================
# INICIANDO CONVERSÃO CSV/GeoJSON → GeoParquet
# ================================================================================
# Lendo CSV: citizens_sample.csv
# Normalizando CSV...
# Salvando GeoParquet...
# ✓ citizens_sample.csv: 50 registros → etl/silver/citizens_sample.parquet
# 
# Lendo GeoJSON: flooding_areas.geojson
# Normalizando GeoJSON...
# Salvando GeoParquet...
# ✓ flooding_areas.geojson: 3 registros → etl/silver/flooding_areas.parquet
# 
# Lendo GeoJSON: citizens_additional.geojson
# Normalizando GeoJSON...
# Salvando GeoParquet...
# ✓ citizens_additional.geojson: 5 registros → etl/silver/citizens_additional.parquet
# ================================================================================
# RESUMO DA CONVERSÃO
# ================================================================================
# Total de arquivos: 3
# Sucesso: 3
# Falhas: 0
# Total de registros: 58
# ================================================================================
```

---

## 🧪 Teste 7: Validação de Arquivos Criados

### Listar Arquivos Criados

```bash
# Bronze layer
ls -lh pipeline/etl/bronze/

# Esperado:
# citizens_sample.parquet (50 registros)
# flooding_areas.parquet (3 registros)
# citizens_additional.parquet (5 registros)

# Silver layer
ls -lh pipeline/etl/silver/

# Esperado:
# citizens_sample.parquet (50 normalizados + metadados)
# flooding_areas.parquet (3 normalizados + metadados)
# citizens_additional.parquet (5 normalizados + metadados)
```

### Inspecionar Parquet

```bash
# Via Python
python -c "
import geopandas as gpd

# Bronze
print('=== BRONZE ===')
gdf = gpd.read_parquet('pipeline/etl/bronze/citizens_sample.parquet')
print(f'Registros: {len(gdf)}')
print(f'Colunas: {gdf.columns.tolist()}')
print(f'Geometrias: {gdf.geometry.type.unique()}')
print(gdf.head())

# Silver
print('\n=== SILVER ===')
gdf = gpd.read_parquet('pipeline/etl/silver/citizens_sample.parquet')
print(f'Registros: {len(gdf)}')
print(f'Colunas: {gdf.columns.tolist()}')
print(f'Metadados adicionados: {[c for c in gdf.columns if c.startswith(\"_\")]}')
print(gdf.head())
"
```

---

## 📋 Checklist de Testes

- [ ] **Teste 1**: CSV com 50 registros lido corretamente
- [ ] **Teste 2**: GeoJSON com 3 features lido corretamente
- [ ] **Teste 3**: CSV convertido para GeoParquet com geometrias Point
- [ ] **Teste 4**: GeoJSON convertido para GeoParquet com geometrias Polygon
- [ ] **Teste 5**: Normalização adiciona metadados (_processed_date, _source_type)
- [ ] **Teste 6**: Spatial join encontra cidadãos em áreas de enchente
- [ ] **Teste 7**: Pipeline completo executa sem erros
- [ ] **Teste 8**: Dados carregados em PostGIS com sucesso
- [ ] **Teste 9**: Flask Dashboard exibe dados corretamente

---

## 🎯 Próximas Etapas

1. **Adicionar mais fontes de dados**:
   - Outros distritos de Porto Alegre
   - Dados históricos de enchentes
   - Dados demográficos adicionais

2. **Melhorar qualidade**:
   - Validação mais rigorosa em Silver
   - Deduplicação de cidadãos
   - Padronização de endereços

3. **Expandir análises**:
   - Cálculo de distância até áreas de enchente
   - Identificação de rotas de evacuação
   - Análise de vulnerabilidade

4. **Integrar com sistemas**:
   - API REST para consultas
   - Webhooks para alertas
   - Integração com sistemas de defesa civil
