# Troubleshooting Guide

A comprehensive guide to diagnosing and resolving common issues in the Astronomer Airflow data engineering platform.

## 🚨 Quick Diagnostics

### **System Health Check**

Run this first when encountering any issues:

```bash
# Check all services
./scripts/verify.sh

# Check specific components
docker ps                                    # Running containers
docker network ls | grep edge                # Network status
curl -k https://registry.localhost/v2/       # Registry health
curl -k https://traefik.localhost/dashboard  # Traefik status
astro dev ps                                  # Airflow components
```

## 🔴 Critical Issues

### **Issue: Nothing is Working**

**Symptoms:**
- All services are down
- Can't access any URLs
- Docker commands fail

**Solutions:**

```bash
# 1. Restart Docker
# On Mac/Windows: Restart Docker Desktop
# On Linux:
sudo systemctl restart docker

# 2. Clean up everything and restart
docker system prune -a --volumes
docker network create edge
cd prerequisites/traefik-registry
docker compose up -d

# 3. Rebuild from scratch
./scripts/setup.sh
./scripts/build-all.sh
```

### **Issue: Out of Disk Space**

**Symptoms:**
- "No space left on device" errors
- Containers crashing
- Build failures

**Solutions:**

```bash
# Check disk usage
df -h
docker system df

# Clean up Docker resources
docker system prune -a --volumes
docker builder prune

# Remove old images
docker images | grep "months ago" | awk '{print $3}' | xargs docker rmi

# Clear Airflow logs
cd examples/all-in-one
find logs -name "*.log" -mtime +7 -delete
```

## 🐳 Docker Issues

### **Issue: Cannot Connect to Docker Daemon**

**Error:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solutions:**

```bash
# Check Docker is running
systemctl status docker

# Start Docker
sudo systemctl start docker

# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker

# Fix socket permissions
sudo chmod 666 /var/run/docker.sock
```

### **Issue: Container Network Issues**

**Symptoms:**
- Containers can't communicate
- "No route to host" errors
- Registry unreachable

**Solutions:**

```bash
# Recreate network
docker network rm edge
docker network create edge

# Restart containers with correct network
docker compose down
docker compose up -d

# Verify network connectivity
docker run --rm --network edge alpine ping -c 1 registry.localhost
```

### **Issue: Registry Push/Pull Failures**

**Error:**
```
Error response from daemon: Get https://registry.localhost/v2/: x509: certificate signed by unknown authority
```

**Solutions:**

```bash
# Option 1: Configure Docker to trust certificate
sudo mkdir -p /etc/docker/certs.d/registry.localhost
sudo cp prerequisites/certificates/certs/cert.pem \
  /etc/docker/certs.d/registry.localhost/ca.crt
sudo systemctl restart docker

# Option 2: Use insecure registry (development only)
# Edit /etc/docker/daemon.json
{
  "insecure-registries": ["registry.localhost:5000"]
}
sudo systemctl restart docker

# Test registry
docker pull busybox
docker tag busybox registry.localhost/test:latest
docker push registry.localhost/test:latest
```

## ✈️ Airflow Issues

### **Issue: DAG Not Appearing in UI**

**Symptoms:**
- DAG file exists but not visible in UI
- No import errors in logs

**Solutions:**

```bash
# 1. Check DAG syntax
python dags/your_dag.py

# 2. Check for import errors
astro dev run dags list-import-errors

# 3. Refresh DAGs
astro dev run dags reserialize

# 4. Restart scheduler
astro dev restart

# 5. Check DAG folder permissions
ls -la dags/
chmod 644 dags/*.py
```

### **Issue: Task Stuck in Running State**

**Symptoms:**
- Task shows "running" but no progress
- No logs being generated

**Solutions:**

```bash
# 1. Check worker logs
astro dev logs -f --worker

# 2. Clear task state
astro dev run tasks clear <dag_id> -t <task_id>

# 3. Check for deadlocks
astro dev run dags show <dag_id>

# 4. Restart workers
docker restart $(docker ps -q --filter "name=worker")
```

### **Issue: Database Connection Errors**

**Error:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solutions:**

```bash
# 1. Verify connection settings
astro dev run connections get postgres_default

# 2. Test connection
astro dev run connections test postgres_default

# 3. Update connection
astro dev run connections add postgres_default \
  --conn-type postgres \
  --conn-host host.docker.internal \
  --conn-login postgres \
  --conn-password postgres \
  --conn-schema airflow \
  --conn-port 5432

# 4. For WSL2 users, use correct host
# Instead of localhost, use:
# - host.docker.internal (from container)
# - $(hostname).local (from WSL2)
```

