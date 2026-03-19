"""
Gold Processor — Spark + Sedona
Equivalente ao gold_processor.py, usando ST_Within do Sedona para o spatial join.

Entrada : GeoParquet em /data/silver/<use_case>/silver_*.parquet
Saída   : GeoParquet em /data/gold/<use_case>/{affected,unaffected,all_citizens_evaluated}.parquet
"""

import logging
from pathlib import Path

from pyspark.sql import functions as F

from etl.spark.session import get_spark
from config import (
    LOCAL_SILVER_USE_CASE, LOCAL_GOLD_USE_CASE,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, ALL_CITIZENS_FILE,
    FLOODING_AREAS_FILE, CITIZENS_FILE,
)

logger = logging.getLogger(__name__)


def _read_geoparquet(spark, path: str):
    return spark.read.format("geoparquet").load(path)


def _save_geoparquet(df, path: str):
    """Salva DataFrame como GeoParquet em arquivo único (compatível com GeoPandas)."""
    import shutil
    import glob

    path = Path(path)
    tmp = Path("/tmp") / (path.name + "._spark_tmp")

    if tmp.exists():
        shutil.rmtree(str(tmp))

    df.coalesce(1).write.format("geoparquet").mode("overwrite").save(str(tmp))

    parts = glob.glob(f"{tmp}/part-*.parquet")
    if not parts:
        raise RuntimeError(f"Nenhum part file encontrado em {tmp}")

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_dir():
            shutil.rmtree(str(path))
        else:
            path.unlink()

    shutil.move(parts[0], str(path))
    shutil.rmtree(str(tmp))

    logger.info(f"✓ Salvo Gold (Spark): {path}")


def process_gold_spark():
    """Orquestrador Gold com Spark+Sedona."""
    logger.info("=" * 60)
    logger.info("GOLD PROCESSOR (Spark) — Batimento geográfico")
    logger.info("=" * 60)

    spark = get_spark("esteira-geo-gold")

    silver_dir = Path(LOCAL_SILVER_USE_CASE)
    flooding = _read_geoparquet(spark, str(silver_dir / f"silver_{FLOODING_AREAS_FILE}"))
    citizens = _read_geoparquet(spark, str(silver_dir / f"silver_{CITIZENS_FILE}"))

    logger.info(f"Áreas carregadas: {flooding.count()}")
    logger.info(f"Cidadãos carregados: {citizens.count()}")

    # Registrar views para SQL Sedona
    flooding.createOrReplaceTempView("flooding_areas")
    citizens.createOrReplaceTempView("citizens")

    # Spatial join: cidadãos dentro de polígonos de enchente
    logger.info("Realizando spatial join com ST_Within (Sedona)...")
    joined = spark.sql("""
        SELECT
            c.*,
            f.area_id   AS matched_area_id,
            f.area_name AS matched_area_name,
            f.flood_date,
            f.severity
        FROM citizens c
        LEFT JOIN flooding_areas f
          ON ST_Within(c.geometry, f.geometry)
    """)

    # Classificar: afetado se teve match com alguma área
    classified = (
        joined
        .withColumn("affected_by_flooding", F.col("matched_area_id").isNotNull())
        # Dedup: se caiu em mais de uma área, manter afetado
        .orderBy(F.col("affected_by_flooding").desc())
        .dropDuplicates(["citizen_id"])
    )

    affected_count = classified.filter(F.col("affected_by_flooding")).count()
    unaffected_count = classified.filter(~F.col("affected_by_flooding")).count()
    logger.info(f"  Cidadãos afetados: {affected_count}")
    logger.info(f"  Cidadãos não afetados: {unaffected_count}")

    # Colunas base para os outputs
    base_cols = [c for c in [
        "citizen_id", "name", "address", "phone", "registration_date",
        "geometry", "affected_by_flooding"
    ] if c in classified.columns]

    affected_cols = base_cols + [c for c in ["matched_area_id", "matched_area_name", "flood_date", "severity"] if c in classified.columns]

    affected   = classified.filter( F.col("affected_by_flooding")).select(affected_cols)
    unaffected = classified.filter(~F.col("affected_by_flooding")).select(base_cols)
    all_summary = classified.select(base_cols)

    gold_dir = Path(LOCAL_GOLD_USE_CASE)
    _save_geoparquet(affected,    str(gold_dir / AFFECTED_CITIZENS_FILE))
    _save_geoparquet(unaffected,  str(gold_dir / UNAFFECTED_CITIZENS_FILE))
    _save_geoparquet(all_summary, str(gold_dir / ALL_CITIZENS_FILE))

    logger.info("=" * 60)
    logger.info(f"✓ Gold layer pronta (Spark)! Afetados: {affected_count} | Não afetados: {unaffected_count}")
    logger.info("=" * 60)

    return affected, unaffected, all_summary
