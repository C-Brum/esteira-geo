# Esteira Geo — Workspace

Workspace completo para uma **esteira de processamento de dados geográficos** usando arquitetura **Medallion** (Bronze → Silver → Gold).

## 📋 Estrutura do Projeto

```
esteira-geo/
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
│   │   ├── bronze_loader.py
│   │   ├── silver_processor.py
│   │   ├── gold_processor.py
│   │   ├── postgis_loader.py
│   │   └── silver/
│   │       └── csv_geojson_converter.py
│   ├── watchers/
│   │   └── watch_bronze.py
│   ├── web/
│   │   ├── app.py         # Flask (multi-caso-de-uso)
│   │   └── templates/index.html
│   ├── main.py            # Orquestrador principal
│   ├── config.py          # Configuração (USE_CASE, paths, credenciais)
│   └── requirements.txt
├── notebooks/             # Notebooks Jupyter interativos
│   └── esteira_geo.ipynb  # Fluxo completo Bronze → Silver → Gold → PostGIS
├── data/
│   └── bronze/
│       └── automatizado/          # Área monitorada pelo watcher
│           ├── enchentes_poa/     # Arquivos CSV/GeoJSON para este use_case
│           ├── enchentes_mg/
│           └── enchentes_rj/
├── docs/                  # Documentação
│   ├── terraform.md
│   └── huawei-setup.md
└── README.md
```

## 🏗️ Arquitetura

A esteira segue o padrão **Medallion**:

- **Bronze**: Armazenamento bruto de dados (OBS/S3). Área `automatizado/<use_case>/` é monitorada pelo watcher; o restante do bucket é ignorado
- **Silver**: Dados normalizados e validados (OBS/S3) — acumulativo por `citizen_id`/`area_id`
- **Gold**: Resultado do batimento geoespacial (OBS/S3 + PostGIS) — única fonte de verdade do PostGIS

**Componentes de Infraestrutura**:
- 2 VMs: `processing` (Python) + `presentation` (web, acesso internet)
- RDS PostgreSQL com PostGIS (compartilhado com bucket gold)
- 3 buckets OBS/S3 (bronze, silver, gold)

---

## � Desenvolvimento Local com Docker

**Opção recomendada para desenvolvimento e testes locais sem credenciais de nuvem.**

O ambiente Docker simula toda a infraestrutura localmente (PostgreSQL + PostGIS + MinIO para S3 + Flask + Pipeline ETL).

### Quick Start Docker

```bash
# 1. Iniciar todo o ambiente
docker compose up -d

# 2. Aguarde ~30 segundos para tudo ficar saudável
docker compose ps

# 3. Executar pipeline ETL
docker compose exec pipeline python /app/main.py

# 4. Acessar serviços
# Dashboard Flask:  http://localhost:5000
# JupyterLab:       http://localhost:8888/lab?token=esteira
# MinIO Console:    http://localhost:9001 (user: minioadmin)
# PostgreSQL:       localhost:5432 (user: esteira_user)
```

### JupyterLab — Processamento Interativo

O ambiente inclui um container JupyterLab com acesso direto a todos os módulos da esteira, MinIO e PostGIS. Ideal para exploração de dados, depuração e experimentos sem alterar o pipeline principal.

```bash
# Iniciar apenas o Jupyter (se o ambiente já estiver rodando)
docker compose up -d jupyter

# Acessar
# http://localhost:8888/lab?token=esteira
```

O notebook `notebooks/esteira_geo.ipynb` replica o fluxo completo do watcher de forma interativa:

| Célula | O que faz |
|--------|-----------|
| 0 — Configuração | Define `USE_CASE` e exibe conexões |
| 1 — Bronze | Lista arquivos no bucket S3/MinIO |
| 2 — Silver | Executa `process_silver()`, exibe DataFrames normalizados |
| 3 — Gold | Executa `process_gold()`, mostra resultado do spatial join |
| 4 — PostGIS | Sincroniza via `load_to_postgis()` |
| 5 — Consultas SQL | Queries direto no PostGIS |
| 6 — Mapa | Abre o mapa Leaflet do Flask via IFrame |
| 7 — Ingestão manual | Upload de arquivo para o bronze + reprocessamento |