### **Issue: Scheduler Not Picking Up Tasks**

**Symptoms:**
- Tasks queued but not running
- Scheduler logs show no activity

**Solutions:**

```bash
# 1. Check scheduler health
astro dev logs --scheduler | tail -50

# 2. Check for DAG errors
astro dev run dags test <dag_id>

# 3. Reset scheduler state
astro dev stop
rm -rf .astro/airflow.db
astro dev start

# 4. Check resource limits
docker stats --no-stream
```

## 🔄 dbt Issues

### **Issue: dbt Models Failing**

**Error:**
```
Database Error in model my_model
  relation "source_table" does not exist
```

**Solutions:**

```bash
# 1. Check source data exists
psql $WAREHOUSE_DB -c "\dt bronze.*"

# 2. Run dependencies first
dbt run --select +my_model

# 3. Full refresh
dbt run --select my_model --full-refresh

# 4. Debug compiled SQL
dbt compile --select my_model
cat target/compiled/project/models/my_model.sql
```

### **Issue: dbt Connection Problems**

**Error:**
```
Could not connect to database
```

**Solutions:**

```bash
# 1. Test connection
dbt debug

# 2. Check profiles.yml
cat ~/.dbt/profiles.yml

# 3. Use environment variables
export DBT_HOST=localhost
export DBT_PORT=5432
export DBT_USER=postgres
export DBT_PASSWORD=postgres
export DBT_DATABASE=warehouse
export DBT_SCHEMA=public

# 4. For Docker, mount profiles
docker run -v ~/.dbt:/root/.dbt \
  registry.localhost/analytics/dbt-runner:1.0.0 \
  dbt debug
```

## 🔐 Authentication Issues

### **Issue: Kerberos Authentication Failing**

**Error:**
```
kinit: Cannot contact any KDC for realm 'EXAMPLE.COM'
```

**Solutions:**

```bash
# 1. Check krb5.conf
cat /etc/krb5.conf

# 2. Test kinit manually
kinit -kt /path/to/keytab principal@REALM

# 3. Check ticket cache
klist

# 4. For containers, mount keytab
docker run -v /path/to/keytab:/keytab:ro \
  -e KRB5_CLIENT_KTNAME=/keytab \
  registry.localhost/etl/sqlserver-runner:0.1.0
```

### **Issue: Certificate Errors**

**Error:**
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solutions:**

```bash
# 1. Regenerate certificates
cd prerequisites/certificates
rm -rf certs/*
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/key.pem \
  -out certs/cert.pem \
  -days 365 \
  -subj "/CN=*.localhost"

# 2. Update hosts file
echo "127.0.0.1 registry.localhost" | sudo tee -a /etc/hosts

# 3. Trust certificate (Mac)
sudo security add-trusted-cert -d -r trustRoot \
  -k /Library/Keychains/System.keychain \
  prerequisites/certificates/certs/cert.pem

# 4. Trust certificate (Linux)
sudo cp prerequisites/certificates/certs/cert.pem \
  /usr/local/share/ca-certificates/localhost.crt
sudo update-ca-certificates
```

## 🚀 Performance Issues

### **Issue: Slow DAG Execution**

**Symptoms:**
- Tasks taking longer than expected
- High resource usage
- Timeouts

**Solutions:**

```bash
# 1. Check resource usage
docker stats

# 2. Increase resources (Docker Desktop)
# Settings > Resources > Increase CPUs and Memory

# 3. Optimize parallelism
# In airflow.cfg or environment variables:
export AIRFLOW__CORE__PARALLELISM=32
export AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG=16

# 4. Use connection pooling
export AIRFLOW__DATABASE__SQL_ALCHEMY_POOL_SIZE=10
export AIRFLOW__DATABASE__SQL_ALCHEMY_MAX_OVERFLOW=20
```

### **Issue: Memory Errors**

**Error:**
```
Container killed due to memory limit
```

**Solutions:**

```bash
# 1. Increase container memory limits
# In docker-compose.yml:
services:
  worker:
    mem_limit: 4g
    memswap_limit: 4g

# 2. Optimize datakit memory usage
# Process in chunks:
for chunk in pd.read_sql(query, con, chunksize=10000):
    process(chunk)

# 3. Clear caches
docker system prune -a
```

## 🗂️ Data Issues

