# Developer Workflows

Practical, day-to-day workflows for data engineers building pipelines on our Astronomer Airflow platform. From morning standup to production deployment.

## 🎯 Developer Daily Routine

### **Morning Startup Checklist**

```bash
# 1. Update your local environment
cd ~/workstation-setup
git pull origin main

# 2. Start infrastructure services
cd prerequisites/traefik-registry
docker compose up -d

# 3. Verify services are healthy
docker ps
curl -k https://registry.localhost/v2/_catalog

# 4. Start Airflow
cd ../../examples/all-in-one
astro dev start

# 5. Check Airflow UI
open https://airflow-dev.customer.localhost
```

### **Before You Start Coding**

1. **Check for updates**: Pull latest platform changes
2. **Review tickets**: Understand requirements completely
3. **Check data sources**: Verify access and schemas
4. **Plan your approach**: Bronze, Silver, or Gold changes?

## 🔄 Common Development Workflows

### **Workflow 1: Adding a New Data Source**

**Scenario**: You need to ingest data from a new SQL Server database.

```bash
# Step 1: Create a new datakit
cd layer2-datakits
mkdir new-source-datakit
cd new-source-datakit

# Step 2: Create the datakit structure
cat > pyproject.toml << 'EOF'
[project]
name = "datakit-new-source"
version = "0.1.0"
dependencies = [
    "pandas>=2.0.0",
    "sqlalchemy>=2.0.0",
    "pymssql>=2.3.0",
    "python-dotenv>=1.0.0"
]
EOF

# Step 3: Create the extraction logic
mkdir datakit_new_source
cat > datakit_new_source/__init__.py << 'EOF'
"""New Source Data Extraction Kit."""
from .extract import extract_table

__all__ = ["extract_table"]
EOF

cat > datakit_new_source/extract.py << 'EOF'
import os
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

def extract_table(table_name: str, target_schema: str = "bronze"):
    """Extract table from source to bronze layer."""

    # Source connection
    source_conn_str = os.getenv("SOURCE_DATABASE_URL")
    source_engine = create_engine(source_conn_str)

    # Target connection
    target_conn_str = os.getenv("WAREHOUSE_DATABASE_URL")
    target_engine = create_engine(target_conn_str)

    # Extract data
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, source_engine)

    # Add metadata
    df['_bronze_loaded_at'] = datetime.now()
    df['_bronze_source'] = 'new_source'

    # Load to bronze
    df.to_sql(
        name=f"br_{table_name}",
        con=target_engine,
        schema=target_schema,
        if_exists='replace',
        index=False
    )

    print(f"✅ Loaded {len(df)} rows to {target_schema}.br_{table_name}")

    return len(df)
EOF

# Step 4: Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e .

COPY datakit_new_source/ ./datakit_new_source/

ENTRYPOINT ["python", "-m", "datakit_new_source.extract"]
EOF

# Step 5: Build and test locally
docker build -t registry.localhost/etl/new-source:0.1.0 .

# Test the extraction
docker run --rm \
  -e SOURCE_DATABASE_URL="mssql+pymssql://user:pass@host:1433/source" \
  -e WAREHOUSE_DATABASE_URL="postgresql://user:pass@host:5432/warehouse" \
  registry.localhost/etl/new-source:0.1.0 \
  customers

# Step 6: Push to registry
docker push registry.localhost/etl/new-source:0.1.0
```

### **Workflow 2: Creating a Silver Layer Transformation**

**Scenario**: Clean and standardize the raw customer data.