Para trocar o use_case, altere `os.environ['USE_CASE']` na célula 0 e reexecute:

```python
os.environ['USE_CASE'] = 'enchentes_rj'  # ou enchentes_mg, enchentes_poa
```

Os notebooks são persistidos em `./notebooks/` no host — alterações sobrevivem a restarts do container.

### Ingestão de Dados Externos

O watcher monitora exclusivamente o prefixo `automatizado/<use_case>/` dentro do bucket bronze. Arquivos depositados em qualquer outro caminho do bucket são ignorados.

```
bronze/
└── automatizado/
    ├── enchentes_poa/      ← watcher detecta e dispara USE_CASE=enchentes_poa
    │   ├── arquivo.csv
    │   └── processados/    ← movido automaticamente após processar
    ├── enchentes_mg/
    └── enchentes_rj/
```

```bash
# Copiar arquivo para a área automatizada
cp meus_cidadaos.csv data/bronze/automatizado/enchentes_poa/

# O watcher detecta em até 10s e dispara o pipeline automaticamente
# Ou execute manualmente para um use_case específico:
docker compose exec -e USE_CASE=enchentes_poa pipeline python /app/main.py
```

**Formatos suportados:**
- CSV com colunas `latitude` e `longitude`
- GeoJSON (pontos ou polígonos)

**Normalização automática:** `registered_date` → `registration_date` | `citizen_id` aceita inteiros ou strings (`C003`, `C004`...) | `document_number` sempre lido como string

### Windows PowerShell Helper

Use o script helper para gerenciar Docker mais facilmente:

```bash
# Ver status dos containers
.\docker.ps1 status

# Executar pipeline
.\docker.ps1 pipeline

# Acessar shell do pipeline
.\docker.ps1 shell

# Ver logs
.\docker.ps1 logs pipeline

# Acessar banco de dados
.\docker.ps1 db

# Abrir MinIO
.\docker.ps1 minio

# Parar ambiente
.\docker.ps1 down

# Mais comandos
.\docker.ps1 help
```

### Linux/macOS - Bash Scripts & Makefile

**Opção 1: Scripts bash** (recomendado)

```bash
# 1. Fazer scripts executáveis
chmod +x setup.sh docker.sh debug.sh

# 2. Setup inicial (primeira vez)
./setup.sh

# 3. Iniciar
./docker.sh up

# 4. Pipeline
./docker.sh pipeline

# 5. Status
./docker.sh status
```

**Opção 2: Makefile** (padrão Linux)

```bash
make setup   # Setup (primeira vez)
make up      # Iniciar
make pipeline # Executar pipeline
make test    # Testes
make logs-pipeline
make db      # Banco de dados
make down    # Parar
```

**Para mais detalhes**: Veja [SCRIPTS_BASH.md](./SCRIPTS_BASH.md) e [pipeline/DOCKER.md](./pipeline/DOCKER.md)

---

## 🚀 Como Configurar e Deploy em Nuvem

### Pré-requisitos

1. **Terraform** >= 1.0
   ```bash
   # Windows (via Chocolatey)
   choco install terraform
   
   # Ou download direto: https://www.terraform.io/downloads
   terraform --version
   ```

2. **Credenciais da Nuvem**
   - **AWS**: Configure `~/.aws/credentials` ou exporte `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`
   - **Huawei Cloud**: Exporte `HW_ACCESS_KEY` e `HW_SECRET_KEY`

3. **SSH Key Pair** (para acesso às VMs)
   ```bash
   # Gere uma chave SSH se não tiver
   ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\id_rsa
   ```

### Passo 1: Escolher Nuvem e Ambiente

Defina qual cloud usar editando o arquivo `terraform.tfvars` ou use um dos presets:

**Para Huawei Cloud (São Paulo)**:
```bash
cd terraform
# Copie o arquivo de exemplo
cp envs/huawei-sp.tfvars terraform.tfvars
```

**Para AWS**:
```bash
cd terraform
cp envs/aws.tfvars terraform.tfvars
```

