# Scripts Bash - Documentação

Scripts para facilitar desenvolvimento em **Linux/macOS** com Docker.

## 📋 Scripts Disponíveis

### 1. `docker.sh` - Gerenciador Principal

Script para iniciar, parar e gerenciar containers Docker.

```bash
# Iniciar
./docker.sh up

# Ver status
./docker.sh status

# Executar pipeline
./docker.sh pipeline

# Ver logs
./docker.sh logs pipeline
./docker.sh logs postgis
./docker.sh logs web

# Acessar shell
./docker.sh shell

# Banco de dados
./docker.sh db

# MinIO UI
./docker.sh minio

# Parar
./docker.sh down

# Limpar
./docker.sh clean
```

**Permissões**: Certifique-se que o script é executável:
```bash
chmod +x docker.sh
```

---

### 2. `setup.sh` - Setup Inicial

Script de configuração que instala dependências e prepara ambiente.

```bash
# Executar setup
./setup.sh

# Escolher modo:
# 1 = Full Setup (Docker + Python + Git)
# 2 = Docker Only
```

**O que faz:**
- ✅ Detecta SO (Linux/macOS)
- ✅ Instala Docker (se não tiver)
- ✅ Instala Docker Compose
- ✅ Instala Git
- ✅ Cria Python venv
- ✅ Instala dependências Python
- ✅ Cria .env file
- ✅ Cria diretórios de dados
- ✅ Torna scripts executáveis

**Permissões**:
```bash
chmod +x setup.sh
```

---

### 3. `debug.sh` - Debug e Testes

Script para testar conectividade, validar dados e gerar reports diagnósticos.

```bash
# Testar Docker
./debug.sh docker

# Testar containers
./debug.sh containers

# Testar PostgreSQL
./debug.sh postgres

# Testar MinIO
./debug.sh minio

# Testar Flask
./debug.sh flask

# Validar dados (Bronze/Silver/Gold)
./debug.sh validate

# Rodar testes específicos
./debug.sh test-bronze
./debug.sh test-silver
./debug.sh test-gold
./debug.sh test-postgis
./debug.sh test-all

# Verificação completa
./debug.sh status

# Gerar report diagnóstico
./debug.sh report
```

**Permissões**:
```bash
chmod +x debug.sh
```

---

### 4. `Makefile` - Alternativa (Padrão Linux)

Makefile oferece interface type-friendly para tasks comuns.

```bash
# Setup
make setup

# Docker
make up
make down
make status
make build
make rebuild

# Pipeline
make pipeline
make bronze
make silver
make gold
make postgis
make test

# Logs
make logs
make logs-pipeline
make logs-postgis
make logs-web

# Acesso
make shell
make db
make minio

# Maintenance
make clean
make prune
make verify
```

**Vantagens do Makefile:**
- Interface consistente de linha única
- Sem precisar de `./` ou extensão
- Melhor para CI/CD
- Mais portável entre ferramentas

---

## 🚀 Quick Start (Linux/macOS)

```bash
# 1. Clonar/navegar para projeto
cd esteira-geo

# 2. Fazer scripts executáveis
chmod +x setup.sh docker.sh debug.sh

# 3. Setup inicial (instala Docker, Python, etc)
./setup.sh

# 4. Iniciar ambiente Docker
./docker.sh up

# 5. Rodar pipeline
./docker.sh pipeline

# 6. Verificar status
./docker.sh status
```

---

## 📊 Fluxo Típico de Desenvolvimento

```bash
# 1️⃣ Primeira vez
./setup.sh

# 2️⃣ Iniciar ambiente
./docker.sh up

# 3️⃣ Testar conectividade
./debug.sh status

# 4️⃣ Rodar testes
./debug.sh test-all

# 5️⃣ Ver logs
./docker.sh logs pipeline

# 6️⃣ Acessar banco de dados
./docker.sh db

# 7️⃣ Parar
./docker.sh down
```

---

## 🔍 Usando Makefile (Alternativa)

Se preferir Makefile (mais padrão em Linux):

```bash
# Setup
make setup

# Iniciar
make up

# Executar pipeline
make pipeline

# Testes
make test

# Logs
make logs-pipeline

# Banco de dados
make db

# Parar
make down
```

---

## 🆘 Troubleshooting

### Script não é executável

```bash
# Tornar executável
chmod +x script.sh

# Ou com Makefile (sem permissão necessária)
make target
```

### Permissão negada no Docker

```bash
# Adicionar user ao grupo docker
sudo usermod -aG docker $USER

# Ativar mudanças (uma das opções)
newgrp docker
# ou fazer logout/login
```

### PostgreSQL não inicia

```bash
# Testar conexão
./debug.sh postgres

# Ver logs
./docker.sh logs postgis

# Reiniciar
./docker.sh down
./docker.sh up
```

### Dados não persistem

```bash
# Verificar volumes
docker volume ls | grep esteira

# Validar camadas
./debug.sh validate

# Conferir permissões de arquivo
ls -la /data/bronze/
```

### Sem espaço em disco

```bash
# Limpar Docker
./docker.sh clean

# OU com Makefile
make clean
make prune
```

---

## 📝 Notas Importantes

### Diferenças entre Scripts

| Script | Uso | Vantagens |
|--------|-----|-----------|
| `docker.sh` | Principal | Colorido, funções específicas |
| `setup.sh` | First-time | Instala dependências do SO |
| `debug.sh` | Debugging | Testes granulares, report |
| `Makefile` | Alternativa | Padrão Linux, simples |

### Escolher qual usar

- **Novo projeto**: `./setup.sh` → `make up`
- **Desenvolvimento diário**: `make` (mais rápido)
- **Debugging**: `./debug.sh`
- **Production**: Ambos funcionam

### Adicionar ao PATH (opcional)

```bash
# Criar symlink em /usr/local/bin (Linux/macOS)
sudo ln -s "$(pwd)/docker.sh" /usr/local/bin/esteira-docker
sudo ln -s "$(pwd)/debug.sh" /usr/local/bin/esteira-debug

# Usar de qualquer lugar
esteira-docker status
esteira-debug validate
```

---

## 📚 Documentação Relacionada

- [DOCKER_SETUP.md](./DOCKER_SETUP.md) - Setup Docker (antes dos scripts)
- [pipeline/DOCKER.md](./pipeline/DOCKER.md) - Detalhes do pipeline
- [README.md](./README.md) - Documentação principal
- [docker-compose.yml](./docker-compose.yml) - Configuração dos containers