### **Issue: Data Not Loading to Bronze**

**Symptoms:**
- Extraction tasks succeed but no data in tables
- Row counts are zero

**Solutions:**

```bash
# 1. Check source connectivity
docker run --rm registry.localhost/etl/postgres-runner:0.1.0 \
  python -c "import psycopg2; print('Connected')"

# 2. Verify credentials
echo $SOURCE_DATABASE_URL
echo $WAREHOUSE_DATABASE_URL

# 3. Check table permissions
psql $SOURCE_DB -c "\dp source_table"

# 4. Enable verbose logging
docker run -e LOG_LEVEL=DEBUG \
  registry.localhost/etl/postgres-runner:0.1.0
```

### **Issue: Incorrect Data in Silver/Gold**

**Symptoms:**
- Transformations producing wrong results
- Duplicates or missing records

**Solutions:**

```sql
-- 1. Check source data quality
SELECT COUNT(*), COUNT(DISTINCT id)
FROM bronze.br_table;

-- 2. Verify transformation logic
-- Look at intermediate CTEs
WITH source AS (
    SELECT * FROM bronze.br_table
),
transformed AS (
    -- Your transformation
)
SELECT * FROM transformed LIMIT 10;

-- 3. Check for race conditions
-- Add explicit ordering
ORDER BY created_at, id;

-- 4. Full refresh
dbt run --select model_name --full-refresh
```

## 🛠️ Development Environment Issues

### **Issue: WSL2 Specific Problems**

**Symptoms:**
- Slow file access
- Network connectivity issues
- Docker performance problems

**Solutions:**

```bash
# 1. Use WSL2 filesystem (not /mnt/c)
cd ~
git clone <repo>

# 2. Configure WSL2 memory
# Create .wslconfig in Windows user directory:
[wsl2]
memory=8GB
processors=4
swap=2GB

# 3. Fix DNS issues
sudo rm /etc/resolv.conf
sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'

# 4. Restart WSL2
wsl --shutdown
# Then reopen WSL2
```

### **Issue: VS Code Integration Problems**

**Symptoms:**
- Can't connect to Dev Container
- Extensions not working

**Solutions:**

```bash
# 1. Rebuild Dev Container
# In VS Code: Cmd+Shift+P > "Rebuild Container"

# 2. Clear VS Code server
rm -rf ~/.vscode-server

# 3. Check Docker context
docker context ls
docker context use default

# 4. Update VS Code and extensions
# Check for updates in VS Code
```

## 📊 Monitoring and Debugging Tools

### **Useful Commands for Debugging**

```bash
# Container inspection
docker inspect <container_id>
docker logs --tail 100 -f <container_id>
docker exec -it <container_id> /bin/bash

# Network debugging
docker network inspect edge
netstat -tulpn | grep LISTEN
nslookup registry.localhost

# Process monitoring
htop
iotop
docker stats

# Database inspection
psql $DB -c "\l"                    # List databases
psql $DB -c "\dt *.*"               # List all tables
psql $DB -c "\d+ schema.table"      # Describe table
psql $DB -c "TABLE schema.table LIMIT 5"  # Sample data

# Airflow debugging
airflow dags list
airflow tasks list <dag_id>
airflow dags show <dag_id>
airflow dags test <dag_id> <date>
```

## 💡 Prevention Tips

### **Best Practices to Avoid Issues**

1. **Regular Maintenance**
   - Clean up Docker resources weekly
   - Update dependencies monthly
   - Archive old logs

2. **Resource Management**
   - Monitor disk space
   - Set resource limits
   - Use connection pooling

3. **Development Practices**
   - Test locally before deploying
   - Use version control
   - Document changes

4. **Monitoring Setup**
   - Set up alerts
   - Monitor key metrics
   - Keep logs accessible

## 🔗 Related Documentation

- **[Architecture Overview](architecture-overview.md)** - System design
- **[Developer Workflows](developer-workflows.md)** - Development practices
- **[Performance & Scaling](performance-scaling.md)** - Optimization
- **[Quick Start Guide](QUICK_START.md)** - Initial setup

## 📞 Getting Help

If you can't resolve an issue:

1. **Check logs** - Most answers are in the logs
2. **Search documentation** - Use Ctrl+F liberally
3. **Reproduce minimally** - Isolate the problem
4. **Document clearly** - Include error messages and steps
5. **Contact platform team** - With detailed information

---

*Remember: Every problem has a solution. Stay calm and debug systematically.*