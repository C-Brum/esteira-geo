# Esteira Geo — Workspace

Workspace completo para uma **esteira de processamento de dados geográficos** usando arquitetura **Medallion** (Bronze → Silver → Gold), orquestrada pelo **Apache Airflow**.

## 📋 Estrutura do Projeto

```
esteira-geo/
├── airflow/                # Orquestração com Apache Airflow
│   ├── Dockerfile          # Imagem Airflow com dependências geoespaciais
│   └── dags/
│       ├── esteira_geo_dag.py           # DAG principal (silver → gold → postgis)
│       ├── esteira_geo_watcher_dag.py   # Watcher S3 (dispara pipeline a cada 30s)
│       └── esteira_geo_manutencao_dag.py # Limpeza diária do histórico (30 dias)
├── terraform/              # Infraestrutura como código (multi-cloud)
│   ├── modules/
│   │   ├── aws/           # Módulo AWS (S3, EC2, RDS)
│   │   ├── huawei/        # Módulo Huawei Cloud (OBS, ECS, RDS)
│   │   └── hcso/          # Placeholder para HCSO
│   ├── envs/              # Arquivos de configuração por ambiente
│   │   ├── dev.tfvars
│   │   ├── aws.tfvars
│   │   └── huawei-sp.tfvars
│   └── [main.tf, providers.tf, variables.tf, outputs.tf]
├── pipeline/              # Esteira de processamento em Python
│   ├── etl/
│   │   ├── bronze_loader.py      # Upload de dados de teste para o bronze
│   │   ├── silver_processor.py   # Normalização + acumulação (schema-tolerante)
│   │   ├── gold_processor.py     # Spatial join + process_gold_areas_only()
│   │   └── postgis_loader.py     # Sincronização PostGIS (sempre lê do gold)
│   ├── watchers/
│   │   └── watch_bronze.py       # Watcher legado (substituído pelo Airflow)
│   ├── web/
│   │   ├── app.py                # Flask (multi-use-case, fallback automático)
│   │   └── templates/
│   │       ├── index.html
│   │       └── map.html          # Mapa Leaflet com SVG markers + fitBounds
│   ├── main.py            # Orquestrador legado (uso sem Airflow)
│   ├── config.py          # Configuração (USE_CASE, paths, credenciais)
│   └── requirements.txt
├── notebooks/             # Notebooks Jupyter interativos
│   ├── esteira_geo.ipynb  # Fluxo completo Bronze → Silver → Gold → PostGIS
│   └── utilitarios.ipynb  # Funções de manutenção (limpar banco, silver, gold)
├── data/
│   └── bronze/
│       └── automatizado/          # Área monitorada pelo Airflow watcher
│           ├── enchentes_poa/
│           ├── enchentes_mg/
│           └── enchentes_rj/
├── diagrams/              # Diagramas Mermaid da arquitetura
├── docs/                  # Documentação técnica
└── README.md
```

## 🏗️ Arquitetura

A esteira segue o padrão **Medallion** orquestrado pelo **Airflow**:

- **Bronze**: Dados brutos (S3/OBS). Prefixo `automatizado/<use_case>/` monitorado pelo `esteira_geo_watcher`
- **Silver**: Dados normalizados e validados (S3/OBS) — acumulativo por `citizen_id`/`area_id`, tolerante a schemas diferentes
- **Gold**: Resultado do batimento geoespacial (S3/OBS) — única fonte de verdade do PostGIS. Sempre gerado antes de sincronizar o banco
- **PostGIS**: Espelho do gold (TRUNCATE + INSERT a cada execução)
- **Flask**: Dashboard e APIs — fallback automático para use_case disponível

**Componentes de Infraestrutura**:
- 2 VMs: `processing` (Airflow + Python) + `presentation` (Flask, acesso internet)
- RDS PostgreSQL com PostGIS (compartilhado: pipeline + Airflow metadata)
- 3 buckets OBS/S3 (bronze, silver, gold)

---

## 🐳 Desenvolvimento Local com Docker

**Opção recomendada para desenvolvimento e testes locais sem credenciais de nuvem.**

O ambiente Docker simula toda a infraestrutura localmente (PostgreSQL + PostGIS + MinIO + Airflow + Flask + Pipeline ETL).

### Quick Start Docker

```bash
# 1. Iniciar todo o ambiente
docker compose up -d

# 2. Aguarde ~60 segundos (Airflow init + serviços)
docker compose ps

# 3. Acessar serviços
# Airflow UI:       http://localhost:8080  (admin/admin)
# Dashboard Flask:  http://localhost:5000
# JupyterLab:       http://localhost:8888/lab?token=esteira
# MinIO Console:    http://localhost:9001  (minioadmin/minioadmin123)
# PostgreSQL:       localhost:5432         (esteira_user/esteira_local_2025)
```

