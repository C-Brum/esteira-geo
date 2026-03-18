# Testes e Validações — CSV/GeoJSON Integration

## Dados Disponíveis

```
data/bronze/enchentes_poa/
├── citizens_data.csv                    (100 cidadãos sintéticos — gerado pelo bronze_loader)
├── citizens_data.geojson                (100 cidadãos sintéticos — gerado pelo bronze_loader)
├── citizens_data.parquet                (gerado pelo bronze_loader)
├── citizens_sample.csv                  (50 cidadãos externos, C003–C052)
├── flooding_areas_porto_alegre.geojson  (3 áreas de enchente)
├── flooding_areas_porto_alegre.parquet  (gerado pelo bronze_loader)
├── novos_cidadaos_poa.csv               (15 cidadãos, C053–C067)
├── novos_pontos_a.csv                   (6 cidadãos, C068–C073)
├── novos_pontos_b.geojson               (6 cidadãos, C074–C079)
├── novos_pontos_c.csv                   (6 cidadãos, C080–C085)
└── novos_pontos_d.geojson               (6 cidadãos, C086–C091)
```

## Estatísticas Atuais

| Fonte | Formato | Registros | Cidadãos |
|-------|---------|-----------|----------|
| bronze_loader (sintético) | GeoParquet | 100 | int IDs |
| citizens_sample.csv | CSV | 50 | C003–C052 |
| novos_cidadaos_poa.csv | CSV | 15 | C053–C067 |
| novos_pontos_a.csv | CSV | 6 | C068–C073 |
| novos_pontos_b.geojson | GeoJSON | 6 | C074–C079 |
| novos_pontos_c.csv | CSV | 6 | C080–C085 |
| novos_pontos_d.geojson | GeoJSON | 6 | C086–C091 |
| **Silver consolidada** | GeoParquet | **189** | — |
| **Gold (afetados)** | GeoParquet | **114** | — |
| **Gold (não afetados)** | GeoParquet | **75** | — |

---

## Teste 1: Verificar arquivos no bronze

```bash
# Host
ls data/bronze/enchentes_poa/

# Container
docker compose exec pipeline find /data/bronze/enchentes_poa -type f
```

Esperado: todos os arquivos acima visíveis em ambos (bind mount).

---

## Teste 2: Conversão CSV → GeoParquet

```bash
docker compose exec pipeline python -c "
import pandas as pd, geopandas as gpd

df = pd.read_csv('/data/bronze/enchentes_poa/novos_pontos_c.csv', dtype={'document_number': str, 'citizen_id': str})
print('Colunas:', df.columns.tolist())
print('Registros:', len(df))

geometry = gpd.points_from_xy(df['longitude'], df['latitude'])
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs='EPSG:4326')
print('Geometrias válidas:', gdf.geometry.is_valid.all())
print('citizen_id dtype:', gdf['citizen_id'].dtype)
"
```

Esperado: 6 registros, geometrias válidas, `citizen_id` como string.

---

## Teste 3: Verificar normalização Silver

```bash
docker compose exec pipeline python -c "
import geopandas as gpd
from pathlib import Path

silver = Path('/data/silver/enchentes_poa')
for f in sorted(silver.glob('*.parquet')):
    gdf = gpd.read_parquet(f)
    print(f'{f.name}: {len(gdf)} registros')
"
```

Esperado:
- `citizens_sample.parquet`: 50 registros
- `novos_cidadaos_poa.parquet`: 15 registros
- `novos_pontos_a.parquet`: 6 registros
- `novos_pontos_b.parquet`: 6 registros
- `novos_pontos_c.parquet`: 6 registros
- `novos_pontos_d.parquet`: 6 registros
- `silver_citizens_data.parquet`: **189** registros consolidados
- `silver_flooding_areas_porto_alegre.parquet`: 3 registros

Verificar que `name` não é `NaT` e `citizen_id` é string:

```bash
docker compose exec pipeline python -c "
import geopandas as gpd
gdf = gpd.read_parquet('/data/silver/enchentes_poa/novos_pontos_c.parquet')
print('citizen_id dtype:', gdf['citizen_id'].dtype)
print('citizen_id sample:', gdf['citizen_id'].tolist())
print('name sample:', gdf['name'].tolist())
"
```

---

## Teste 4: Verificar consolidação Silver

```bash
docker compose exec pipeline python -c "
import geopandas as gpd
gdf = gpd.read_parquet('/data/silver/enchentes_poa/silver_citizens_data.parquet')
print('Total consolidado:', len(gdf))
print('citizen_id dtype:', gdf['citizen_id'].dtype)
assert gdf['citizen_id'].nunique() == len(gdf), 'DUPLICATAS ENCONTRADAS!'
print('Sem duplicatas: OK')
"
```

