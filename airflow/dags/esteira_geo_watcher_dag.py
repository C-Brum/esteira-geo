"""
DAG: esteira_geo_watcher

Monitora bronze/automatizado/ a cada 30s.
Para cada use_case com arquivos novos, dispara esteira_geo — desde que não
haja já um run ativo ou enfileirado para aquele use_case.
"""

import os
import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

log = logging.getLogger(__name__)

BRONZE_BUCKET    = os.getenv("AWS_S3_BRONZE_BUCKET", "bronze")
WATCHED_EXTS     = {".csv", ".geojson", ".parquet"}
AUTO_ROOT_PREFIX = "automatizado/"


def _s3():
    import boto3
    kwargs = {
        "region_name":           os.getenv("AWS_S3_REGION_NAME", "us-east-1"),
        "aws_access_key_id":     os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }
    endpoint = os.getenv("AWS_ENDPOINT_URL")
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)


def detect_and_trigger(**context):
    """
    Lista arquivos pendentes em automatizado/<use_case>/ e dispara esteira_geo
    para cada use_case — apenas se não houver run ativo/enfileirado.
    """
    import os as _os
    from airflow.api.common.trigger_dag import trigger_dag
    from airflow.models.dagrun import DagRun
    from airflow.utils import timezone
    from airflow import settings

    # Detectar use_cases com arquivos pendentes
    s3 = _s3()
    try:
        resp = s3.list_objects_v2(Bucket=BRONZE_BUCKET, Prefix=AUTO_ROOT_PREFIX)
    except Exception as e:
        log.error(f"Erro ao listar bucket {BRONZE_BUCKET}: {e}")
        return

    pending = set()
    for obj in resp.get("Contents", []):
        key = obj["Key"]
        parts = key[len(AUTO_ROOT_PREFIX):].split("/")
        if len(parts) < 2 or "processados" in parts:
            continue
        filename = parts[-1]
        if not filename:
            continue
        if _os.path.splitext(filename)[1].lower() not in WATCHED_EXTS:
            continue
        pending.add(parts[0])

    if not pending:
        log.info("Nenhum arquivo pendente.")
        return

    log.info(f"Use cases pendentes: {sorted(pending)}")

    # Buscar use_cases já em processamento
    session = settings.Session()
    try:
        active_runs = session.query(DagRun).filter(
            DagRun.dag_id == "esteira_geo",
            DagRun.state.in_(["running", "queued"])
        ).all()
        active_use_cases = {(r.conf or {}).get("use_case") for r in active_runs}
    finally:
        session.close()

    for use_case in sorted(pending):
        if use_case in active_use_cases:
            log.info(f"[{use_case}] Já há run ativo/enfileirado, pulando.")
            continue
        run_id = f"watcher__{use_case}__{timezone.utcnow().strftime('%Y%m%dT%H%M%S')}"
        try:
            trigger_dag(dag_id="esteira_geo", run_id=run_id,
                        conf={"use_case": use_case}, replace_microseconds=False)
            log.info(f"✓ Disparado: {use_case}")
        except Exception as e:
            log.warning(f"Não foi possível disparar {use_case}: {e}")


with DAG(
    dag_id="esteira_geo_watcher",
    default_args={"owner": "esteira-geo", "retries": 0},
    start_date=datetime(2024, 1, 1),
    schedule=timedelta(seconds=30),
    catchup=False,
    max_active_runs=1,
    tags=["geo", "watcher"],
    doc_md=__doc__,
) as dag:

    PythonOperator(task_id="detecta_e_dispara", python_callable=detect_and_trigger)
