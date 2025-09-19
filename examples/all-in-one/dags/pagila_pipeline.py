from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator

DEFAULT_ARGS = {
    "owner": "data-platform",
    "depends_on_past": False,
    "retries": 0,
}

# Images from the local registry
DBT_IMAGE = os.environ.get("DBT_IMAGE", "registry.localhost/analytics/dbt-runner:1.0.0")
BRONZE_IMAGE = os.environ.get("BRONZE_IMAGE", "registry.localhost/etl/datakit-bronze:0.1.0")

# Shared Kerberos cache (from sidecar) mount target
KRB_MOUNT = os.environ.get("KRB_MOUNT", "/krb5cc/krb5cc")

SRC_URL = (
    f"postgresql+psycopg://{os.getenv('SRC_PG_USER')}:{os.getenv('SRC_PG_PASSWORD')}@"
    f"{os.getenv('SRC_PG_HOST')}:{os.getenv('SRC_PG_PORT')}/{os.getenv('SRC_PG_DB')}"
)
WH_URL = (
    f"postgresql+psycopg://{os.getenv('WH_PG_USER')}:{os.getenv('WH_PG_PASSWORD')}@"
    f"{os.getenv('WH_PG_HOST')}:{os.getenv('WH_PG_PORT')}/{os.getenv('WH_PG_DB')}"
)

with DAG(
    dag_id="pagila_bronze_silver_gold",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["demo","bronze","silver","gold"],
) as dag:

    # 1) Bronze: land a few tables via datakit (loop condensed to one example task)
    bronze_film = DockerOperator(
        task_id="bronze_film",
        image=BRONZE_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=[
            "ingest",
            "--table","film",
            "--source-url", SRC_URL,
            "--target-url", WH_URL,
            "--batch-id","{{ ds_nodash }}"
        ],
        # Kerberos example env (point to shared cache)
        environment={
            "KRB5CCNAME": f"FILE:{KRB_MOUNT}",
        },
        mounts=[
            # mount the shared kerberos cache read-only
            {"source": "krb_ccache", "target": "/krb5cc", "type": "volume", "read_only": False},
        ],
        docker_url="unix://var/run/docker.sock",
        network_mode="airflow-obsv-net",
    )

    # 2) Silver build (dbt) – build only selected models for speed
    dbt_silver = DockerOperator(
        task_id="dbt_silver_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=[
            "bash","-lc",
            "dbt deps && dbt build --profiles-dir /app/profiles --select pagila_silver"
        ],
        # Mount a local profiles dir if you maintain it on the host; otherwise bake into image
        mounts=[
            {"source": "dbt_profiles", "target": "/app/profiles", "type": "volume", "read_only": False},
        ],
        docker_url="unix://var/run/docker.sock",
        network_mode="airflow-obsv-net",
        environment={
            "DBT_TARGET":"dev"
        }
    )

    # 3) Dims + 4) Fact (dbt) – same runner image, different selector
    dbt_dims = DockerOperator(
        task_id="dbt_dims_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=[
            "bash","-lc",
            "dbt deps && dbt build --profiles-dir /app/profiles --select gold_mart"
        ],
        mounts=[{"source":"dbt_profiles","target":"/app/profiles","type":"volume","read_only":False}],
        docker_url="unix://var/run/docker.sock",
        network_mode="airflow-obsv-net",
        environment={"DBT_TARGET":"dev"}
    )

    dbt_fact = DockerOperator(
        task_id="dbt_fact_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=[
            "bash","-lc",
            "dbt deps && dbt build --profiles-dir /app/profiles --select gold_rental"
        ],
        mounts=[{"source":"dbt_profiles","target":"/app/profiles","type":"volume","read_only":False}],
        docker_url="unix://var/run/docker.sock",
        network_mode="airflow-obsv-net",
        environment={"DBT_TARGET":"dev"}
    )

    bronze_film >> dbt_silver >> dbt_dims >> dbt_fact
