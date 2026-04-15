#!/bin/bash
set -e

# Trigger manual de um use_case via Airflow CLI
# Uso: ./run_pipeline.sh enchentes_poa

USE_CASE=${1:-enchentes_poa}
APP_DIR=/home/esteira/esteira-geo

cd "$APP_DIR"
source venv/bin/activate
set -a && source .env && set +a

airflow dags trigger esteira_geo --conf "{\"use_case\": \"$USE_CASE\"}"

echo "DAG esteira_geo triggered for use_case=$USE_CASE at $(date)"
