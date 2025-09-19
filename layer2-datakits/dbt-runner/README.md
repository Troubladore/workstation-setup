# dbt-runner

A minimal container for running dbt (local dev with DockerOperator, or KPO in prod).

## Build
```bash
docker build -t registry.localhost/analytics/dbt-runner:1.0.0 .
```

## Usage
Mount a `profiles` directory or set env vars as needed:
```bash
docker run --rm -v $PWD/profiles:/app/profiles \
  -e DBT_TARGET=dev \
  registry.localhost/analytics/dbt-runner:1.0.0 \
  bash -lc "dbt deps && dbt build --profiles-dir /app/profiles"
```

## Compose snippet (Airflow worker image mounting Docker socket for local dev)
```yaml
services:
  dbt-runner:
    image: registry.localhost/analytics/dbt-runner:1.0.0
    environment:
      DBT_TARGET: "dev"
    volumes:
      - ./profiles:/app/profiles:ro
      - ./:/workspace  # optionally mount your project
    working_dir: /workspace
```

In Airflow, use the same image/command via your `run_datakit(...)` adapter.
