# Diagramas De Arquitetura - Índice

Colecção de diagramas Mermaid visualizando a arquitetura completa do projeto Esteira Geo.

## 📊 Diagramas Renderizados

Clique para visualizar os diagramas em alta qualidade:

### 1. **Arquitetura Terraform/Ansible** 
🔗 [Versão Mermaid HTML](./diagrams/terraform_architecture.html)

Mostra deployment em **nuvem pública** com multi-cloud suporte.

```
Terraform (IaC)
    ↓
    ├─ AWS Cloud
    │  ├─ S3 Buckets
    │  ├─ EC2 VMs
    │  └─ RDS PostgreSQL
    │
    └─ Huawei Cloud
       ├─ OBS Buckets
       ├─ ECS VMs
       └─ RDS PostgreSQL
    
Ansible (Config Management)
    ↓ deploy on VMs
    ├─ Processing: Python pipeline
    └─ Presentation: Flask + Nginx
```

**Quando usar:**
- ✅ Ambiente de **produção**
- ✅ Infraestrutura em **nuvem pública**
- ✅ Múltiplas regiões/clouds
- ✅ Escalabilidade automática

---

### 2. **Arquitetura Docker Local**
🔗 [Versão Mermaid HTML](./diagrams/docker_architecture.html)

Ambiente **completo dockerizado** para desenvolvimento local.

```
Docker Compose
    ↓
    ├─ PostgreSQL 13 + PostGIS
    │  └─ Health: pg_isready
    │
    ├─ MinIO (S3 simulado)
    │  ├─ Port 9000 (API)
    │  └─ Port 9001 (Console)
    │
    ├─ Pipeline ETL Container
    │  ├─ Bronze Loader
    │  ├─ Silver Processor
    │  ├─ Gold Processor (Spatial Join)
    │  └─ PostGIS Loader
    │
    └─ Flask Web Container
       ├─ Flask (port 5000)
       ├─ Gunicorn (4 workers)
       └─ Nginx (reverse proxy)

Volumes Persistentes
    ├─ postgres_data/
    ├─ minio_data/
    ├─ pipeline_bronze/
    ├─ pipeline_silver/
    └─ pipeline_gold/
```

**Quando usar:**
- ✅ **Desenvolvimento local** (sem credenciais)
- ✅ **Testes rápidos** (2-3 min startup)
- ✅ **Debugging** (ambiente isolado)
- ✅ **Aprendizado** (toda stack em um lugar)

---

### 3. **Fluxo Medallion (Bronze → Silver → Gold)**
🔗 [Versão Mermaid HTML](./diagrams/medallion_flow.html)

Visualização do **fluxo de dados** através das camadas de processamento.

```
INPUT DATA
  ├─ Flooding Areas (3 polygons)
  └─ Citizens (100 points)
     ↓

BRONZE LAYER (Raw)
  ├─ flooding_areas.parquet (3 records)
  ├─ citizens.parquet (100 records)
  └─ Format: GeoParquet (CRS: EPSG:4326)
     ↓

SILVER LAYER (Normalized)
  ├─ Validate geometries
  ├─ Remove duplicates
  ├─ Standardize types
  └─ Parse dates
     ↓

GOLD LAYER (Processed)
  ├─ Spatial Join (ST_Contains)
  ├─ 60 Affected Citizens ✓
  ├─ 40 Unaffected Citizens ✗
  └─ 100 Total Summary
     ↓

PostGIS (Spatial DB)
  ├─ flooding_areas table
  ├─ citizens table
  ├─ GIST spatial indexes
  └─ v_citizens_summary view
     ↓

FLASK DASHBOARD
  ├─ REST APIs
  ├─ Web UI (HTML/CSS/JS)
  └─ Map Integration
```

**Quando usar:**
- ✅ Entender **fluxo de dados**
- ✅ Compreender **transformações**
- ✅ Design de **novas features**
- ✅ Documentação

---

## 📁 Arquivos

| Arquivo | Conteúdo |
|---------|----------|
| `DIAGRAMAS.md` | Documentação detalhada dos 3 diagramas |
| `MERMAID_DIAGRAMS.md` | Código Mermaid e instruções de export |
| `diagrams/*.mmd` | Arquivo Mermaid bruto (editável) |
| `diagrams/*.html` | Versão HTML interativa |
| `diagrams/*.png` | Imagem PNG (renderizada) |

---

## 🎯 Quando Usar Cada Diagrama

```
ESCOLHER TERRAFORM/ANSIBLE SE:
  ✓ Você tem credenciais AWS ou Huawei
  ✓ Quer environment em produção
  ✓ Precisa de escalabilidade automática
  ✓ Multi-cloud é um requisito

ESCOLHER DOCKER SE:
  ✓ Estou desenvolvendo localmente
  ✓ Não tenho credenciais de nuvem
  ✓ Quero feedback rápido
  ✓ Vou depois migrar para Terraform

ESCOLHER MEDALLION FLOW SE:
  ✓ Quero entender transformações de dados
  ✓ Vou customizar o pipeline
  ✓ Preciso documentar para team
  ✓ Estou planejando novas features
```

---

## 🔄 Fluxo Recomendado

```
1. Ler DIAGRAMAS.md
   └─ Entender arquitetura de alto nível

2. Visualizar Docker Architecture
   └─ Começar com desenvolvimento local

3. Executar docker.sh up && docker.sh pipeline
   └─ Ver fluxo de dados na prática

4. Visualizar Medallion Flow
   └─ Correlacionar código com diagrama

5. (Se indo para produção) Visualizar Terraform/Ansible
   └─ Adaptar para credenciais reais

6. Deploy com Terraform + Ansible
   └─ Usar diagrama como referência de configuração
```

---

## 📖 Links Úteis

**Documentação:**
- `README.md` - Overview do projeto
- `DIAGRAMAS.md` - Explicação dos 3 diagramas
- `MERMAID_DIAGRAMS.md` - Código e export
- `DOCKER_SETUP.md` - Setup Docker
- `SCRIPTS_BASH.md` - Scripts de automação

**Código Relacionado:**
- `pipeline/etl/` - Implementação do pipeline
- `terraform/` - Infraestrutura em nuvem
- `ansible/` - Automação de VMs
- `docker-compose.yml` - Compose local
- `pipeline/main.py` - Orquestrador do pipeline

---

## 🎨 Customizar Diagramas

Para editar os diagramas:

1. Abra [Mermaid Live Editor](https://mermaid.live)
2. Copie o conteúdo de `diagrams/*.mmd`
3. Cole no editor
4. Faça suas mudanças
5. Exporte como PNG/SVG

## 💾 Exportar para PNG/SVG

```bash
# Instalar CLI
npm install -g @mermaid-js/mermaid-cli

# Converter
mmdc -i diagrams/docker_architecture.mmd -o diagrams/docker_architecture.png
mmdc -i diagrams/terraform_architecture.mmd -o diagrams/terraform_architecture.png
mmdc -i diagrams/medallion_flow.mmd -o diagrams/medallion_flow.png
```

---

## ✅ Checklist

- [ ] Li DIAGRAMAS.md
- [ ] Visualizei os 3 diagramas HTML
- [ ] Entendi que Terraform = Cloud, Docker = Local
- [ ] Selecionei qual path seguir (Cloud vs Local)
- [ ] Correlacionei diagrama com código
- [ ] Estou pronto para deployment

Bom desenvolvimento! 🚀
