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
│   ├── main.py            # Script exemplo
│   └── requirements.txt
├── docs/                  # Documentação
│   ├── terraform.md
│   └── huawei-setup.md
└── README.md
```

## 🏗️ Arquitetura

A esteira segue o padrão **Medallion**:

- **Bronze**: Armazenamento bruto de dados (OBS/S3)
- **Silver**: Dados processados e validados (OBS/S3)
- **Gold**: Dados transformados prontos para análise (OBS/S3 + PostGIS)

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
docker-compose up -d

# 2. Aguarde ~30 segundos para tudo ficar saudável
docker-compose ps

# 3. Executar pipeline ETL
docker-compose exec pipeline python /app/pipeline/main.py

# 4. Acessar serviços
# Dashboard Flask: http://localhost:5000
# MinIO Console: http://localhost:9001 (user: minioadmin)
# PostgreSQL: localhost:5432 (user: esteira_user)
```

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
**Gold**: Resultado do batimento geoespacial (60 afetados + 40 não afetados)
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

# Executar pipeline completo
python main.py

# Resultado esperado:
# ✓ PIPELINE CONCLUÍDO COM SUCESSO!
#   Cidadãos Atingidos: 60
#   Cidadãos Não Atingidos: 40
#   Total Avaliado: 100
#   Percentual Atingido: 60.0%
```

### 10.3 Testes do Pipeline

Arquivo `pipeline/testes_e_validacoes.txt` contém 25+ testes:

```bash
# Testes unitários (Bronze, Silver, Gold, PostGIS)
python etl/bronze_loader.py
python etl/silver_processor.py
python etl/gold_processor.py
python etl/postgis_loader.py

# Validações de dados
python -c "
import geopandas as gpd
affected = gpd.read_parquet('pipeline/data/affected_citizens.parquet')
print(f'Cidadãos afetados: {len(affected)}')
print(affected[['citizen_id', 'name', 'area_name']].head())
"
```

### 10.4 Verificar Dados no PostGIS

```bash
# Conectar ao banco e executar queries
psql -h <RDS_ENDPOINT> -U postgres -d esteira-geo

# Dentro do psql:
SELECT COUNT(*) as total_citizens FROM citizens;
SELECT COUNT(*) as affected FROM citizens WHERE affected_by_flooding = TRUE;

# Ver cidadãos afetados
SELECT citizen_id, name, ST_AsText(geometry) FROM citizens 
WHERE affected_by_flooding = TRUE LIMIT 5;
```

### 10.5 Visualizar no Flask

```bash
# Acessar endpoints no navegador
curl http://<PRESENTATION_IP>/api/geometries
curl http://<PRESENTATION_IP>/api/stats

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

---

## 🔧 Troubleshooting

**Erro: `Provider not found`**
```bash
terraform init -upgrade
```

**Erro: `Authentication failed`**
- Verifique credenciais exportadas: `echo $env:AWS_ACCESS_KEY_ID`
- Confirme permissões na conta da nuvem

**RDS não accessible**
- Verifique security group permite porta 5432
- Confirme IP da VM está autorizado

---

## 📞 Suporte

Para dúvidas ou adaptações:
- Leia documentação em `docs/`
- Consulte outputs Terraform: `terraform output`
- Valide estado: `terraform show`
