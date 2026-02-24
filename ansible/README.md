# Ansible Automation para Esteira Geo

## 📋 Estrutura

```
ansible/
├── ansible.cfg                 # Configuração do Ansible
├── inventory.ini               # Hosts (VMs) a configurar
├── processing.yml              # Playbook para VM de processamento
├── presentation.yml            # Playbook para VM de apresentação
├── group_vars/
│   ├── all.yml                 # Variáveis globais
│   ├── processing.yml          # Variáveis do grupo processing
│   └── presentation.yml        # Variáveis do grupo presentation
└── roles/
    ├── common/                 # Tarefas comuns (update system, deps)
    ├── processing/             # Role para VM de processamento
    └── presentation/           # Role para VM de apresentação (Flask)
```

## 🚀 Como Usar

### 1. Pré-requisitos

Instale Ansible em seu workstation:

```bash
# Windows - via WSL ou Python
pip install ansible

# Ou via Chocolatey
choco install ansible
```

Verifique:
```bash
ansible --version
```

### 2. Configure o Inventory

Edite `inventory.ini` com os IPs das VMs provisionadas pelo Terraform:

```bash
# Obter IPs do Terraform
cd ../terraform
terraform output -json
```

Atualize `inventory.ini`:
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

### 3. Configurar SSH

Certifique-se que pode acessar as VMs via SSH:

```bash
# Teste conexão
ssh -i ~/.ssh/id_rsa ec2-user@<PROCESSING_IP>

# Se houver problemas, ajuste permissões
Get-Item $env:USERPROFILE\.ssh\id_rsa | Set-ItemProperty -Name 'Attributes' -Value 'Normal'
icacls $env:USERPROFILE\.ssh\id_rsa /inheritance:r /grant:r "$env:USERNAME:(F)"
```

### 4. Executar Playbooks

**Sintaxe de teste** (verificar com --check):
```bash
cd ansible
ansible-playbook -i inventory.ini processing.yml --check
ansible-playbook -i inventory.ini presentation.yml --check
```

**Aplicar configuração** (VM de processamento):
```bash
ansible-playbook -i inventory.ini processing.yml -v
```

**Aplicar configuração** (VM de apresentação):
```bash
ansible-playbook -i inventory.ini presentation.yml -v
```

**Ambas as VMs ao mesmo tempo**:
```bash
ansible-playbook -i inventory.ini processing.yml presentation.yml
```

### 5. Verificar Configuração

Após execução bem-sucedida, teste as VMs:

#### VM de Processamento

```bash
# SSH para VM
ssh -i ~/.ssh/id_rsa ec2-user@<PROCESSING_IP>

# Verifique ambiente virtual
su - esteira
source ~/esteira-geo/venv/bin/activate
python3 -c "import geopandas; print(geopandas.__version__)"

# Verifique configurações
cat ~/esteira-geo/.env
```

#### VM de Apresentação

```bash
# SSH para VM
ssh -i ~/.ssh/id_rsa ec2-user@<PRESENTATION_IP>

# Verifique status Flask/Gunicorn
sudo systemctl status esteira-geo
# ou via Supervisor:
sudo supervisorctl status esteira_geo_flask

# Teste endpoint
curl http://localhost/health
curl http://localhost/api/db-status

# Verifique logs
tail -f /home/webapp/esteira-geo/logs/gunicorn-access.log
tail -f /home/webapp/esteira-geo/logs/gunicorn-error.log
```

---

## 📝 Detalhes das Roles

### Role: `common`

Tarefas executadas em **todas as VMs**:
- Update de pacotes do sistema
- Instalação de Python 3.9
- Ferramentas básicas (git, wget, curl, htop, jq)

### Role: `processing`

Configuração da **VM de Processamento**:
- Cria usuário `esteira`
- Instala dependências geoespaciais (GDAL, GEOS, PROJ)
- Cria virtual environment Python
- Instala pacotes: geopandas, rasterio, fiona, boto3, etc.
- Cria arquivo `.env` com credenciais (buckets, RDS)
- Configura cron job para executar pipeline (padrão: 2:00 AM diariamente)

**Arquivo de script**: `run_pipeline.sh`
- Ativa virtual environment
- Carrega variáveis de ambiente
- Executa `main.py`

### Role: `presentation`

Configuração da **VM de Apresentação** (Flask):
- Cria usuário `webapp`
- Instala Flask, Gunicorn, Nginx, Supervisor
- Cria virtual environment Python
- Instala dependências: flask, psycopg2, boto3, geopandas, etc.
- Configura **Nginx** como reverse proxy na porta 80
- Configura **Supervisor** para gerenciar Gunicorn
- Copia aplicação Flask de exemplo
- Cria arquivo `.env` com credenciais

**Aplicação Flask** (`app.py`):
- Endpoints:
  - `GET /` → Home page
  - `GET /health` → Health check
  - `GET /api/db-status` → Status de conexão RDS
  - `GET /api/buckets` → Info de buckets de dados
  - `GET /api/geometries` → Lê geometrias do PostGIS
  - `GET /api/stats` → Estatísticas de dados

---

## 🔧 Customização

### Variar Schedule do Pipeline

Edite `group_vars/processing.yml`:
```yaml
pipeline_schedule: "0 3 * * *"  # Executa às 3:00 AM
# Formato: "minute hour day month weekday"
# Exemplos:
# - 0 2 * * *  = 2:00 AM diariamente
# - 0 */6 * * * = A cada 6 horas
# - 0 0 * * 0  = Domingo à meia-noite
```

### Ajustar Número de Workers Gunicorn

Edite `group_vars/presentation.yml`:
```yaml
gunicorn_workers: 8      # Mais workers = mais concorrência
gunicorn_threads: 2      # Threads por worker
```

### Customizar Aplicação Flask

Modifique `roles/presentation/files/app.py` conforme seu caso de uso.

---

## 🐛 Troubleshooting

**Erro: "Connection refused"**
```bash
# Verifique se Ansible consegue alcançar as VMs
ansible all -i inventory.ini -m ping
```

**Erro: "Permission denied (publickey)"**
```bash
# Verifique a chave SSH
ls -la ~/.ssh/id_rsa
# Ou ajuste em inventory.ini:
ansible_ssh_private_key_file=/path/to/key
```

**Erro: "Module not found"**
```bash
# Force install de dependências Python
ansible-playbook -i inventory.ini presentation.yml -t pip -v
```

**Nginx não inicia**
```bash
# SSH para VM e verifique logs
sudo tail -f /var/log/nginx/error.log
```

**Flask não responde**
```bash
# Verifique Gunicorn
sudo journalctl -u esteira-geo -f
# ou via Supervisor
sudo supervisorctl tail esteira_geo_flask stderr
```

---

## 📞 Próximos Passos

1. **Customizar Flask app** para suas análises geoespaciais
2. **Testar pipeline** de processamento manualmente antes de confiar em cron
3. **Configurar PostGIS** com suas tabelas de geometrias
4. **Implementar CI/CD** para atualizar playbooks e aplicação
5. **Adicionar monitoramento** (CloudWatch, Prometheus, ELK)