```bash
# Step 1: Navigate to silver dbt project
cd layer2-dbt-projects/silver-core

# Step 2: Create new model
cat > models/silver/new_source_customers.sql << 'EOF'
{{
  config(
    materialized='incremental',
    unique_key='customer_id',
    on_schema_change='sync_all_columns'
  )
}}

WITH source AS (
    SELECT * FROM {{ source('bronze', 'br_customers') }}
    {% if is_incremental() %}
    WHERE _bronze_loaded_at > (SELECT MAX(silver_processed_at) FROM {{ this }})
    {% endif %}
),

cleaned AS (
    SELECT
        -- IDs
        CAST(customer_id AS INTEGER) as customer_id,

        -- Clean text fields
        TRIM(UPPER(customer_code)) as customer_code,
        INITCAP(TRIM(customer_name)) as customer_name,
        LOWER(TRIM(email)) as email,

        -- Standardize phone
        REGEXP_REPLACE(phone, '[^0-9]', '') as phone_clean,

        -- Parse dates
        TO_DATE(created_date, 'YYYY-MM-DD') as created_date,
        TO_DATE(modified_date, 'YYYY-MM-DD') as modified_date,

        -- Decode status
        CASE status_code
            WHEN 'A' THEN 'Active'
            WHEN 'I' THEN 'Inactive'
            WHEN 'P' THEN 'Pending'
            ELSE 'Unknown'
        END as status,

        -- Add derived fields
        CASE
            WHEN email IS NOT NULL THEN TRUE
            ELSE FALSE
        END as has_email,

        -- Metadata
        _bronze_loaded_at as bronze_loaded_at,
        CURRENT_TIMESTAMP as silver_processed_at

    FROM source
    WHERE customer_id IS NOT NULL
      AND customer_name IS NOT NULL
)

SELECT * FROM cleaned
EOF

# Step 3: Add to schema.yml
cat >> models/silver/schema.yml << 'EOF'

  - name: new_source_customers
    description: Cleaned customer data from new source system
    columns:
      - name: customer_id
        description: Unique customer identifier
        tests:
          - unique
          - not_null
      - name: customer_code
        description: Business customer code
        tests:
          - not_null
      - name: email
        description: Customer email address
        tests:
          - unique
EOF

# Step 4: Test the model locally
dbt run --select new_source_customers
dbt test --select new_source_customers

# Step 5: Create a PR
git add .
git commit -m "Add silver layer transformation for new source customers"
git push origin feature/new-source-silver
```

### **Workflow 3: Building a Gold Layer Fact Table**

**Scenario**: Create a fact table for customer transactions.

```bash
# Step 1: Navigate to gold facts project
cd layer2-dbt-projects/gold-facts

# Step 2: Create fact model
cat > models/facts/fact_customer_transaction.sql << 'EOF'
{{
  config(
    materialized='table',
    indexes=[
      {'columns': ['transaction_date'], 'type': 'btree'},
      {'columns': ['customer_key'], 'type': 'hash'}
    ]
  )
}}

WITH transactions AS (
    SELECT * FROM {{ ref('transactions') }}  -- Silver layer
),

customers AS (
    SELECT * FROM {{ ref('dim_customer') }}  -- Gold dimension
),

dates AS (
    SELECT * FROM {{ ref('dim_date') }}  -- Gold dimension
),

final AS (
    SELECT
        -- Surrogate keys
        {{ dbt_utils.surrogate_key(['t.transaction_id']) }} as transaction_key,
        c.customer_key,
        d.date_key,

        -- Natural keys
        t.transaction_id,
        t.customer_id,

        -- Dimensions
        t.transaction_type,
        t.payment_method,
        t.channel,

        -- Measures
        t.transaction_amount,
        t.fee_amount,
        t.tax_amount,
        t.transaction_amount + t.fee_amount + t.tax_amount as total_amount,

        -- Calculated measures
        CASE
            WHEN t.transaction_amount > 1000 THEN 'High'
            WHEN t.transaction_amount > 100 THEN 'Medium'
            ELSE 'Low'
        END as transaction_size,

        -- Flags
        CASE
            WHEN t.status = 'Completed' THEN 1
            ELSE 0
        END as is_completed,

        CASE
            WHEN t.transaction_type = 'Refund' THEN 1
            ELSE 0
        END as is_refund,

        -- Metadata
        CURRENT_TIMESTAMP as gold_processed_at

    FROM transactions t
    LEFT JOIN customers c ON t.customer_id = c.customer_id
    LEFT JOIN dates d ON t.transaction_date = d.date_actual
)

SELECT * FROM final
EOF

# Step 3: Run and test
dbt run --select fact_customer_transaction
dbt test --select fact_customer_transaction

# Step 4: Build downstream metrics
cat > models/facts/metrics_daily_transactions.sql << 'EOF'
SELECT
    date_key,
    COUNT(*) as transaction_count,
    SUM(total_amount) as total_revenue,
    SUM(is_completed) as completed_count,
    SUM(is_refund) as refund_count,
    AVG(transaction_amount) as avg_transaction_amount
FROM {{ ref('fact_customer_transaction') }}
GROUP BY date_key
EOF
```

### **Workflow 4: Creating an Airflow DAG**

**Scenario**: Orchestrate the complete pipeline for the new source.

