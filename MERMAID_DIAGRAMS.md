# Mermaid Diagrams - Esteira Geo

Diagramas de arquitetura em formato Mermaid refletindo o ambiente atual do projeto.

## 📊 Diagramas Disponíveis

---

### 1. Arquitetura Docker Local
**Arquivo**: `diagrams/docker_architecture.mmd`

Stack Docker completa com Airflow, JupyterLab e volumes bind para edição ao vivo.

```mermaid
graph TB
    subgraph host["🖥️ Host Machine"]
        dags_dir["📁 airflow/dags/\n3 DAGs"]
        pipeline_dir["📁 pipeline/\netl/ + config.py + web/"]
        notebooks_dir["📓 notebooks/\nesteira_geo.ipynb\nutilitarios.ipynb"]
    end

    subgraph docker_network["🌐 Docker Network: esteira-network"]
        subgraph postgis_service["PostgreSQL + PostGIS"]
            db["🗄️ Port: 5432\npipeline + Airflow metadata"]
        end
        subgraph minio_service["MinIO"]
            b_bronze["bronze/automatizado/use_case/\nprocessados/"]
            b_silver["silver/use_case/"]
            b_gold["gold/use_case/"]
        end
        subgraph airflow_services["Apache Airflow"]
            af_webserver["🖥️ Webserver :8080\nadmin/admin"]
            subgraph scheduler["⚙️ Scheduler"]
                watcher["esteira_geo_watcher\n30s"]
                main_dag["esteira_geo\nsilver→branch→gold→postgis"]
                manut["esteira_geo_manutencao\ndiário, 30 dias"]
            end
            watcher -->|trigger| main_dag
        end
        pipeline_service["Pipeline ETL\nidle"]
        web_service["Flask :5000\nLeaflet + SVG markers"]
        jupyter_service["JupyterLab :8888\ntoken: esteira"]
    end

    dags_dir -->|volume| scheduler
    pipeline_dir -->|volume| scheduler
    pipeline_dir -->|volume| web_service
    notebooks_dir -->|bind| jupyter_service
    main_dag -->|lê/escreve| b_bronze
    main_dag -->|salva| b_silver
    main_dag -->|salva| b_gold
    main_dag -->|TRUNCATE+INSERT| db
    web_service -->|queries| db

    style host fill:#2196F3,stroke:#000,color:#fff
    style docker_network fill:#1b5e20,stroke:#000,color:#fff
    style airflow_services fill:#017CEE,stroke:#000,color:#fff
    style scheduler fill:#0052cc,stroke:#000,color:#fff
```

---

### 2. Fluxo Medallion (Bronze → Silver → Gold → PostGIS)
**Arquivo**: `diagrams/medallion_flow.mmd`

Fluxo de dados com Airflow como orquestrador, silver acumulativo e gold como fonte exclusiva do PostGIS.

```mermaid
graph LR
    subgraph input["📥 bronze/automatizado/"]
        uc_a["use_case_a/\nCSV + GeoJSON"]
        processed["processados/\n(após silver salvo)"]
    end

    subgraph airflow["⚙️ Airflow"]
        sensor["watcher 30s\nnão duplica runs"]
        branch["branch_gold\nverifica silver total"]
        sensor --> branch
    end

    subgraph silver_layer["⚪ SILVER"]
        s_checks["_safe_concat\nWKT + datetime str\nschema-tolerante\nAcumulativo por ID"]
    end

    subgraph gold_layer["🟡 GOLD\nFonte exclusiva PostGIS"]
        g_areas_only["flooding_areas.parquet\n(mesmo sem cidadãos)"]
        g_full["affected + unaffected\nall_citizens_evaluated\nflooding_areas"]
    end

    subgraph postgis["🗺️ PostGIS"]
        pg["use_case_citizens\nuse_case_flooding_areas\nTRUNCATE + INSERT"]
    end

    subgraph flask["🌐 Flask :5000"]
        map["/map\nSVG markers\nfitBounds em áreas\nfallback use_case"]
    end

    input --> airflow
    airflow --> s_checks
    s_checks --> g_areas_only
    s_checks --> g_full
    g_areas_only --> pg
    g_full --> pg
    pg --> map
    uc_a --> processed

    style input fill:#4E342E,stroke:#000,color:#fff
    style airflow fill:#017CEE,stroke:#000,color:#fff
    style silver_layer fill:#616161,stroke:#000,color:#fff
    style gold_layer fill:#F9A825,stroke:#000,color:#000
    style postgis fill:#336791,stroke:#000,color:#fff
    style flask fill:#013243,stroke:#000,color:#fff
```

---

### 3. Arquitetura Terraform/Ansible (Cloud)
**Arquivo**: `diagrams/terraform_architecture.mmd`

Deploy multi-cloud com Airflow nas VMs de processamento.

```mermaid
graph TB
    subgraph user["👤 Developer/Admin"]
        tf["Terraform >= 1.0"]
        ansible["Ansible"]
    end

    subgraph aws["☁️ AWS Cloud"]
        aws_s3["S3: Bronze/Silver/Gold"]
        aws_proc["EC2: Processing\nAirflow + Pipeline ETL"]
        aws_web["EC2: Presentation\nFlask + Nginx"]
        aws_rds["RDS PostgreSQL\n+ PostGIS\n+ Airflow metadata"]
    end

    subgraph huawei["☁️ Huawei Cloud SP"]
        hw_obs["OBS: Bronze/Silver/Gold"]
        hw_proc["ECS: Processing\nAirflow + Pipeline ETL"]
        hw_web["ECS: Presentation\nFlask + Nginx"]
        hw_rds["RDS PostgreSQL\n+ PostGIS\n+ Airflow metadata"]
    end

    subgraph pipeline["🔄 DAGs Airflow"]
        p_w["esteira_geo_watcher\n30s"]
        p_m["esteira_geo\nsilver→gold→postgis"]
        p_c["esteira_geo_manutencao\ndiário 30 dias"]
        p_w --> p_m
    end

    user -->|terraform apply| aws
    user -->|terraform apply| huawei
    user -->|ansible-playbook| aws_proc
    user -->|ansible-playbook| aws_web
    user -->|ansible-playbook| hw_proc
    user -->|ansible-playbook| hw_web

    aws_proc -->|executa| pipeline
    pipeline <-->|S3| aws_s3
    pipeline -->|sincroniza| aws_rds
    aws_web -->|queries| aws_rds

    hw_proc -->|executa| pipeline
    pipeline <-->|OBS| hw_obs
    pipeline -->|sincroniza| hw_rds
    hw_web -->|queries| hw_rds

    style aws fill:#FF9900,stroke:#000,color:#000
    style huawei fill:#E60012,stroke:#000,color:#fff
    style pipeline fill:#017CEE,stroke:#000,color:#fff
    style user fill:#2196F3,stroke:#000,color:#fff
```

---

## 🎨 Visualizar Online

1. Abra [Mermaid Live Editor](https://mermaid.live)
2. Copie o conteúdo de um arquivo `.mmd` em `diagrams/`
3. Cole no editor

## 💾 Exportar para PNG/SVG

```bash
npm install -g @mermaid-js/mermaid-cli

mmdc -i diagrams/docker_architecture.mmd    -o diagrams/docker_architecture.png
mmdc -i diagrams/medallion_flow.mmd         -o diagrams/medallion_flow.png
mmdc -i diagrams/terraform_architecture.mmd -o diagrams/terraform_architecture.png
```