### Passo 2: Configurar Credenciais

**AWS** - Exporte credenciais:
```bash
$env:AWS_ACCESS_KEY_ID = "sua-access-key"
$env:AWS_SECRET_ACCESS_KEY = "sua-secret-key"
```

**Huawei Cloud** - Exporte credenciais:
```bash
$env:HW_ACCESS_KEY = "seu-access-key"
$env:HW_SECRET_KEY = "seu-secret-key"
```

### Passo 3: Configurar SSH Public Key

Adicione a public key ao arquivo de variáveis:

```bash
# Obtenha o caminho da public key
$sshKey = Get-Content $env:USERPROFILE\.ssh\id_rsa.pub

# Adicione ao terraform.tfvars
echo "ssh_public_key = `"$sshKey`"" >> terraform.tfvars
```

### Passo 4: Inicializar Terraform

```bash
cd terraform
terraform init
```

### Passo 5: Planejar Deployment

Revise os recursos que serão criados:

```bash
terraform plan -out=tfplan
```

### Passo 6: Aplicar Infraestrutura

```bash
terraform apply tfplan
```

Terraform exibirá os **outputs**:
- `s3_or_obs_buckets`: Nomes dos buckets (bronze, silver, gold)
- `processing_public_ip`: IP da VM de processamento
- `presentation_public_ip`: IP da VM de apresentação (acesso internet)
- `rds_endpoint`: Endpoint do PostgreSQL (PostGIS)

### Passo 7: Habilitar PostGIS no RDS

Após o deployment, habilite a extensão PostGIS:

```bash
# Obtenha o endpoint do RDS (do output anterior)
$rdsEndpoint = terraform output -raw rds_endpoint

# Conecte via psql (certifique-se que psql está instalado)
# Download: https://www.postgresql.org/download/

psql -h $rdsEndpoint -U postgres -d esteira-geo-huawei-sp
# Digite a senha (default: postgrespw)

# Dentro do psql:
CREATE EXTENSION postgis;
\q
```

### Passo 8: Acessar as VMs

```bash
# SSH para VM de processamento
$processingIP = terraform output -raw processing_public_ip
ssh -i $env:USERPROFILE\.ssh\id_rsa ec2-user@$processingIP

# SSH para VM de apresentação
$presentationIP = terraform output -raw presentation_public_ip
ssh -i $env:USERPROFILE\.ssh\id_rsa ec2-user@$presentationIP
```

---

## 🤖 Passo 9: Automatizar Configuração com Ansible

Após provisionar a infraestrutura, use **Ansible** para configurar automaticamente as VMs.

### 9.1 Instalar Ansible

```bash
pip install ansible
ansible --version
```

### 9.2 Configurar Inventário

Edite `ansible/inventory.ini` com os IPs das VMs:

```bash
# Obter IPs do Terraform
cd terraform
terraform output -json

# Copie os IPs e atualize inventory.ini
cd ../ansible
```

Exemplo `inventory.ini`:
```ini
[processing]
processing-vm ansible_host=10.0.1.10 ansible_user=ec2-user

[presentation]
presentation-vm ansible_host=10.0.1.11 ansible_user=ec2-user

[all:vars]
aws_s3_bronze_bucket=esteira-geo-bronze-xxxxx
aws_s3_silver_bucket=esteira-geo-silver-xxxxx
aws_s3_gold_bucket=esteira-geo-gold-xxxxx
rds_host=esteira-geo-postgres.xxxxx.rds.amazonaws.com
rds_password=postgrespw
```

### 9.3 Executar Playbooks

**VM de Processamento** (instala Python geoespacial, configura pipeline):
```bash
cd ansible
ansible-playbook -i inventory.ini processing.yml -v
```

**VM de Apresentação** (instala Flask, Nginx, Gunicorn):
```bash
ansible-playbook -i inventory.ini presentation.yml -v
```

**Ambas ao mesmo tempo**:
```bash
ansible-playbook -i inventory.ini processing.yml presentation.yml
```

### 9.4 Verificar Configuração

```bash
# Testar health check da apresentação
$presentationIP = terraform output -raw presentation_public_ip
curl "http://$presentationIP/health"