```bash
# Step 1: Create new DAG
cd layer3-warehouses/dags

cat > new_source_pipeline.py << 'EOF'
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'new_source_pipeline',
    default_args=default_args,
    description='Pipeline for new source data',
    schedule_interval='@daily',
    catchup=False,
    tags=['bronze', 'silver', 'gold', 'new_source'],
)

# Bronze extraction tasks
extract_customers = DockerOperator(
    task_id='extract_customers',
    image='registry.localhost/etl/new-source:0.1.0',
    command=['customers'],
    environment={
        'SOURCE_DATABASE_URL': '{{ var.value.new_source_db }}',
        'WAREHOUSE_DATABASE_URL': '{{ var.value.warehouse_db }}',
    },
    docker_url='unix://var/run/docker.sock',
    network_mode='edge',
    dag=dag,
)

extract_transactions = DockerOperator(
    task_id='extract_transactions',
    image='registry.localhost/etl/new-source:0.1.0',
    command=['transactions'],
    environment={
        'SOURCE_DATABASE_URL': '{{ var.value.new_source_db }}',
        'WAREHOUSE_DATABASE_URL': '{{ var.value.warehouse_db }}',
    },
    docker_url='unix://var/run/docker.sock',
    network_mode='edge',
    dag=dag,
)

# Silver transformation
transform_silver = DockerOperator(
    task_id='transform_silver',
    image='registry.localhost/analytics/dbt-runner:1.0.0',
    command=['bash', '-c', 'dbt run --select tag:new_source tag:silver'],
    environment={
        'DBT_PROFILES_DIR': '/profiles',
        'DBT_PROJECT_DIR': '/dbt/silver-core',
    },
    docker_url='unix://var/run/docker.sock',
    network_mode='edge',
    volumes=[
        'dbt_profiles:/profiles:ro',
        'silver_core_project:/dbt/silver-core:ro'
    ],
    dag=dag,
)

# Gold transformation
transform_gold = DockerOperator(
    task_id='transform_gold',
    image='registry.localhost/analytics/dbt-runner:1.0.0',
    command=['bash', '-c', 'dbt run --select fact_customer_transaction metrics_daily_transactions'],
    environment={
        'DBT_PROFILES_DIR': '/profiles',
        'DBT_PROJECT_DIR': '/dbt/gold-facts',
    },
    docker_url='unix://var/run/docker.sock',
    network_mode='edge',
    volumes=[
        'dbt_profiles:/profiles:ro',
        'gold_facts_project:/dbt/gold-facts:ro'
    ],
    dag=dag,
)

# Data quality checks
quality_check = BashOperator(
    task_id='quality_check',
    bash_command="""
    psql "$WAREHOUSE_DB" -c "
        SELECT
            'Customers' as table,
            COUNT(*) as row_count
        FROM pagila_silver.new_source_customers
        UNION ALL
        SELECT
            'Transactions' as table,
            COUNT(*) as row_count
        FROM gold_rental.fact_customer_transaction
    "
    """,
    env={'WAREHOUSE_DB': '{{ var.value.warehouse_db }}'},
    dag=dag,
)

# Set dependencies
[extract_customers, extract_transactions] >> transform_silver >> transform_gold >> quality_check
EOF

# Step 2: Test DAG syntax
python new_source_pipeline.py

# Step 3: Deploy to Airflow
cp new_source_pipeline.py ../../examples/all-in-one/dags/

# Step 4: Trigger in UI or CLI
astro dev run dags test new_source_pipeline
```

## 🧪 Testing Your Changes

### **Local Testing Workflow**

```bash
# 1. Unit test your datakit
cd layer2-datakits/new-source-datakit
python -m pytest tests/

# 2. Integration test with local database
docker compose -f docker-compose.test.yml up -d
python -m datakit_new_source.extract customers
docker compose -f docker-compose.test.yml down

# 3. Test dbt models
cd layer2-dbt-projects/silver-core
dbt test --select new_source_customers

# 4. Test complete pipeline
cd examples/all-in-one
astro dev pytest tests/dags/test_new_source_pipeline.py
```

### **Writing Effective Tests**

```python
# tests/test_extract.py
import pytest
from unittest.mock import Mock, patch
from datakit_new_source.extract import extract_table

def test_extract_table_success():
    """Test successful extraction."""
    with patch('datakit_new_source.extract.create_engine') as mock_engine:
        # Mock the database connections
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=100)

        with patch('pandas.read_sql', return_value=mock_df):
            result = extract_table('customers')
            assert result == 100

def test_extract_table_handles_empty():
    """Test extraction with no data."""
    with patch('pandas.read_sql', return_value=pd.DataFrame()):
        result = extract_table('customers')
        assert result == 0
```

## 📦 Dependency Management

### **Adding Python Dependencies**

