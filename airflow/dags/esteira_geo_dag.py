"""
DAG: esteira_geo

Orquestra o pipeline original (silver → gold → postgis) sem modificar nenhum
arquivo do pipeline. Os módulos são importados via PYTHONPATH=/opt/airflow/pipeline.

Disparada automaticamente pela DAG esteira_geo_watcher ao detectar arquivos
novos em bronze/automatizado/<use_case>/.

Trigger manual:
    airflow dags trigger esteira_geo --conf '{"use_case": "enchentes_rj"}'
"""

import os
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

log = logging.getLogger(__name__)

DEFAULT_USE_CASE = os.getenv("USE_CASE", "enchentes_poa")

default_args = {
    "owner": "esteira-geo",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


def _use_case(context) -> str:
    return context["dag_run"].conf.get("use_case", DEFAULT_USE_CASE)


def _reload_pipeline_modules():
    """Limpa cache de módulos do pipeline para garantir USE_CASE atualizado."""
    import sys
    for mod in list(sys.modules.keys()):
        if mod in ("config", "etl.silver_processor", "etl.gold_processor", "etl.postgis_loader"):
            del sys.modules[mod]


def task_silver(**context):
    use_case = _use_case(context)
    os.environ["USE_CASE"] = use_case
    _reload_pipeline_modules()

    from etl.silver_processor import process_silver
    try:
        result = process_silver()
    except RuntimeError as e:
        if "bronze" in str(e).lower() or "nenhum arquivo" in str(e).lower():
            log.warning(f"[silver] Bronze vazio para {use_case}, encerrando sem retry.")
            context["ti"].xcom_push(key="has_flooding", value=False)
            context["ti"].xcom_push(key="has_citizens", value=False)
            return
        raise

    context["ti"].xcom_push(key="has_flooding", value="flooding" in result)
    context["ti"].xcom_push(key="has_citizens", value="citizens" in result)
    log.info(f"[silver] flooding={'flooding' in result} citizens={'citizens' in result}")


def task_branch_gold(**context):
    """Verifica o silver acumulado total para decidir o próximo passo."""
    use_case = _use_case(context)
    os.environ["USE_CASE"] = use_case
    _reload_pipeline_modules()

    from etl.silver_processor import silver_exists
    from config import FLOODING_AREAS_FILE, CITIZENS_FILE

    has_flooding = silver_exists(f"silver_{FLOODING_AREAS_FILE}")
    has_citizens = silver_exists(f"silver_{CITIZENS_FILE}")
    log.info(f"[branch] silver: flooding={has_flooding} citizens={has_citizens}")

    if has_flooding and has_citizens:
        return "gold"
    elif has_flooding:
        return "postgis_areas_only"
    return "skip_gold"


def task_gold(**context):
    use_case = _use_case(context)
    os.environ["USE_CASE"] = use_case
    _reload_pipeline_modules()

    from etl.gold_processor import process_gold
    affected, unaffected, all_summary = process_gold()
    log.info(f"[gold] afetados={len(affected)} não_afetados={len(unaffected)} total={len(all_summary)}")


def task_postgis(**context):
    use_case = _use_case(context)
    os.environ["USE_CASE"] = use_case
    _reload_pipeline_modules()

    from etl.postgis_loader import load_to_postgis
    load_to_postgis(sync_areas=True, sync_citizens=True)


def task_postgis_areas_only(**context):
    use_case = _use_case(context)
    os.environ["USE_CASE"] = use_case
    _reload_pipeline_modules()

    # Garantir que o gold de áreas existe antes de sincronizar o PostGIS
    from etl.gold_processor import process_gold_areas_only
    process_gold_areas_only()

    from etl.postgis_loader import load_to_postgis
    load_to_postgis(sync_areas=True, sync_citizens=False)


with DAG(
    dag_id="esteira_geo",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["geo", "medallion"],
    doc_md=__doc__,
) as dag:

    silver = PythonOperator(task_id="silver", python_callable=task_silver)
    branch = BranchPythonOperator(task_id="branch_gold", python_callable=task_branch_gold)
    gold = PythonOperator(task_id="gold", python_callable=task_gold)
    postgis = PythonOperator(task_id="postgis", python_callable=task_postgis)
    postgis_areas = PythonOperator(task_id="postgis_areas_only", python_callable=task_postgis_areas_only)
    skip_gold = EmptyOperator(task_id="skip_gold")

    silver >> branch
    branch >> gold >> postgis
    branch >> postgis_areas
    branch >> skip_gold