# Acessar dashboard Flask
# Abra navegador: http://<PRESENTATION_IP>/
```

**Detalhes**: Veja [ansible/README.md](./ansible/README.md) para guia completo.

---

## � Passo 10: Executar Pipeline de Processamento

O pipeline implementa um **caso de uso completo de batimento geográfico**: identifica cidadãos atingidos por enchentes em Porto Alegre através de spatial join.

### 10.1 Estrutura do Pipeline (Medallion)

```
Bronze → Silver → Gold → PostGIS → Flask
```

**Bronze**: Dados brutos (3 áreas de enchente + 100 cidadãos)
**Silver**: Dados normalizados e validados  
**Gold**: Resultado do batimento geoespacial — afetados + não afetados, sem duplicatas por citizen_id
**PostGIS**: Armazenamento em RDS com índices espaciais
**Flask**: APIs e dashboard

### 10.2 Configurar e Executar

```bash
# Setup local (desenvolvimento)
cd pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configurar variáveis de ambiente (.env)
$env:RDS_HOST = "<RDS_ENDPOINT>"
$env:RDS_PASSWORD = "postgrespw"
$env:AWS_S3_BRONZE_BUCKET = "esteira-geo-bronze-xxxxx"
$env:USE_CASE = "enchentes_poa"

# Executar pipeline completo
python main.py

# Resultado esperado (com dados de exemplo incluídos):
# ✓ PIPELINE CONCLUÍDO COM SUCESSO!
#   Cidadãos Atingidos: 114
#   Cidadãos Não Atingidos: 75
#   Total Avaliado: 189
#   Percentual Atingido: 60.3%
```

### 10.3 Testes do Pipeline

Veja [pipeline/TESTES_CSV_GEOJSON.md](./pipeline/TESTES_CSV_GEOJSON.md) para suite completa de testes.

Arquivos de dados de teste disponíveis em `data/bronze/automatizado/enchentes_poa/`:

| Arquivo | Tipo | Cidadãos |
|---------|------|----------|
| `citizens_sample.csv` | CSV | C003–C052 (50) |
| `novos_cidadaos_poa.csv` | CSV | C053–C067 (15) |
| `novos_pontos_a.csv` | CSV | C068–C073 (6) |
| `novos_pontos_b.geojson` | GeoJSON | C074–C079 (6) |
| `novos_pontos_c.csv` | CSV | C080–C085 (6) |
| `novos_pontos_d.geojson` | GeoJSON | C086–C091 (6) |

### 10.4 Verificar Dados no PostGIS

Tabelas prefixadas pelo caso de uso (`enchentes_poa_citizens`, `enchentes_poa_flooding_areas`):

```bash
# Conectar ao banco
psql -h <RDS_ENDPOINT> -U postgres -d esteira-geo

# Dentro do psql:
SELECT COUNT(*) as total_citizens FROM enchentes_poa_citizens;
SELECT COUNT(*) as affected FROM enchentes_poa_citizens WHERE affected_by_flooding = TRUE;

# Ver cidadãos afetados
SELECT citizen_id, name, ST_AsText(geometry) FROM enchentes_poa_citizens
WHERE affected_by_flooding = TRUE LIMIT 5;
```

### 10.5 Visualizar no Flask

```bash
curl http://<PRESENTATION_IP>/health
curl http://<PRESENTATION_IP>/api/stats
curl http://<PRESENTATION_IP>/api/stats?use_case=enchentes_poa
curl http://<PRESENTATION_IP>/api/use_cases   # lista casos de uso disponíveis
curl http://<PRESENTATION_IP>/api/geojson

