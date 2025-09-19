from __future__ import annotations

import os
from datetime import datetime
import yaml

from airflow import DAG
from airflow.utils.task_group import TaskGroup
from airflow.providers.docker.operators.docker import DockerOperator

def load_spec() -> dict:
    spec_path = os.environ.get("WAREHOUSE_SPEC", "configs/warehouses/acme.yaml")
    with open(spec_path, "r") as f:
        return yaml.safe_load(f)

def build_urls() -> tuple[str, str]:
    src = (
        f"postgresql+psycopg://{os.getenv('SRC_PG_USER')}:{os.getenv('SRC_PG_PASSWORD')}@"
        f"{os.getenv('SRC_PG_HOST')}:{os.getenv('SRC_PG_PORT')}/{os.getenv('SRC_PG_DB')}"
    )
    wh = (
        f"postgresql+psycopg://{os.getenv('WH_PG_USER')}:{os.getenv('WH_PG_PASSWORD')}@"
        f"{os.getenv('WH_PG_HOST')}:{os.getenv('WH_PG_PORT')}/{os.getenv('WH_PG_DB')}"
    )
    return src, wh

DEFAULT_ARGS = {"owner":"platform","retries":0}

spec = load_spec()
warehouse_name = spec["warehouse"]["name"]
bronze_jobs = spec["warehouse"].get("bronze_jobs", [])
silver_select = spec["warehouse"]["dbt"]["silver_select"]
dims_select   = spec["warehouse"]["dbt"]["dims_select"]
facts_select  = spec["warehouse"]["dbt"]["facts_select"]

DBT_IMAGE = os.environ.get("DBT_IMAGE", "registry.localhost/analytics/dbt-runner:1.0.0")
BRONZE_IMAGE = os.environ.get("BRONZE_IMAGE", "registry.localhost/etl/datakit-bronze:0.1.0")
KRB_MOUNT = os.environ.get("KRB_MOUNT", "/krb5cc/krb5cc")
SRC_URL, WH_URL = build_urls()

with DAG(
    dag_id=f"warehouse_build__{warehouse_name}",
    start_date=datetime(2025,1,1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["layer3","warehouse"],
) as dag:

    with TaskGroup(group_id="bronze") as bronze_group:
        tasks = []
        for job in bronze_jobs:
            table = job["table"]
            t = DockerOperator(
                task_id=f"land_{table}",
                image=BRONZE_IMAGE,
                api_version="auto",
                auto_remove=True,
                command=["ingest","--table",table,"--source-url",SRC_URL,"--target-url",WH_URL,"--batch-id","{{ ts_nodash }}"],
                environment={"KRB5CCNAME": f"FILE:{KRB_MOUNT}"},
                mounts=[{"source":"krb_ccache","target":"/krb5cc","type":"volume","read_only":False}],
                docker_url="unix://var/run/docker.sock",
                network_mode="l3-warehouse-net",
            )
            tasks.append(t)

    dbt_silver = DockerOperator(
        task_id="dbt_silver_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=["bash","-lc", f"dbt deps && dbt build --profiles-dir /app/profiles --select {silver_select}"],
        mounts=[{"source":"dbt_profiles","target":"/app/profiles","type":"volume","read_only":False}],
        docker_url="unix://var/run/docker.sock",
        network_mode="l3-warehouse-net",
        environment={"DBT_TARGET":"dev"}
    )

    dbt_dims = DockerOperator(
        task_id="dbt_dims_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=["bash","-lc", f"dbt deps && dbt build --profiles-dir /app/profiles --select {dims_select}"],
        mounts=[{"source":"dbt_profiles","target":"/app/profiles","type":"volume","read_only":False}],
        docker_url="unix://var/run/docker.sock",
        network_mode="l3-warehouse-net",
        environment={"DBT_TARGET":"dev"}
    )

    dbt_facts = DockerOperator(
        task_id="dbt_facts_build",
        image=DBT_IMAGE,
        api_version="auto",
        auto_remove=True,
        command=["bash","-lc", f"dbt deps && dbt build --profiles-dir /app/profiles --select {facts_select}"],
        mounts=[{"source":"dbt_profiles","target":"/app/profiles","type":"volume","read_only":False}],
        docker_url="unix://var/run/docker.sock",
        network_mode="l3-warehouse-net",
        environment={"DBT_TARGET":"dev"}
    )

    bronze_group >> dbt_silver >> dbt_dims >> dbt_facts
