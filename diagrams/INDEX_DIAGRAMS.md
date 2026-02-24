# 📊 Índice de Diagramas - Esteira Geo

Referência rápida de todos os diagramas de arquitetura do projeto.

---

## 🎨 Os 3 Diagramas Principais

| # | Nome | Tipo | Descrição | Para Quem | Arquivo |
|---|------|------|-----------|-----------|---------|
| 1️⃣ | **Terraform/Ansible** | Infraestrutura | Multi-cloud (AWS + Huawei) com Terraform e Ansible | DevOps / Cloud Architects | `terraform_architecture.mmd` |
| 2️⃣ | **Docker Local** | Ambiente | Stack Docker completo para desenvolvimento local | Desenvolvedores | `docker_architecture.mmd` |
| 3️⃣ | **Medallion Flow** | Pipeline | Fluxo de dados (Bronze → Silver → Gold → PostGIS) | Data Engineers / Analysts | `medallion_flow.mmd` |

---

## ⚡ Quick Links

```
📁 diagrams/
├─ terraform_architecture.mmd      (↓ Visualize em Mermaid Live)
├─ docker_architecture.mmd         (↓ Visualize em Mermaid Live)
├─ medallion_flow.mmd              (↓ Visualize em Mermaid Live)
├─ README.md                        (Como usar diagramas)
└─ INDEX_DIAGRAMS.md               (Este arquivo)
```

---

## 🔗 Visualizar Online

### 1️⃣ Terraform/Ansible Architecture
```
Abra: https://mermaid.live
Cole este código:
↓ [diagrams/terraform_architecture.mmd]
```

Mostra:
- 2 Clouds (AWS + Huawei São Paulo)
- S3/OBS buckets (Bronze/Silver/Gold medallion)
- EC2/ECS VMs (processing + presentation)
- RDS PostgreSQL com PostGIS
- Fluxo Terraform → Ansible

**Quando usar:**
- ☁️ Deploy em produção
- 📊 Planejamento de infraestrutura
- 🔄 Multi-cloud strategy
- 📚 Documentação técnica

---

### 2️⃣ Docker Local Architecture
```
Abra: https://mermaid.live
Cole este código:
↓ [diagrams/docker_architecture.mmd]
```

Mostra:
- Host machine (Windows/Linux/macOS)
- Docker Compose orquestração
- PostgreSQL 13 + PostGIS
- MinIO (S3 simulado)
- Pipeline ETL container
- Flask web container
- 5 volumes (postgres, minio, bronze, silver, gold)

**Quando usar:**
- 💻 Desenvolvimento local
- 🧪 Testes rápidos
- 🎓 Aprendizado
- 🐳 CI/CD local

---

### 3️⃣ Medallion Flow (Data Pipeline)
```
Abra: https://mermaid.live
Cole este código:
↓ [diagrams/medallion_flow.mmd]
```

Mostra:
- Input (3 flood areas + 100 citizens)
- Bronze layer (raw GeoParquet)
- Silver layer (normalized with validation)
- Gold layer (spatial join results)
- PostGIS (spatial database)
- Flask dashboard (visualization)

**Quando usar:**
- 📈 Entender transformações
- 🎯 Desenhar features
- 👥 Onboarding data team
- 📖 Documentação pipeline

---

## 🛠️ Ferramentas

### Visualizar
- **Online**: https://mermaid.live (recomendado)
- **GitHub**: Renderiza automaticamente no README
- **VS Code**: Extensão `markdown-mermaid`

### Editar
- **Mermaid Live**: Interface visual
- **VS Code**: Edit + preview lado a lado
- **Texto puro**: Qualquer editor

### Exportar
```bash
# Instalar
npm install -g @mermaid-js/mermaid-cli

# Converter
mmdc -i terraform_architecture.mmd -o terraform_architecture.png
mmdc -i docker_architecture.mmd -o docker_architecture.png
mmdc -i medallion_flow.mmd -o medallion_flow.png
```

---

## 📖 Documentação

| Arquivo | Conteúdo |
|---------|----------|
| `README_DIAGRAMS.md` | Overview, quando usar cada diagrama |
| `DIAGRAMAS.md` | Explicação detalhada dos 3 diagramas |
| `MERMAID_DIAGRAMS.md` | Código bruto + instruções export |
| `diagrams/README.md` | Como editar e manter diagramas |
| `diagrams/INDEX_DIAGRAMS.md` | Este arquivo (quick ref) |

---

## ✅ Checklist: Qual Diagrama Usar?

### ☁️ Vou fazer DEPLOY EM NUVEM?
→ Use **Terraform/Ansible Architecture**
```
✓ Mostra infraestrutura real (AWS/Huawei)
✓ Mostra VMs, buckets, RDS
✓ Mostra orquestração com Terraform/Ansible
```

### 💻 Vou DESENVOLVER LOCALMENTE?
→ Use **Docker Local Architecture**
```
✓ Mostra stack completo dockerizado
✓ Mostra volumes, networks, containers
✓ Mostra como tudo se conecta
```

### 📊 Vou ENTENDER O PIPELINE?
→ Use **Medallion Flow**
```
✓ Mostra transformação de dados
✓ Mostra Bronze → Silver → Gold
✓ Mostra SQL queries + visualização
```

### 👥 Vou DOCUMENTAR PARA O TEAM?
→ Use **TODOS OS 3!**
```
✓ Terraform/Ansible: Arquitetos explicam infraestrutura
✓ Docker: Devs entendem ambiente local
✓ Medallion: Data team entende transformações
```

---

## 🎯 Recomendação de Workflow

```
1. Comece com Docker Local Architecture
   └─ Entenda ambiente local

2. Execute pipeline localmente
   └─ ./docker.sh up && ./docker.sh pipeline

3. Olhe para Medallion Flow
   └─ Correlacione código com diagrama

4. Leia Terraform/Ansible Architecture
   └─ Prepare para deploy em cloud

5. (Se deploy) Use como referência
   └─ Adapte para credenciais reais
```

---

## 🔄 Manutenção

Quando algo muda:

1. **Diagrama desatualizado?**
   - Edite `.mmd` em Mermaid Live
   - Exporte PNG (se necessário)
   - Atualize documentação

2. **Código mudou?**
   - Revise diagramas relacionados
   - Atualize `.mmd`
   - Commit junto com código

3. **Nova feature?**
   - Adicione ao Medallion Flow
   - Atualize documentação
   - Notifique team

---

## 🚀 Próximas Etapas

- [ ] Abrir https://mermaid.live
- [ ] Visualizar os 3 diagramas
- [ ] Entender qual serve para quê
- [ ] Salvar PNGs se precisar (slides, docs)
- [ ] Compartilhar com team
- [ ] Usar como referência no desenvolvimento

---

## 📞 Referências

- **Mermaid Docs**: https://mermaid.js.org/
- **Mermaid Live**: https://mermaid.live/
- **Este projeto**: [README.md](../README.md)
- **Documentação Completa**: [DIAGRAMAS.md](../DIAGRAMAS.md)

---

**Status**: ✅ Completo  
**Última atualização**: Feb 24, 2026  
**Diagramas**: 3 (renderizados com sucesso)  
**Formatos**: `.mmd` (editável), `.png` (exportável)
