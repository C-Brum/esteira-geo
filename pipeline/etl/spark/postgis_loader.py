"""
PostGIS Loader — Spark
Lê GeoParquet gold via Spark/Sedona, coleta os dados e insere no PostGIS via psycopg2.
Reutiliza create_tables e get_db_connection do loader Python.
"""

import logging
from pathlib import Path

from pyspark.sql import functions as F
from pyspark.sql.types import StringType

from etl.spark.session import get_spark
from etl.postgis_loader import get_db_connection, create_tables
from config import (
    LOCAL_GOLD_USE_CASE, LOCAL_SILVER_USE_CASE,
    USE_CASE,
    AFFECTED_CITIZENS_FILE, UNAFFECTED_CITIZENS_FILE, FLOODING_AREAS_FILE,
)

logger = logging.getLogger(__name__)


def _read_geoparquet(spark, path: str):
    return spark.read.format("geoparquet").load(path)


def _load_citizens(spark, filepath: str, affected: bool, use_case: str):
    label = "afetados" if affected else "não afetados"
    logger.info(f"Carregando cidadãos {label}...")

    df = _read_geoparquet(spark, filepath)

    # Garantir citizen_id como string e geometry como WKT
    df = (
        df.withColumn("citizen_id", F.col("citizen_id").cast(StringType()))
          .withColumn("geom_wkt", F.expr("ST_AsText(geometry)"))
    )

    rows = df.select(
        "citizen_id",
        F.col("name").cast(StringType()),
        F.col("address").cast(StringType()) if "address" in df.columns else F.lit("N/A").alias("address"),
        F.col("phone").cast(StringType()) if "phone" in df.columns else F.lit("N/A").alias("phone"),
        F.col("registration_date").cast(StringType()) if "registration_date" in df.columns else F.lit(None).cast(StringType()).alias("registration_date"),
        "geom_wkt",
    ).collect()

    table = f"{use_case}_citizens"
    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE affected_by_flooding = %s", (affected,))
    for row in rows:
        cur.execute(
            f"""INSERT INTO {table}
                (citizen_id, name, address, phone, registration_date, geometry, affected_by_flooding)
                VALUES (%s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s)
                ON CONFLICT (citizen_id) DO UPDATE SET affected_by_flooding = EXCLUDED.affected_by_flooding""",
            (
                row["citizen_id"],
                row["name"],
                row["address"] or "N/A",
                row["phone"] or "N/A",
                row["registration_date"],
                row["geom_wkt"],
                affected,
            )
        )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"✓ {len(rows)} cidadãos {label} carregados")


def _load_flooding_areas(spark, use_case: str):
    logger.info("Carregando áreas de enchente...")
    src = str(Path(LOCAL_SILVER_USE_CASE) / f"silver_{FLOODING_AREAS_FILE}")
    df = _read_geoparquet(spark, src)

    df = df.withColumn("geom_wkt", F.expr("ST_AsText(geometry)"))

    rows = df.select(
        F.col("area_name").cast(StringType()),
        F.col("flood_date").cast(StringType()),
        F.col("severity").cast(StringType()),
        F.col("affected_population").cast("int"),
        "geom_wkt",
    ).collect()

    table = f"{use_case}_flooding_areas"
    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table}")
    for row in rows:
        cur.execute(
            f"""INSERT INTO {table} (area_name, flood_date, severity, affected_population, geometry)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))""",
            (row["area_name"], row["flood_date"], row["severity"],
             row["affected_population"], row["geom_wkt"])
        )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"✓ {len(rows)} áreas de enchente carregadas")


def load_to_postgis_spark():
    logger.info("=" * 60)
    logger.info(f"POSTGIS LOADER (Spark) — Caso de uso: {USE_CASE}")
    logger.info("=" * 60)

    conn = get_db_connection()
    if not conn:
        logger.error("✗ Não foi possível conectar ao banco de dados!")
        return False

    create_tables(conn, USE_CASE)
    conn.close()

    spark = get_spark("esteira-geo-postgis")
    gold_dir = Path(LOCAL_GOLD_USE_CASE)

    _load_flooding_areas(spark, USE_CASE)
    _load_citizens(spark, str(gold_dir / AFFECTED_CITIZENS_FILE), True, USE_CASE)
    _load_citizens(spark, str(gold_dir / UNAFFECTED_CITIZENS_FILE), False, USE_CASE)

    logger.info("=" * 60)
    logger.info("✓ Dados carregados no PostGIS via Spark!")
    logger.info("=" * 60)
    return True
