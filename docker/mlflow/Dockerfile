FROM ghcr.io/mlflow/mlflow:v2.18.0

RUN pip install --no-cache-dir psycopg2-binary

COPY scripts/build_database_url.py /scripts/build_database_url.py
