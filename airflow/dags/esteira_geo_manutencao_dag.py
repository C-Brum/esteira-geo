"""
DAG: esteira_geo_manutencao

Roda diariamente e limpa o histórico do banco Airflow,
mantendo apenas os últimos 30 dias de runs.

Usa o comando oficial `airflow db clean` do Airflow 2.9.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="esteira_geo_manutencao",
    default_args={"owner": "esteira-geo", "retries": 0},
    start_date=datetime(2024, 1, 1),
    schedule=timedelta(days=1),
    catchup=False,
    max_active_runs=1,
    tags=["geo", "manutencao"],
    doc_md=__doc__,
) as dag:

    BashOperator(
        task_id="limpar_historico_30_dias",
        bash_command=(
            "airflow db clean "
            "--clean-before-timestamp \"$(date -u -d '30 days ago' '+%Y-%m-%dT%H:%M:%S+00:00')\" "
            "--skip-archive --yes"
        ),
    )
