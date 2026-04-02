FROM apache/airflow:2.9.1-python3.12

USER root
RUN apt-get update && apt-get install -y \
    gdal-bin libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
RUN pip install --no-cache-dir \
    "geopandas>=0.13.0" \
    "shapely>=2.0.0" \
    "pyproj>=3.4.0" \
    "psycopg2-binary>=2.9.0" \
    "boto3>=1.28.0" \
    "pyarrow>=12.0.0" \
    "apache-airflow-providers-amazon>=8.0.0"

ENV PYTHONPATH=/opt/airflow/pipeline
ENV AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
ENV AIRFLOW__CORE__LOAD_EXAMPLES=false