Esperado: 189 registros, sem duplicatas.

---

## Teste 5: Verificar Gold

```bash
docker compose exec pipeline python -c "
import geopandas as gpd
from pathlib import Path

gold = Path('/data/gold/enchentes_poa')
for f in sorted(gold.glob('*.parquet')):
    gdf = gpd.read_parquet(f)
    print(f'{f.name}: {len(gdf)} registros')

all_c = gpd.read_parquet(gold / 'all_citizens_evaluated.parquet')
print('Total avaliado:', len(all_c))
print('Afetados:', all_c['affected_by_flooding'].sum())
print('Não afetados:', (~all_c['affected_by_flooding']).sum())
assert len(all_c) == 189, f'Esperado 189, obtido {len(all_c)}'
print('Total correto: OK')
"
```

Esperado: 189 total, 114 afetados, 75 não afetados.

---

## Teste 6: Verificar PostGIS

```bash
docker compose exec postgis psql -U esteira_user -d esteira_geo -c "
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN affected_by_flooding THEN 1 END) as afetados,
    COUNT(CASE WHEN NOT affected_by_flooding THEN 1 END) as nao_afetados,
    pg_typeof(citizen_id) as tipo_citizen_id
FROM enchentes_poa_citizens
GROUP BY pg_typeof(citizen_id);
"
```

Esperado: total=189, afetados=114, não_afetados=75, tipo=`character varying`.

---

## Teste 7: Verificar Flask

```bash
curl -s http://localhost:5000/health
# {"status": "ok"}

curl -s http://localhost:5000/api/stats
# {"affected": 114, "affected_pct": "60.32", "total_citizens": 189, "unaffected": 75, "use_case": "enchentes_poa"}

curl -s http://localhost:5000/api/use_cases
# {"use_cases": ["enchentes_poa"]}

curl -s http://localhost:5000/api/geojson | python -c "
import json, sys
data = json.load(sys.stdin)
print('Features:', len(data['features']))
"
# Features: 192 (189 cidadãos + 3 áreas de enchente)
```

---

## Teste 8: Pipeline completo

```bash
docker compose exec pipeline python /app/main.py 2>&1 | grep -E "(✓|⚠|✗|CONCLUÍDO|Total Avaliado)"
```

Saída esperada:
```
✓ Bronze: 3 áreas + 100 cidadãos
✓ Conversão: 9 arquivo(s) processado(s)
✓ Consolidando citizens_sample.parquet: 50 registros
✓ Consolidando novos_cidadaos_poa.parquet: 15 registros
✓ Consolidando novos_pontos_a.parquet: 6 registros
✓ Consolidando novos_pontos_b.parquet: 6 registros
✓ Consolidando novos_pontos_c.parquet: 6 registros
✓ Consolidando novos_pontos_d.parquet: 6 registros
✓ Total consolidado: 189 cidadãos (100 sintéticos + 89 externos)
✓ Silver: 3 áreas + 189 cidadãos
✓ Gold: 114 afetados + 75 não afetados
✓ PIPELINE CONCLUÍDO COM SUCESSO!
  Total Avaliado: 189
```

---

## Teste 9: Watcher automático

```bash
# Ver logs do watcher em tempo real
docker compose logs -f pipeline-watcher

# Em outro terminal, adicionar arquivo novo
cp data/bronze/enchentes_poa/novos_pontos_c.csv data/bronze/enchentes_poa/teste_watcher.csv

# Aguardar ~5 segundos — watcher detecta e dispara pipeline automaticamente
# Remover após teste
rm data/bronze/enchentes_poa/teste_watcher.csv
```

> O watcher usa polling de 5s comparando `mtime` e `size` dos arquivos. Um `touch` no arquivo também dispara o pipeline.

---

## Checklist

- [x] Subdiretório `enchentes_poa/` em bronze, silver e gold
- [x] `citizens_sample.csv` visível no container via bind mount
- [x] `document_number` lido como string (`dtype={'document_number': str}`)
- [x] Conversão CSV → GeoParquet sem corrupção de colunas string
- [x] `registered_date` renomeado para `registration_date`
- [x] `citizen_id` string (`C003`) aceito sem erro
- [x] Silver consolidada com 189 cidadãos únicos
- [x] Gold com 189 avaliados (114 afetados + 75 não afetados)
- [x] PostGIS com tabelas prefixadas `enchentes_poa_citizens`, `enchentes_poa_flooding_areas`
- [x] `citizen_id VARCHAR(50)` no PostGIS
- [x] Flask exibindo 189 cidadãos com `?use_case=enchentes_poa`
- [x] Watcher com `RDS_HOST` configurado — PostGIS atualizado automaticamente
- [x] Watcher disparando pipeline ao detectar novos arquivos
