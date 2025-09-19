# Layer 3 — Warehouse Orchestrator (Tenant-Aware)

Assemble **datakits (Bronze)** and **dbt (Silver/Gold)** into **per-customer warehouses** by describing what to include in a YAML spec.
Layer 2 stays orchestration-agnostic; Layer 3 adapts specs into Airflow tasks.

## Why this matters
- **Pick-and-choose**: each tenant gets just the sources and topics they need.
- **Parity**: same runner images as production (DockerOperator here; KPO in clusters).
- **Kerberos sidecar**: dev uses a shared cache volume; prod uses a pod volume—same concept.

## Setup
1. Ensure Traefik+registry are running and TLS trusted.
2. Ensure Postgres has `pagila` and `pagila_wh`.
3. Push runner images:
   - `registry.localhost/etl/datakit-bronze:0.1.0`
   - `registry.localhost/analytics/dbt-runner:1.0.0`
4. Prepare a dbt profiles file mounted to the `dbt_profiles` volume.

## Configure
```bash
cp include/.env.example .env
# Optionally switch the tenant spec:
# export WAREHOUSE_SPEC=configs/warehouses/globex.yaml
```

## Run
```bash
docker network create edge || true
astro dev start
```

Visit **https://airflow-dev.customer.localhost** and trigger **`warehouse_build__acme_wh`**.

## Verify
```bash
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt bronze.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt pagila_silver.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt gold_mart.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt gold_rental.*"
```

## Create new tenant
Copy one of the files in `configs/warehouses/` and list the `bronze_jobs` + dbt selectors for Silver/Gold.

## Production note
Switch **DockerOperator → KubernetesPodOperator**; keep images/args the same. Mount Kerberos cache as a pod volume and run an init/sidecar for kinit.
