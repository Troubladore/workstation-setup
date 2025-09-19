# Airflow Local Observability (Astronomer Runtime 3.0-10)

**Purpose:** give developers a production-like experience on laptop:
- Astronomer-based Airflow + UI behind Traefik at `https://airflow-dev.customer.localhost`
- Tasks run in **DockerOperator** using the **same runner images** you’ll use with **KPO** in clusters
- Optional **Kerberos sidecar** writes TGT to a shared cache volume that tasks consume

## Prereqs (already covered elsewhere)
- Traefik bundle is up (`edge` external network exists, certs trusted)
- Local registry is reachable at `registry.localhost`
- Runner images pushed: 
  - `registry.localhost/analytics/dbt-runner:1.0.0`
  - `registry.localhost/etl/datakit-bronze:0.1.0`
- Local Postgres with `pagila` (source) and `pagila_wh` (warehouse)

## One-time setup
```bash
cp include/.env.example .env  # adjust SRC/WH credentials if needed
# Create external network if your Traefik bundle didn't already:
docker network create edge || true
```

## Start Airflow (via Astro CLI)
```bash
astro dev start
```

- The project includes `docker-compose.override.yml` with **Traefik labels** bound to `webserver` and an external `edge` network.
- Open **https://airflow-dev.customer.localhost** → you should see the Airflow UI.
- If TLS/browser warning appears, ensure your IT-provided mkcert CA is trusted.

## (Optional) Kerberos sidecar
- Put your dev keytab in `include/dev.keytab` and set `KRB_PRINCIPAL`/`KRB_REALM` in `.env`.
- The `krb-sidecar` service will refresh a TGT hourly and write to the `krb_ccache` volume.
- Tasks read the cache via `KRB5CCNAME=FILE:/krb5cc/krb5cc`.

> In production, the same principle applies with KPO and an init/sidecar container; here we mimic it with a long-lived helper.

## Prepare dbt profiles
If you want to mount dbt profiles through the included `dbt_profiles` volume:
```bash
docker run --rm -v airflow-local-observability_dbt_profiles:/dst busybox sh -c 'mkdir -p /dst && echo "pagila: ..." > /dst/profiles.yml'
# or use docker cp to place your real file at /dst/profiles.yml
```

## Run the pipeline
In the Airflow UI:
1. Open DAG **`pagila_bronze_silver_gold`**
2. Trigger **Run**

Watch the task graph:
- **bronze_film** runs the **datakit** container and writes to `bronze.br_film` in `pagila_wh`
- **dbt_silver_build** builds `pagila_silver.*`
- **dbt_dims_build** builds `gold_mart.dim_*`
- **dbt_fact_build** builds `gold_rental.fact_rental`

## Verify data landed
From your shell:
```bash
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt bronze.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt pagila_silver.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt gold_mart.*"
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" -c "\dt gold_rental.*"
```

## Notes on fidelity
- **Operators**: Locally we use **DockerOperator** with the exact images that prod runs under **KPO**.
- **Sidecar**: Kerberos ticket cache is provided via a **shared volume** in dev; in prod, this is a pod volume.
- **Routing**: `.localhost` mirrors `.myco.com` patterns so URLs and operator behavior feel the same.
