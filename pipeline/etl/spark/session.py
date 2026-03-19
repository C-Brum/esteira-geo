"""
Spark Session Factory — Esteira Geo
Inicializa SparkSession com Apache Sedona e suporte a S3A (MinIO/AWS).
"""

import os
from pyspark.sql import SparkSession
from sedona.spark import SedonaContext


def get_spark(app_name: str = "esteira-geo") -> SparkSession:
    """Cria SparkSession com Sedona e S3A configurados."""

    endpoint = os.getenv("AWS_ENDPOINT_URL", "")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin123")

    builder = (
        SparkSession.builder.appName(app_name)
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator")
        .config("spark.sql.extensions", "org.apache.sedona.viz.sql.SedonaVizExtensions,org.apache.sedona.sql.SedonaSqlExtensions")
    )

    # S3A — MinIO ou AWS
    if endpoint:
        builder = (
            builder
            .config("spark.hadoop.fs.s3a.endpoint", endpoint)
            .config("spark.hadoop.fs.s3a.path.style.access", "true")
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        )

    builder = (
        builder
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.parquet.enableVectorizedReader", "false")
    )

    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return SedonaContext.create(spark)
