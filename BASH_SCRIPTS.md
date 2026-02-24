# Bash Scripts & Automation

Tudo que você precisa para desenvolvimento local com **Docker em Linux/macOS**.

## 📜 Scripts Criados

| Script | SO | Função | Permissão |
|--------|----|---------|----|
| `docker.sh` | Linux/macOS | Gerenciar containers Docker | `chmod +x docker.sh` |
| `setup.sh` | Linux/macOS | Setup inicial (instala dependências) | `chmod +x setup.sh` |
| `debug.sh` | Linux/macOS | Testes e diagnósticos | `chmod +x debug.sh` |
| `Makefile` | Linux (padrão) | Interface make (sem permissão necessária) | - |
| `docker.ps1` | Windows | Gerenciar containers (PowerShell) | - |

---

## 🚀 Como Começar em Linux/macOS

### 1️⃣ Primeira Vez - Setup Completo

```bash
# Ir para projeto
cd esteira-geo

# Tornar scripts executáveis
chmod +x setup.sh docker.sh debug.sh

# Executar setup (instala Docker, Python, etc)
./setup.sh

# Escolher opção:
# 1 = Full Setup (Docker + Python + Git)  [recomendado]
# 2 = Docker Only
```

### 2️⃣ Iniciar Ambiente

```bash
# Opção A: Com script
./docker.sh up

# Opção B: Com Makefile
make up

# Opção C: Docker direto
docker-compose up -d
```

### 3️⃣ Rodar Pipeline

```bash
# Opção A: Script
./docker.sh pipeline

# Opção B: Makefile
make pipeline

# Opção C: Docker direto
docker-compose exec pipeline python /app/pipeline/main.py
```

### 4️⃣ Verificar Tudo

```bash
# Opção A: Script
./debug.sh status

# Opção B: Makefile
make verify

# Opção C: Docker direto
docker-compose ps
```

### 5️⃣ Parar

```bash
# Opção A: Script
./docker.sh down

# Opção B: Makefile
make down

# Opção C: Docker direto
docker-compose down
```

---

## 📖 Comandos Detalhados

### `docker.sh` - Gerenciador Principal

```bash
./docker.sh up              # Iniciar
./docker.sh down            # Parar
./docker.sh status          # Ver status
./docker.sh logs [serviço]  # Ver logs (postgis, minio, pipeline, web)
./docker.sh pipeline        # Executar pipeline
./docker.sh shell           # Acessar bash do container
./docker.sh test            # Rodar testes
./docker.sh db              # Conectar ao banco (psql)
./docker.sh minio           # Abrir MinIO UI no navegador
./docker.sh clean           # Remover containers + volumes
./docker.sh help            # Ajuda
```

### `setup.sh` - Setup Inicial

```bash
./setup.sh

# Faz automaticamente:
# 1. Detecta SO (Linux/macOS)
# 2. Instala Docker (se não tiver)
# 3. Instala Docker Compose
# 4. Instala Git
# 5. Cria Python venv
# 6. Instala dependências Python
# 7. Cria .env file
# 8. Cria diretórios de dados
# 9. Torna scripts executáveis
```

### `debug.sh` - Debugging & Testes

```bash
./debug.sh docker           # Testar Docker setup
./debug.sh containers       # Status dos containers
./debug.sh postgres         # Testar conexão PostgreSQL
./debug.sh minio            # Testar MinIO
./debug.sh flask            # Testar Flask app
./debug.sh validate         # Validar dados (Bronze/Silver/Gold)
./debug.sh test-bronze      # Rodar teste Bronze
./debug.sh test-silver      # Rodar teste Silver
./debug.sh test-gold        # Rodar teste Gold
./debug.sh test-postgis     # Rodar teste PostGIS
./debug.sh test-all         # Rodar todos os testes
./debug.sh status           # Verificação completa
./debug.sh report           # Gerar report diagnóstico
./debug.sh help             # Ajuda
```

### `Makefile` - Interface Make (Padrão Linux)