### Serviços Docker

| Container | Porta | Descrição |
|-----------|-------|-----------|
| `esteira-postgis` | 5432 | PostgreSQL + PostGIS (pipeline + Airflow metadata) |
| `esteira-minio` | 9000/9001 | MinIO — S3 simulado |
| `esteira-airflow-webserver` | 8080 | Airflow UI |
| `esteira-airflow-scheduler` | — | Scheduler + executor das DAGs |
| `esteira-pipeline` | — | Container ETL (idle, testes manuais) |
| `esteira-web` | 5000 | Flask dashboard |
| `esteira-jupyter` | 8888 | JupyterLab |

### DAGs Airflow

| DAG | Schedule | Descrição |
|-----|----------|-----------|
| `esteira_geo_watcher` | a cada 30s | Monitora `bronze/automatizado/`, dispara `esteira_geo` por use_case |
| `esteira_geo` | manual/trigger | silver → branch → gold → postgis |
| `esteira_geo_manutencao` | diário | Limpa histórico do banco (mantém 30 dias) |

### Ingestão de Dados

Deposite arquivos em `bronze/automatizado/<use_case>/` — o watcher detecta em até 30s e dispara o pipeline automaticamente:

```
bronze/
└── automatizado/
    ├── enchentes_poa/      ← watcher detecta → dispara esteira_geo (use_case=enchentes_poa)
    │   ├── arquivo.csv
    │   └── processados/    ← movido após salvar no silver com sucesso
    ├── enchentes_mg/
    └── enchentes_rj/
```

