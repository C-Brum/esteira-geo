# CSV/GeoJSON Integration — Resumo

## Estado Atual

O pipeline processa dados de múltiplas fontes e consolida tudo antes do batimento geoespacial.

### Resultados com `citizens_sample.csv` presente

| Camada | Registros | Detalhe |
|--------|-----------|---------|
| Bronze (sintético) | 100 cidadãos + 3 áreas | Gerado pelo `bronze_loader` |
| Bronze (externo) | 50 cidadãos | `data/bronze/citizens_sample.csv` |
| Silver consolidada | **150 cidadãos** | Deduplicado por `citizen_id` |
| Gold — afetados | **89** | Spatial join com áreas de enchente |
| Gold — não afetados | **61** | Fora das áreas |
| PostGIS | **150** | `citizen_id VARCHAR(50)` |
| Flask `/api/stats` | **150** | `affected_pct: 59.33%` |

---

## Correções Implementadas

### Volume bronze como bind mount
- Antes: `pipeline_bronze` era volume Docker nomeado — arquivos do host não chegavam ao container
- Depois: `./data/bronze:/data/bronze` — bind mount direto, watcher e pipeline enxergam os mesmos arquivos

### `normalize_dataframe` não corrompe colunas string
- Antes: toda coluna `object` era tentada como datetime — `name`, `phone` viravam `NaT`
- Depois: apenas colunas cujo nome contém `date`, `data`, `timestamp` ou `dt_` são convertidas

### Normalização de schema no CSV converter
- `registered_date` → renomeado automaticamente para `registration_date`
- `citizen_id` aceita inteiros ou strings (`C003`, `C004`...)

### Consolidação na Silver
- `silver_processor.consolidate_citizens()` lê `citizens_sample.parquet` da silver e faz merge com os sintéticos
- Deduplicação por `citizen_id` (convertido para string para comparação uniforme)
- Colunas auxiliares com tipos mistos removidas antes do `to_parquet`

### PostGIS — `citizen_id VARCHAR(50)`
- Antes: `INTEGER PRIMARY KEY` — quebrava com `C003`
- Depois: `VARCHAR(50)` com migração automática na primeira execução
- `postgis_loader` usa `str(row['citizen_id'])` e `.get()` com fallback para campos opcionais

### Watcher funcionando
- Antes: `ENTRYPOINT` do Dockerfile sobrescrevia o `command` do docker-compose — watcher ficava em `tail -f /dev/null`
- Depois: `entrypoint.sh` usa `exec "$@"` para passar controle ao CMD

### Upload MinIO no Gold
- Antes: `boto3.client('s3')` sem `endpoint_url` — ignorava o MinIO
- Depois: lê `AWS_ENDPOINT_URL` das variáveis de ambiente, igual ao silver_processor

### Deduplicação no Gold
- Antes: `all_citizens_evaluated` podia ter 102 registros (cidadão em 2 áreas = 2 linhas)
- Depois: `drop_duplicates(subset=['citizen_id'])` nas 3 funções de geração, mantendo `affected=True` em caso de conflito

---

## Arquivos Modificados

| Arquivo | Mudança |
|---------|---------|
| `pipeline/entrypoint.sh` | `exec "$@"` em vez de `tail -f /dev/null` |
| `pipeline/etl/silver/csv_geojson_converter.py` | `normalize_dataframe` corrigido; alias `registered_date` |
| `pipeline/etl/silver_processor.py` | `normalize_citizens` aceita citizen_id string; `consolidate_citizens()` adicionado |
| `pipeline/etl/gold_processor.py` | `drop_duplicates` nas 3 funções; `save_to_gold` com suporte MinIO |
| `pipeline/etl/postgis_loader.py` | `citizen_id VARCHAR(50)`; migração automática; `str()` em vez de `int()` |
| `docker-compose.yml` | `./data/bronze:/data/bronze` bind mount; watcher usa `build` em vez de `image` |

---

## Como Adicionar Novas Fontes

1. Copiar arquivo para `data/bronze/`:
   ```bash
   cp nova_fonte.csv data/bronze/
   ```

2. O watcher detecta e dispara o pipeline automaticamente (até 5s), ou execute manualmente:
   ```bash
   docker compose exec pipeline python /app/main.py
   ```

3. Para incluir um novo parquet na consolidação Silver, adicionar o nome em `CITIZEN_PATTERNS` no `silver_processor.py`:
   ```python
   CITIZEN_PATTERNS = ['citizens_sample.parquet', 'nova_fonte.parquet']
   ```

---

## Documentação Relacionada

- [pipeline/CSV_GEOJSON_GUIDE.md](pipeline/CSV_GEOJSON_GUIDE.md) — guia de uso
- [pipeline/TESTES_CSV_GEOJSON.md](pipeline/TESTES_CSV_GEOJSON.md) — testes e validações
- [pipeline/README.md](pipeline/README.md) — documentação completa do pipeline
- [pipeline/DOCKER.md](pipeline/DOCKER.md) — ambiente Docker