```bash
make help              # Mostrar ajuda
make setup             # Setup inicial
make up                # Iniciar
make down              # Parar
make status            # Status
make build             # Build imagens
make rebuild           # Rebuild imagens (sem cache)
make logs              # Ver todos os logs
make logs-pipeline     # Ver logs do pipeline
make logs-postgis      # Ver logs do PostgreSQL
make logs-web          # Ver logs do Flask
make pipeline          # Rodar pipeline
make bronze            # Rodar Bronze layer
make silver            # Rodar Silver layer
make gold              # Rodar Gold layer (spatial join)
make postgis           # Rodar PostGIS loader
make test              # Rodar todos os testes
make shell             # Acessar bash
make db                # Conectar ao banco
make minio             # Abrir MinIO
make clean             # Limpar containers
make prune             # Limpar recursos Docker
make verify            # Verificar setup
```

---

## 💡 Fluxo de Desenvolvimento Típico

```bash
# 1. Primeira vez
./setup.sh

# 2. Iniciar dia
./docker.sh up
# OU
make up

# 3. Testar ambiente
./debug.sh status
# OU
make verify

# 4. Rodar pipeline completo
./docker.sh pipeline
# OU
make pipeline

# 5. Testar camadas específicas
./debug.sh test-bronze      # Dados brutos
./debug.sh test-silver      # Normalização
./debug.sh test-gold        # Spatial join
./debug.sh test-postgis     # Banco de dados

# 6. Ver logs
./docker.sh logs pipeline
# OU
make logs-pipeline

# 7. Acessar banco de dados
./docker.sh db
# OU
make db

# 8. Parar
./docker.sh down
# OU
make down
```

---

## 🔍 Troubleshooting

### Script não é executável

```bash
# Tentar novamente
chmod +x docker.sh debug.sh setup.sh

# Ou usar Makefile (não precisa de permissão)
make status
```

### Sem permissão Docker

```bash
# Adicionar user ao grupo docker
sudo usermod -aG docker $USER

# Ativar (escolha uma):
newgrp docker              # Opção 1
# OU fazer logout/login    # Opção 2
```

### PostgreSQL não sobe

```bash
# Testar conexão
./debug.sh postgres

# Ver logs detalhados
./docker.sh logs postgis

# Reiniciar
./docker.sh down
./docker.sh up
```

### Sem espaço em disco

```bash
# Limpar tudo
./docker.sh clean
# OU
make clean

# Limpar recursos Docker extras
make prune
```

### Verificar tudo está OK

```bash
# Diagnostic completo
./debug.sh status

# Ou com Makefile
make verify

# Gerar report
./debug.sh report
```

---

## 🎯 Qual Script Usar?

### Para Desenvolvimento Diário

```bash
# Opção 1: Makefile (mais rápido, padrão Linux)
make up
make pipeline
make down

# Opção 2: docker.sh (mais colorido, detalhado)
./docker.sh up
./docker.sh pipeline
./docker.sh down
```

### Para Debugging

```bash
./debug.sh status       # Verificação rápida
./debug.sh report       # Report completo
./debug.sh test-all     # Rodar testes
```

### Para Setup

```bash
./setup.sh    # Primeira vez (instala dependências)
```

---

## 📚 Referências Rápidas

- **Setup**: [setup.sh](./setup.sh)
- **Docker**: [docker.sh](./docker.sh)
- **Debug**: [debug.sh](./debug.sh)
- **Makefile**: [Makefile](./Makefile)
- **Docs**: [SCRIPTS_BASH.md](./SCRIPTS_BASH.md)
- **Docker Completo**: [pipeline/DOCKER.md](./pipeline/DOCKER.md)
- **Setup Docker**: [DOCKER_SETUP.md](./DOCKER_SETUP.md)

---

## ✅ Checklist Inicial

```bash
# 1. Scripts executáveis
chmod +x setup.sh docker.sh debug.sh

# 2. Setup (primeira vez)
./setup.sh

# 3. Verificar Docker
./debug.sh docker

# 4. Iniciar
./docker.sh up

# 5. Testar
./debug.sh status

# 6. Pipeline
./docker.sh pipeline

# 7. Dashboard
# http://localhost:5000

# 8. MinIO
# http://localhost:9001
```

Tudo pronto! 🚀