**Via MinIO Console** (http://localhost:9001): faça upload direto para `bronze/automatizado/<use_case>/`

**Via CLI**:
```bash
# Upload via bronze_loader (dados sintéticos)
docker compose exec pipeline python /app/etl/bronze_loader.py

# Trigger manual de um use_case específico
docker compose exec airflow-scheduler \
  airflow dags trigger esteira_geo --conf '{"use_case": "enchentes_poa"}'
```

**Formatos suportados:**
- CSV com colunas `latitude` e `longitude`
- GeoJSON (pontos ou polígonos)

**Normalização automática:** `registered_date` → `registration_date` | `citizen_id` aceita inteiros ou strings (`C003`, `C004`...) | `document_number` sempre lido como string

### Cenários do Pipeline

| Conteúdo do bronze | Caminho na DAG | Resultado |
|---|---|---|
| Áreas + cidadãos | silver → gold → postgis | Batimento completo no PostGIS |
| Só áreas | silver → gold_areas_only → postgis_areas_only | Polígonos visíveis no mapa |
| Só cidadãos | silver → skip_gold | Cidadãos acumulados no silver, aguarda áreas |
| Bronze vazio | silver (encerra sem retry) | Nenhuma ação |

### Executar Pipeline Manualmente (sem Airflow)

```bash
# Pipeline completo via main.py
docker compose exec -e USE_CASE=enchentes_poa pipeline python /app/main.py

# Etapa individual
docker compose exec pipeline python -c \
  "from etl.silver_processor import process_silver; process_silver()"
```

### JupyterLab

O notebook `notebooks/esteira_geo.ipynb` replica o fluxo completo de forma interativa:

| Célula | O que faz |
|--------|-----------|
| 0 — Configuração | Define `USE_CASE` e exibe conexões |
| 1 — Bronze | Lista arquivos no bucket S3/MinIO |
| 2 — Silver | `process_silver()` em modo exploratório (não move arquivos) |
| 3 — Gold | `process_gold()`, mostra resultado do spatial join |
| 4 — PostGIS | Sincroniza via `load_to_postgis()` |
| 5 — Consultas SQL | Queries direto no PostGIS |
| 6 — Mapa | Abre o mapa Leaflet do Flask via IFrame |
| 7 — Ingestão manual | Upload de arquivo para o bronze + reprocessamento |

O notebook `notebooks/utilitarios.ipynb` oferece funções de manutenção:

| Função | O que faz |
|--------|-----------|
| `limpar_banco()` | Remove tabelas de use_case(s) do PostGIS |
| `limpar_silver_gold()` | Remove objetos dos buckets silver e gold |
| `mover_processados()` | Devolve arquivos de `processados/` para reprocessamento |
| `apagar_use_case()` | Remove tudo de um use_case (PostGIS + silver + gold + bronze) |

Todas as funções têm `confirmar=False` por padrão (dry-run) — execute com `confirmar=True` para aplicar.

### Scripts de Gerenciamento

**Linux/macOS:**
```bash
chmod +x setup.sh docker.sh debug.sh
./setup.sh        # Setup inicial
./docker.sh up    # Iniciar
./docker.sh down  # Parar
```

**Windows PowerShell:**
```powershell
.\docker.ps1 status
.\docker.ps1 pipeline
.\docker.ps1 down
```

**Makefile:**
```bash
make up       # Iniciar
make pipeline # Executar pipeline
make down     # Parar
```

---

## 🚀 Deploy em Nuvem

### Pré-requisitos

1. **Terraform** >= 1.0
2. **Credenciais da Nuvem** (AWS ou Huawei Cloud)
3. **SSH Key Pair**

### Deploy AWS

```bash
cd terraform
cp envs/aws.tfvars terraform.tfvars
export AWS_ACCESS_KEY_ID="sua-access-key"
export AWS_SECRET_ACCESS_KEY="sua-secret-key"
terraform init && terraform apply
```

### Deploy Huawei Cloud (São Paulo)

```bash
cd terraform
cp envs/huawei-sp.tfvars terraform.tfvars
export HW_ACCESS_KEY="seu-access-key"
export HW_SECRET_KEY="seu-secret-key"
terraform init && terraform apply
```

### Outputs do Terraform

```bash
terraform output  # Exibe IPs das VMs, endpoints RDS, nomes dos buckets
```

### Configurar VMs com Ansible

```bash
pip install ansible
cd ansible

# Editar inventory.ini com os IPs do terraform output
ansible-playbook -i inventory.ini processing.yml    # VM de processamento (Airflow + pipeline)
ansible-playbook -i inventory.ini presentation.yml  # VM de apresentação (Flask + Nginx)
```

---

## 📊 Verificar Dados

### PostGIS

```bash
docker compose exec postgis psql -U esteira_user -d esteira_geo

-- Listar use_cases disponíveis
SELECT tablename FROM pg_tables WHERE tablename LIKE '%_citizens';

-- Estatísticas de um use_case
SELECT COUNT(*) as total,
       SUM(CASE WHEN affected_by_flooding THEN 1 ELSE 0 END) as afetados
FROM enchentes_poa_citizens;
```

### Flask APIs

```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/use_cases
curl "http://localhost:5000/api/stats?use_case=enchentes_poa"
curl "http://localhost:5000/api/geojson?use_case=enchentes_poa"
```

---

## 🔧 Troubleshooting

**Airflow não inicia**
```bash
docker compose logs airflow-init
docker compose logs airflow-scheduler
```

**DAG não detecta arquivos no bronze**
- Verifique se o arquivo está em `automatizado/<use_case>/` (não em `processados/`)
- O watcher roda a cada 30s — aguarde até 1 minuto
- Verifique se a DAG `esteira_geo_watcher` está ativa na UI (http://localhost:8080)

**Arquivo foi para `processados/` mas não apareceu no frontend**
- O silver pode ter falhado antes de salvar — use `mover_processados()` no notebook utilitários para reprocessar

**Mapa não aparece / erro no browser**
- Verifique se há dados no PostGIS: `curl http://localhost:5000/api/use_cases`
- Se o use_case padrão não existir, o Flask usa automaticamente o primeiro disponível

**Pipeline falha com erro de schema**
- O `_safe_concat` do silver tolera schemas diferentes — verifique os logs do Airflow na UI

**Histórico do Airflow muito grande**
- A DAG `esteira_geo_manutencao` limpa automaticamente runs com mais de 30 dias
- Para limpeza manual: use o notebook `utilitarios.ipynb`

**PostGIS não atualiza após pipeline rodar**
- Verifique se `RDS_HOST: postgis` está configurado no scheduler do Airflow no `docker-compose.yml`

**Jupyter — alterações no código do pipeline não refletem**
- O Jupyter usa volume bind `./pipeline:/app/pipeline_src` — alterações são imediatas, sem rebuild

---

## 📝 Documentação Adicional

- [Airflow DAGs](./airflow/dags/)
- [Terraform Setup](./docs/terraform.md)
- [Huawei Cloud Setup](./docs/huawei-setup.md)
- [Ansible Automation](./ansible/README.md)
- [Docker Environment](./pipeline/DOCKER.md)
- [Pipeline README](./pipeline/README.md)
- [CSV/GeoJSON Guide](./pipeline/CSV_GEOJSON_GUIDE.md)
- [Diagramas de Arquitetura](./DIAGRAMAS.md)
- [Notebook Interativo](./notebooks/esteira_geo.ipynb)
- [Notebook Utilitários](./notebooks/utilitarios.ipynb)
