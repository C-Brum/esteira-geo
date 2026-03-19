"""
Silver Processor — Spark + Sedona
Equivalente ao silver_processor.py, usando DataFrames Spark com geometrias Sedona.

Entrada : GeoParquet + CSV + GeoJSON em /data/bronze/<use_case>/
Saída   : GeoParquet em /data/silver/<use_case>/silver_*.parquet
"""

import logging
import os
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import StringType
from sedona.sql.types import GeometryType

from etl.spark.session import get_spark
from config import (
    LOCAL_BRONZE_USE_CASE, LOCAL_SILVER_USE_CASE,
    FLOODING_AREAS_FILE, CITIZENS_FILE,
)

logger = logging.getLogger(__name__)


def _read_geoparquet(spark, path: str):
    """Lê GeoParquet preservando coluna geometry como tipo Sedona."""
    return spark.read.format("geoparquet").load(path)


def _save_geoparquet(df, path: str):
    """Salva DataFrame como GeoParquet em arquivo único (compatível com GeoPandas)."""
    import shutil
    import glob

    path = Path(path)
    tmp = Path("/tmp") / (path.name + "._spark_tmp")

    # Limpar tmp anterior
    if tmp.exists():
        shutil.rmtree(str(tmp))

    # Salvar em /tmp (fora dos volumes compartilhados)
    df.coalesce(1).write.format("geoparquet").mode("overwrite").save(str(tmp))

    # Mover part file para o destino final como arquivo único
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

    logger.info(f"✓ Salvo Silver (Spark): {path}")


def process_flooding_areas(spark) -> "DataFrame":
    src = str(Path(LOCAL_BRONZE_USE_CASE) / FLOODING_AREAS_FILE)
    logger.info(f"Carregando áreas de enchente: {src}")
    df = _read_geoparquet(spark, src)
    df = (
        df.withColumn("area_id", F.col("area_id").cast("long"))
          .withColumn("affected_population", F.col("affected_population").cast("long"))
          .withColumn("flood_date", F.to_date(F.col("flood_date").cast(StringType())))
          .dropDuplicates(["area_id"])
    )
    logger.info(f"✓ Áreas normalizadas: {df.count()} registros")
    return df


def process_citizens_bronze(spark) -> "DataFrame":
    """Normaliza o parquet sintético de cidadãos gerado pelo bronze_loader."""
    src = str(Path(LOCAL_BRONZE_USE_CASE) / CITIZENS_FILE)
    logger.info(f"Carregando cidadãos bronze: {src}")
    df = _read_geoparquet(spark, src)
    df = _normalize_citizens(df)
    logger.info(f"✓ Cidadãos bronze normalizados: {df.count()} registros")
    return df


def _normalize_citizens(df) -> "DataFrame":
    """Normaliza tipos e colunas de um DataFrame de cidadãos."""
    # registered_date → registration_date
    if "registered_date" in df.columns and "registration_date" not in df.columns:
        df = df.withColumnRenamed("registered_date", "registration_date")
    if "registration_date" in df.columns:
        df = df.withColumn("registration_date", F.to_date(F.col("registration_date").cast(StringType())))

    df = df.withColumn("citizen_id", F.col("citizen_id").cast(StringType()))

    if "document_number" in df.columns:
        df = df.withColumn("document_number", F.col("document_number").cast(StringType()))

    if "name" in df.columns:
        df = df.withColumn("name", F.trim(F.col("name")))

    return df.dropDuplicates(["citizen_id"])


def consolidate_external_citizens(spark) -> "DataFrame":
    """
    Lê todos os parquets externos (sem prefixo silver_) do diretório silver
    gerados pelo csv_geojson_converter e consolida em um único DataFrame.
    """
    silver_dir = Path(LOCAL_SILVER_USE_CASE)
    frames = []

    for fp in sorted(silver_dir.glob("*.parquet")):
        if fp.name.startswith("silver_") or fp.name in {FLOODING_AREAS_FILE, CITIZENS_FILE}:
            continue
        try:
            df = _read_geoparquet(spark, str(fp))
            df = _normalize_citizens(df)
            frames.append(df)
            logger.info(f"✓ Consolidando {fp.name}: {df.count()} registros")
        except Exception as e:
            logger.warning(f"⚠ Erro ao consolidar {fp.name}: {e}")

    if not frames:
        return None

    result = frames[0]
    for f in frames[1:]:
        result = result.unionByName(f, allowMissingColumns=True)
    return result.dropDuplicates(["citizen_id"])


def process_silver_spark():
    """Orquestrador Silver com Spark+Sedona."""
    logger.info("=" * 60)
    logger.info("SILVER PROCESSOR (Spark) — Normalizando dados")
    logger.info("=" * 60)

    spark = get_spark("esteira-geo-silver")

    # Áreas de enchente
    flooding = process_flooding_areas(spark)
    _save_geoparquet(flooding, str(Path(LOCAL_SILVER_USE_CASE) / f"silver_{FLOODING_AREAS_FILE}"))

    # Cidadãos sintéticos
    citizens = process_citizens_bronze(spark)

    # Consolidar externos
    external = consolidate_external_citizens(spark)
    if external:
        citizens = citizens.unionByName(external, allowMissingColumns=True)
        citizens = citizens.dropDuplicates(["citizen_id"])

    total = citizens.count()
    logger.info(f"✓ Total consolidado (Spark): {total} cidadãos")

    _save_geoparquet(citizens, str(Path(LOCAL_SILVER_USE_CASE) / f"silver_{CITIZENS_FILE}"))

    logger.info("=" * 60)
    logger.info("✓ Silver layer pronta (Spark)!")
    logger.info("=" * 60)

    return flooding, citizens
