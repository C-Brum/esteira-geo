# Pipeline - Esteira de Processamento Geoespacial

## 📋 Caso de Uso

**Batimento Geográfico de Áreas Atingidas por Enchentes - Rio Grande do Sul**

Objetivo: Identificar quais cidadãos estão em áreas atingidas por enchentes em Porto Alegre através de operações geoespaciais.

### Dados de Entrada

1. **Áreas de Enchente** (3 polígonos):
   - Partenon
   - Centro/Menino Deus
   - Zona Norte
   - Contém: id, nome, data, severidade, população afetada

2. **Dados de Cidadãos** (100 registros):
   - 60 cidadãos em áreas de risco
   - 40 cidadãos em áreas seguras
   - Contém: id, nome, endereço, telefone, data registro, geometria (ponto)

### Processamento

```
Bronze → Silver → Gold → PostGIS → Flask
```

- **Bronze**: Geração de dados de exemplo em GeoParquet
- **Silver**: Normalização e validação de qualidade
- **Gold**: Batimento geográfico (spatial join)
- **PostGIS**: Armazenamento em RDS com índices espaciais
- **Flask**: Visualização e APIs

### Saída

3 arquivos GeoParquet + dados em PostGIS:

1. `affected_citizens.parquet` - 60 cidadãos em área atingida
2. `unaffected_citizens.parquet` - 40 cidadãos fora de área atingida
3. `all_citizens_evaluated.parquet` - 100 cidadãos com status

---

## 🚀 Como Executar

### 1. Setup Inicial

```bash
cd pipeline
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env na raiz do pipeline
cat > .env << EOF
AWS_S3_BRONZE_BUCKET=esteira-geo-bronze-xxxxx
AWS_S3_SILVER_BUCKET=esteira-geo-silver-xxxxx
AWS_S3_GOLD_BUCKET=esteira-geo-gold-xxxxx
RDS_HOST=esteira-geo-postgres.xxxxx.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=esteira-geo
RDS_USER=postgres
RDS_PASSWORD=postgrespw
EOF
```

### 3. Executar Pipeline Completo

```bash
python main.py
```

### 4. Testes Unitários

Veja `testes_e_validacoes.txt` para comandos completos de teste.

```bash
# Teste individual Bronze
python etl/bronze_loader.py

# Teste individual Silver
python etl/silver_processor.py

# Teste individual Gold
python etl/gold_processor.py

# Teste PostGIS (requer banco online)
python etl/postgis_loader.py
```

---

## 📊 Estrutura de Arquivos

```
pipeline/
├── main.py                      # Orquestrador principal
├── config.py                    # Configurações centralizadas
├── requirements.txt             # Dependências Python
├── postgis_setup.sql            # Setup do banco de dados
├── testes_e_validacoes.txt      # Comandos de teste
├── etl/
│   ├── __init__.py
│   ├── bronze_loader.py         # Geração de dados exemplo
│   ├── silver_processor.py      # Normalização
│   ├── gold_processor.py        # Batimento geoespacial
│   └── postgis_loader.py        # Importação em RDS
├── data/                        # Arquivos de dados (local)
└── logs/                        # Logs de execução
    └── pipeline.log
```

---

## 📞 Próximas Etapas

1. Customizar dados (trocar polígonos/cidadãos)
2. Adicionar mais transformações em Silver
3. Integrar com Grafana para monitoramento
4. Implementar versionamento (MLflow/DVC)
