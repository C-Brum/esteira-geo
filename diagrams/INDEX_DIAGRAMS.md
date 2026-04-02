# 📊 Índice de Diagramas - Esteira Geo

Referência rápida de todos os diagramas de arquitetura do projeto.

---

## 🎨 Os 3 Diagramas Principais

| # | Nome | Tipo | Descrição | Arquivo |
|---|------|------|-----------|---------|
| 1️⃣ | **Terraform/Ansible** | Infraestrutura | Multi-cloud (AWS + Huawei) com Airflow nas VMs | `terraform_architecture.mmd` |
| 2️⃣ | **Docker Local** | Ambiente | Stack Docker com Airflow, JupyterLab, volumes bind | `docker_architecture.mmd` |
| 3️⃣ | **Medallion Flow** | Pipeline | Bronze → Silver → Gold → PostGIS orquestrado pelo Airflow | `medallion_flow.mmd` |

---

## ⚡ Quick Links

```
📁 diagrams/
├─ terraform_architecture.mmd
├─ docker_architecture.mmd
├─ medallion_flow.mmd
├─ README.md
└─ INDEX_DIAGRAMS.md  (este arquivo)
```

---

## 🔗 O que cada diagrama mostra

### 1️⃣ Terraform/Ansible Architecture

- 2 Clouds (AWS + Huawei São Paulo)
- S3/OBS buckets (Bronze/Silver/Gold)
- EC2/ECS VMs: processing (Airflow + Pipeline) + presentation (Flask)
- RDS PostgreSQL + PostGIS (pipeline + Airflow metadata)
- Fluxo Terraform → Ansible → DAGs

**Quando usar:** deploy em produção, planejamento de infraestrutura

---

### 2️⃣ Docker Local Architecture

- Host com volumes bind (dags, etl, config, web — editáveis ao vivo)
- PostgreSQL + PostGIS (pipeline + Airflow metadata)
- MinIO com estrutura de buckets (bronze/automatizado/processados, silver, gold)
- Airflow: init + scheduler + webserver (port 8080)
  - `esteira_geo_watcher` (30s)
  - `esteira_geo` (trigger)
  - `esteira_geo_manutencao` (diário, 30 dias)
- Pipeline ETL (idle), Flask (port 5000), JupyterLab (port 8888)

**Quando usar:** desenvolvimento local, debugging, aprendizado

---

### 3️⃣ Medallion Flow (Data Pipeline)

- Input: CSV/GeoJSON em `bronze/automatizado/<use_case>/`
- Airflow watcher (30s, sem duplicatas por use_case)
- Silver: `_safe_concat` (WKT + datetime str, schema-tolerante, acumulativo)
- Move para `processados/` **somente após** salvar no S3
- Gold: sempre gerado antes do PostGIS
  - `process_gold_areas_only()` quando só há áreas
  - `process_gold()` quando há áreas + cidadãos
- PostGIS: TRUNCATE + INSERT (espelho do gold)
- Flask: fallback automático de use_case, SVG markers, fitBounds em áreas

**Quando usar:** entender transformações, onboarding, documentação

---

## 🛠️ Ferramentas

```bash
# Visualizar online
# https://mermaid.live

# Exportar PNG
npm install -g @mermaid-js/mermaid-cli
mmdc -i diagrams/docker_architecture.mmd -o diagrams/docker_architecture.png
mmdc -i diagrams/medallion_flow.mmd -o diagrams/medallion_flow.png
mmdc -i diagrams/terraform_architecture.mmd -o diagrams/terraform_architecture.png
```

---

## ✅ Checklist: Qual Diagrama Usar?

```
☁️ VOU FAZER DEPLOY EM NUVEM?
  → Terraform/Ansible Architecture
    ✓ Infraestrutura real (AWS/Huawei)
    ✓ VMs com Airflow, buckets, RDS

💻 VOU DESENVOLVER LOCALMENTE?
  → Docker Local Architecture
    ✓ Stack completa dockerizada
    ✓ Airflow UI (port 8080)
    ✓ Volumes bind (edição ao vivo)

📊 VOU ENTENDER O PIPELINE?
  → Medallion Flow
    ✓ Orquestração pelo Airflow
    ✓ Bronze → Silver → Gold
    ✓ Correções de schema e ordem de operações
```

---

**Diagramas**: 3 (Terraform/Ansible, Docker, Medallion)
**Formatos**: `.mmd` (editável), `.png` (exportável via mermaid-cli)