# Abrir dashboard
# http://<PRESENTATION_IP>/
```

**Detalhes**: Veja [pipeline/README.md](./pipeline/README.md) para documentação completa.

---

## �📦 Próximos Passos

### 1. Customizar Aplicação Flask

Edite `ansible/roles/presentation/files/app.py` para adicionar endpoints de análise geoespacial customizados:
- Integração com dados do bucket gold
- Queries SQL/PostGIS específicas
- Visualização de mapas (ex: folium, leaflet)

### 2. Implementar Pipeline de Processamento

Desenvolva scripts em `pipeline/main.py` para:
- Ler dados do bucket bronze
- Processar com geopandas/rasterio
- Validar e escrever em silver/gold
- Carregar geometrias para PostGIS

### 3. Testar Pipeline Localmente

```bash
cd pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Teste antes de confiar em cron na VM
python main.py
```

### 4. Deploy Atualizado na VM

Atualize o código na VM sem re-rodar Ansible:

```bash
# SSH para VM de processamento
ssh -i ~/.ssh/id_rsa ec2-user@$processingIP

# Atualize código
cd ~/esteira-geo
git pull origin main  # ou copie arquivos manualmente
```

### 5. Monitoramento e Logs

**VM de Processamento**:
```bash
# Ver logs do pipeline
tail -f ~/esteira-geo/logs/pipeline.log

# Verificar execução do cron
sudo tail -f /var/log/cron
```

**VM de Apresentação**:
```bash
# Ver logs Flask/Gunicorn
sudo journalctl -u esteira-geo -f
# ou via Supervisor:
sudo supervisorctl tail esteira_geo_flask stderr
```

### 6. Configurar Banco de Dados

Criar tabelas de geometrias no PostGIS (após conexão funcionar):

```bash
psql -h $rdsEndpoint -U postgres -d esteira-geo-huawei-sp

-- Dentro do psql:
CREATE TABLE geometries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    geometry GEOMETRY(MULTIPOLYGON, 4326),
    properties JSONB
);

CREATE INDEX idx_geometries_geom ON geometries USING GIST(geometry);
\q
```

### 7. Integração Contínua

- Configure GitHub Actions / GitLab CI para atualizar playbooks
- Implemente testes de infraestrutura (terratest, kitchen)
- Versione dados com DVC ou Delta Lake

---

## 📝 Documentação Adicional

- [Terraform Setup](./docs/terraform.md)
- [Huawei Cloud Setup](./docs/huawei-setup.md)
- [Ansible Automation](./ansible/README.md)
- [Docker Environment](./pipeline/DOCKER.md)
- [CSV/GeoJSON Guide](./pipeline/CSV_GEOJSON_GUIDE.md)
- [Testes e Validações](./pipeline/TESTES_CSV_GEOJSON.md)
- [Notebook Interativo](./notebooks/esteira_geo.ipynb)

---

## 🔧 Troubleshooting

**Erro: `Provider not found`**
```bash
terraform init -upgrade
```

**Erro: `Authentication failed`**
- Verifique credenciais exportadas: `echo $env:AWS_ACCESS_KEY_ID`
- Confirme permissões na conta da nuvem

**RDS não acessível**
- Verifique security group permite porta 5432
- Confirme IP da VM está autorizado

**PostGIS não atualiza após pipeline rodar (Docker)**
- Verifique se `pipeline-watcher` tem `RDS_HOST: postgis` no `docker-compose.yml`
- Sem essa variável o loader tenta `localhost` e falha silenciosamente

**Watcher não detecta arquivo já existente**
```bash
touch data/bronze/automatizado/enchentes_poa/meu_arquivo.csv
```

**Arquivo fora de `automatizado/` não é processado**
- O watcher ignora qualquer key que não comece com `automatizado/<use_case>/`
- Mova o arquivo para o caminho correto: `bronze/automatizado/<use_case>/arquivo.csv`

**Jupyter — módulos da esteira não encontrados**
- Confirme que o container foi buildado após alterações: `docker compose build jupyter`
- O `sys.path` do notebook aponta para `/app` onde os módulos são copiados no build

**Jupyter — alterações no código do pipeline não refletem no notebook**
```bash
# Rebuild necessário para copiar código atualizado para o container
docker compose build jupyter && docker compose up -d jupyter
```

---

## 📞 Suporte

Para dúvidas ou adaptações:
- Leia documentação em `docs/`
- Consulte outputs Terraform: `terraform output`
- Valide estado: `terraform show`