```bash
# For datakits
cd layer2-datakits/your-datakit
echo "new-package==1.0.0" >> pyproject.toml
docker build -t registry.localhost/etl/your-datakit:0.1.1 .

# For Airflow
cd examples/all-in-one
echo "new-package==1.0.0" >> requirements.txt
astro dev restart
```

### **Managing dbt Dependencies**

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1

  - git: "https://github.com/yourorg/dbt-common-dimensions"
    revision: v1.0.0

# Install packages
dbt deps
```

## 🔍 Debugging Workflows

### **Common Debugging Commands**

```bash
# Check Airflow logs
astro dev logs -f

# View specific task logs
astro dev run tasks test <dag_id> <task_id> <execution_date>

# Debug a container
docker run -it --entrypoint /bin/bash \
  registry.localhost/etl/your-datakit:latest

# Check database state
psql $WAREHOUSE_DB -c "\dt bronze.*"
psql $WAREHOUSE_DB -c "SELECT * FROM bronze.br_customers LIMIT 10"

# dbt debugging
dbt debug
dbt run --select my_model --full-refresh
dbt compile --select my_model
```

### **Troubleshooting Checklist**

1. **Container won't start**: Check Dockerfile and dependencies
2. **Connection errors**: Verify network and credentials
3. **Transform fails**: Check source data and SQL syntax
4. **DAG not appearing**: Verify Python syntax and imports
5. **Tests failing**: Check test data and assertions

## 🚀 Deployment Workflow

### **From Local to Dev Environment**

```bash
# 1. Create feature branch
git checkout -b feature/new-source-integration

# 2. Commit your changes
git add .
git commit -m "feat: Add new source data pipeline

- Created datakit for bronze extraction
- Added silver transformations
- Built gold fact table
- Configured DAG orchestration"

# 3. Push to remote
git push origin feature/new-source-integration

# 4. Create PR
gh pr create --title "Add new source data pipeline" \
  --body "Implements complete pipeline for new source system"

# 5. After review and merge
git checkout main
git pull origin main

# 6. Tag for deployment
git tag -a v1.2.0 -m "Release: New source integration"
git push origin v1.2.0
```

### **Deployment Verification**

```bash
# Verify in dev environment
kubectl -n dev get pods | grep airflow
kubectl -n dev logs -f deployment/airflow-scheduler

# Check DAG is loaded
airflow dags list | grep new_source

# Trigger test run
airflow dags trigger new_source_pipeline

# Monitor execution
airflow tasks list new_source_pipeline
airflow tasks state new_source_pipeline extract_customers 2024-01-15
```

## 💡 Best Practices

### **Code Organization**
- One datakit per source system
- Separate dbt projects by layer (silver/gold)
- Group related DAGs in subdirectories
- Use consistent naming conventions

### **Development Process**
1. Always work in feature branches
2. Test locally before pushing
3. Write tests for new functionality
4. Document your changes
5. Request code reviews

### **Performance Tips**
- Use incremental models where possible
- Partition large tables
- Add appropriate indexes
- Monitor query performance
- Cache frequently used data

### **Security Practices**
- Never hardcode credentials
- Use Airflow Variables/Connections
- Rotate secrets regularly
- Follow principle of least privilege
- Audit data access

## 📚 Helpful Commands Reference

```bash
# Docker
docker ps                                    # List running containers
docker logs -f <container>                   # Follow container logs
docker exec -it <container> /bin/bash        # Shell into container

# Airflow (via Astro CLI)
astro dev start                              # Start Airflow
astro dev stop                               # Stop Airflow
astro dev restart                            # Restart Airflow
astro dev run dags list                      # List DAGs
astro dev run dags test <dag_id>            # Test DAG

# dbt
dbt run                                      # Run all models
dbt run --select <model>                     # Run specific model
dbt test                                     # Run all tests
dbt test --select <model>                    # Test specific model
dbt docs generate                            # Generate documentation
dbt docs serve                               # Serve documentation

# Git
git status                                   # Check changes
git diff                                     # View changes
git add .                                    # Stage changes
git commit -m "message"                      # Commit changes
git push origin <branch>                     # Push to remote

# Database
psql $DATABASE_URL                           # Connect to database
\dt <schema>.*                              # List tables in schema
\d <schema>.<table>                         # Describe table
SELECT COUNT(*) FROM <table>;               # Count rows
```

## 🔗 Related Documentation

- **[Creating Datakits](creating-datakits.md)** - Detailed datakit development
- **[dbt Development](dbt-development.md)** - Advanced dbt patterns
- **[DAG Patterns](dag-patterns.md)** - Airflow best practices
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions

---

*Next: Learn about [Creating Datakits](creating-datakits.md) for custom data extraction.*