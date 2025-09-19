# Quick Start Guide

Get up and running with the Astronomer Airflow Data Engineering platform in under 30 minutes.

## Prerequisites Checklist

- [ ] Docker Desktop or Docker Engine installed
- [ ] 16GB RAM (32GB recommended)
- [ ] 50GB free disk space
- [ ] Admin/sudo access for hosts file modification

## Step 1: Initial Setup (5 minutes)

```bash
# Clone the repository
git clone https://github.com/yourorg/workstation-setup.git
cd workstation-setup

# Run the automated setup
./scripts/setup.sh
```

This script will:
- Install required packages
- Set up Astronomer CLI
- Configure local hosts entries
- Create Docker networks
- Generate TLS certificates

## Step 2: Start Infrastructure (5 minutes)

```bash
# Start Traefik and Registry
cd prerequisites/traefik-registry
docker compose up -d

# Verify services are running
docker ps

# Test the registry
docker pull busybox
docker tag busybox registry.localhost/test/busybox:latest
docker push registry.localhost/test/busybox:latest
```

Access points:
- Traefik Dashboard: https://traefik.localhost
- Registry: https://registry.localhost
- Test Service: https://whoami.localhost

## Step 3: Build Images (10 minutes)

```bash
# Build all required Docker images
./scripts/build-all.sh
```

This builds:
- Platform base image (Airflow Runtime)
- dbt runner
- Datakit runners (Postgres, SQL Server, Spark)
- Bronze data ingestion containers

## Step 4: Run the Example (5 minutes)

```bash
# Navigate to the example
cd examples/all-in-one

# Start Airflow
astro dev start

# Wait for services to be healthy (2-3 minutes)
astro dev ps
```

Access Airflow UI:
- URL: https://airflow-dev.customer.localhost
- Username: admin
- Password: admin

## Step 5: Trigger a Pipeline

1. Open the Airflow UI
2. Find the DAG: `pagila_bronze_silver_gold`
3. Click the play button to trigger
4. Watch the pipeline execute:
   - Bronze: Raw data ingestion
   - Silver: Business entity modeling
   - Gold: Dimensional modeling and facts

## Verify Data

```bash
# Check that data landed in all layers
psql "postgresql://postgres:postgres@localhost:5432/pagila_wh" \
  -c "SELECT 'Bronze:', COUNT(*) FROM bronze.br_film
      UNION ALL SELECT 'Silver:', COUNT(*) FROM pagila_silver.film
      UNION ALL SELECT 'Gold:', COUNT(*) FROM gold_rental.fact_rental;"
```

## What's Next?

### For Developers
1. Explore the [all-in-one example](../examples/all-in-one/)
2. Review [DAG patterns](../layer3-warehouses/dags/)
3. Create your own datakits in [layer2-datakits](../layer2-datakits/)

### For Architects
1. Read the [philosophy documentation](philosophy/)
2. Understand the [journey to production](journey/)
3. Review [warehouse configurations](../layer3-warehouses/configs/)

### Common Tasks
- **Add a new data source**: Create a datakit in layer2-datakits/
- **Modify transformations**: Edit dbt projects in layer2-dbt-projects/
- **Configure a new tenant**: Add YAML in layer3-warehouses/configs/warehouses/
- **Customize Airflow**: Modify layer1-platform/airflow_settings/

## Troubleshooting

### Docker Issues
```bash
# Reset Docker state
docker system prune -a
docker volume prune

# Restart Docker Desktop
# Then re-run setup
```

### Certificate Issues
```bash
# Regenerate certificates
cd prerequisites/certificates
rm -rf certs/*
# Re-run setup.sh
```

### Port Conflicts
```bash
# Check for conflicts
lsof -i :80
lsof -i :443
lsof -i :5432
lsof -i :8080

# Stop conflicting services or adjust ports in docker-compose files
```

### Airflow Won't Start
```bash
# Clean Airflow state
cd examples/all-in-one
astro dev kill
astro dev start --no-cache
```

## Support

- Check [documentation](../docs/)
- Review [examples](../examples/)
- Consult architecture team for design questions