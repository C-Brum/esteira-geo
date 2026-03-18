# CSV/GeoJSON Integration Guide

## Visão Geral

O pipeline aceita arquivos externos em `data/bronze/<caso_de_uso>/` além dos dados gerados sinteticamente. Qualquer CSV ou GeoJSON colocado nessa pasta é automaticamente detectado pelo watcher, convertido para GeoParquet e consolidado na camada Silver antes do batimento geoespacial.

## Formatos Suportados

| Formato | Requisito | Resultado |
|---------|-----------|-----------|
| CSV | Colunas `latitude` e `longitude` | `GEOMETRY(POINT, EPSG:4326)` |
| GeoJSON | `FeatureCollection` válido | Preserva geometria original |

## Fluxo de Dados

```
data/bronze/enchentes_poa/
  ├── citizens_sample.csv       → silver/enchentes_poa/citizens_sample.parquet
  ├── novos_pontos_a.csv        → silver/enchentes_poa/novos_pontos_a.parquet
  ├── novos_pontos_b.geojson    → silver/enchentes_poa/novos_pontos_b.parquet
  └── ...
        ↓
  [csv_geojson_converter]  converte e salva em /data/silver/enchentes_poa/
        ↓
  [silver_processor]  normaliza dados sintéticos + consolida externos
        ↓
  silver/enchentes_poa/silver_citizens_data.parquet  (todos unificados, sem duplicatas)
        ↓
  [gold_processor]  spatial join
        ↓
  gold/enchentes_poa/{affected,unaffected,all_citizens_evaluated}.parquet
        ↓
  PostGIS (enchentes_poa_citizens, enchentes_poa_flooding_areas) + Flask
```

## Como Adicionar Dados

### CSV

Requisitos mínimos:

```csv
citizen_id,name,latitude,longitude
C092,João Silva,-30.0312,-51.2285
C093,Maria Santos,-30.0354,-51.2201
```

Colunas opcionais reconhecidas:
- `registered_date` → renomeado automaticamente para `registration_date`
- `address`, `phone`, `age`, `document_number`, `city`, `district`

`citizen_id` aceita inteiros (`0`, `1`...) ou strings (`C003`, `C004`...).

> `document_number` deve ser string — valores como `88899900123` são lidos com `dtype=str` para evitar conflito de schema no PyArrow.

```bash
cp meus_cidadaos.csv data/bronze/enchentes_poa/
# watcher detecta em até 5s e dispara o pipeline automaticamente
```

### GeoJSON

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "citizen_id": "C092", "name": "Ana Lima", "registration_date": "2024-07-01" },
      "geometry": { "type": "Point", "coordinates": [-51.2285, -30.0312] }
    }
  ]
}
```

> Coordenadas no formato GeoJSON: `[longitude, latitude]`

```bash
cp novos_dados.geojson data/bronze/enchentes_poa/
# watcher detecta em até 5s e dispara o pipeline automaticamente
```

## Casos de Uso (Subdiretórios)

O pipeline é controlado pela variável `USE_CASE` (default: `enchentes_poa`). Cada caso de uso tem seus próprios subdiretórios e tabelas PostGIS:

| Layer | Path |
|-------|------|
| Bronze | `data/bronze/<use_case>/` |
| Silver | `/data/silver/<use_case>/` |
| Gold | `/data/gold/<use_case>/` |
| PostGIS | `<use_case>_citizens`, `<use_case>_flooding_areas` |

Para criar um novo caso de uso:

```bash
mkdir data/bronze/novo_caso/
cp meus_dados.csv data/bronze/novo_caso/
USE_CASE=novo_caso docker compose exec pipeline python /app/main.py
```

## Normalização Automática

O `csv_geojson_converter` aplica as seguintes transformações:

- `document_number` e `citizen_id` lidos como string no CSV (`dtype=str`)
- Colunas com nome contendo `date`, `data`, `timestamp` ou `dt_` são convertidas para `datetime`
- `registered_date` → renomeado para `registration_date`
- Geometrias inválidas são corrigidas com `buffer(0)`
- Metadados adicionados: `_processed_date`, `_source_type`, `_data_quality`

O `silver_processor` consolida os arquivos externos com os dados sintéticos:

- Glob dinâmico em `silver/<use_case>/*.parquet` — qualquer arquivo sem prefixo `silver_` é consolidado automaticamente
- Deduplicação por `citizen_id` (string) — cidadão presente em múltiplas fontes é mantido uma única vez
- Colunas auxiliares com tipos mistos (`geometry_valid`, `_source_type`...) são removidas antes de salvar

## Schema PostGIS

Tabelas prefixadas pelo caso de uso. `citizen_id` é `VARCHAR(50)` para suportar IDs alfanuméricos:

```sql
-- Listar tabelas do caso de uso
SELECT tablename FROM pg_tables WHERE tablename LIKE 'enchentes_poa_%';

-- Consultar cidadãos
SELECT citizen_id, name, affected_by_flooding
FROM enchentes_poa_citizens LIMIT 5;
-- citizen_id pode ser '0', '1', 'C003', 'C086'...

-- Estatísticas
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN affected_by_flooding THEN 1 END) as afetados
FROM enchentes_poa_citizens;
```

## Troubleshooting

**Erro: "Colunas 'latitude' ou 'longitude' não encontradas"**
Verifique os nomes das colunas no CSV — devem ser exatamente `latitude` e `longitude`.

**Erro: "Could not convert '...' with type str: tried to convert to int64"**
O `document_number` estava sendo inferido como `int64`. Corrigido: o converter usa `dtype={'document_number': str, 'citizen_id': str}` no `pd.read_csv`.

**Colunas de texto virando `NaT`**
O converter converte apenas colunas cujo nome contém `date`, `data`, `timestamp` ou `dt_`. Se ainda ocorrer, verifique se o nome da coluna problemática contém algum desses termos.

**Watcher não dispara o pipeline**
O watcher compara `mtime` e `size` dos arquivos. Se o arquivo já existia quando o container subiu, use `touch` para atualizar o mtime:
```bash
touch data/bronze/enchentes_poa/meu_arquivo.csv
```

**PostGIS não atualiza após pipeline rodar**
Verifique se o serviço `pipeline-watcher` tem `RDS_HOST: postgis` no `docker-compose.yml`. Sem essa variável, o loader tenta conectar em `localhost` e falha silenciosamente.

**GeoJSON inválido**
Valide em https://geojson.io/ — o arquivo deve ter `type: "FeatureCollection"` e coordenadas no formato `[longitude, latitude]`.
