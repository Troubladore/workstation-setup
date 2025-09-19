# Layer 2: Data Processing Components Setup Guide

**🎯 Transform raw data into analytics-ready datasets using the Astronomer Airflow platform**

This guide walks you through setting up and validating the complete data processing layer, from bronze data ingestion through gold analytics tables.

## 📋 Prerequisites

You must have completed **Layer 1: Platform Foundation** setup:
- ✅ Traefik reverse proxy running at https://traefik.localhost
- ✅ Container registry available at https://registry.localhost
- ✅ Platform validation passed: `ansible-playbook -i ansible/inventory/local-dev.ini ansible/validate-all.yml --ask-become-pass`

## 🏗️ Layer 2 Architecture

### Data Processing Pipeline
```
Source Data (Pagila DB)
    ↓
📊 Bronze Layer (Raw ingestion with audit columns)
    ↓
🔄 Silver Layer (Cleaned, validated, conformed)
    ↓
✨ Gold Layer (Analytics-ready dimensions & facts)
```

### Component Stack
```
Data Kits (Python containers):
├── bronze-pagila     → Raw data ingestion with audit trails
├── postgres-runner   → PostgreSQL operations and utilities
├── sqlserver-runner  → SQL Server operations and utilities
├── spark-runner      → Spark processing for large datasets
└── dbt-runner        → DBT transformations orchestration

DBT Projects (SQL transformations):
├── silver-core       → Data cleaning and conformance
├── gold-dimensions   → Slowly changing dimensions
└── gold-facts        → Fact tables and metrics
```

## 🚀 Quick Start

### Step 1: Build and Deploy Data Components
```bash
# 🐧 Run in WSL2 Ubuntu terminal
cd <<your_repo_folder>>/workstation-setup

# Cache sudo password (prevents hanging tasks)
sudo echo "Testing sudo access"

# Build and deploy Layer 2 data processing components
ansible-playbook -i ansible/inventory/local-dev.ini ansible/setup-layer2-data.yml --ask-become-pass
```

### Step 2: Initialize Sample Database
```bash
# Initialize Pagila sample database for testing
./scripts/setup-sample-data.sh
```

### Step 3: Run End-to-End Data Pipeline
```bash
# Execute complete bronze → silver → gold pipeline
./scripts/run-data-pipeline.sh --full-refresh
```

### Step 4: Validate Data Processing
```bash
# Validate all data processing components and outputs
ansible-playbook -i ansible/inventory/local-dev.ini ansible/validate-layer2-data.yml --ask-become-pass
```

## 📊 Expected Results After Setup

### ✅ Database Infrastructure
- **Source Database**: Pagila sample data loaded and accessible
- **Target Database**: PostgreSQL with bronze/silver/gold schemas
- **Data Lineage**: Clear audit trails from source to analytics tables

### ✅ Data Pipeline Components
- **Bronze Ingestion**: Raw data with audit columns (load_time, source_table, batch_id, record_hash)
- **Silver Processing**: Cleaned data with data quality validations
- **Gold Analytics**: Dimension and fact tables ready for BI tools

### ✅ Container Registry Images
All data processing components available in local registry:
- `registry.localhost/datakits/bronze-pagila:latest`
- `registry.localhost/datakits/postgres-runner:latest`
- `registry.localhost/datakits/dbt-runner:latest`
- `registry.localhost/datakits/spark-runner:latest`
- `registry.localhost/datakits/sqlserver-runner:latest`

### ✅ Data Quality Validations
- **Row count consistency** across pipeline stages
- **Data freshness checks** with configurable thresholds
- **Schema validation** ensuring expected columns and types
- **Business rule validation** for data integrity

## 🗂️ Component Details

### Bronze Layer (Raw Data Ingestion)
**Purpose**: Ingest raw data with full audit trail and change tracking

**Key Features**:
- Immutable raw data preservation
- Audit columns: `br_load_time`, `br_source_table`, `br_batch_id`, `br_is_current`, `br_record_hash`
- Incremental and full-refresh modes
- Data lineage tracking

**Usage Example**:
```bash
# Ingest specific table with batch tracking
docker run --rm \
  registry.localhost/datakits/bronze-pagila:latest \
  ingest actor "postgresql://source_db" "postgresql://target_db" "batch_001"
```

### Silver Layer (Data Cleaning & Conformance)
**Purpose**: Apply business rules, data quality checks, and standardization

**Key Features**:
- Data type standardization
- Business rule validation
- Data quality scoring
- Slowly changing dimension handling
- Incremental processing with change detection

**DBT Models**: `layer2-dbt-projects/silver-core/models/`

### Gold Layer (Analytics-Ready Tables)
**Purpose**: Create optimized tables for analytics and reporting

**Key Features**:
- Star schema fact and dimension tables
- Pre-aggregated metrics and KPIs
- Optimized for query performance
- Business-friendly naming conventions

**DBT Models**:
- `layer2-dbt-projects/gold-dimensions/models/`
- `layer2-dbt-projects/gold-facts/models/`

## 🧪 Development & Testing Workflow

### Iterative Development Pattern
```bash
# 1. Make changes to data processing logic
vim layer2-datakits/bronze-pagila/datakit_bronze/ingest.py

# 2. Rebuild and test single component
./scripts/build-datakit.sh bronze-pagila

# 3. Test component in isolation
./scripts/test-datakit.sh bronze-pagila --sample-data

# 4. Run end-to-end pipeline test
./scripts/run-data-pipeline.sh --test-mode

# 5. Validate results
./scripts/validate-data-quality.sh --verbose
```

### Clean Slate Testing

**Complete Fresh Start** (nuclear option):
```bash
# Clean everything including data volumes
./scripts/teardown-layer2.sh --full-clean

# Fresh rebuild and deploy
./scripts/setup-layer2.sh
```

**Quick Reset** (preserves data volumes):
```bash
# Preserve data for faster rebuild
./scripts/teardown-layer2.sh --preserve-data

# Rebuild and deploy
./scripts/setup-layer2.sh
```

**Step-by-Step Control**:
```bash
# 1. Clean slate
./scripts/teardown-layer2.sh --full-clean

# 2. Build static components (images, DBT configs)
./scripts/build-layer2-components.sh

# 3. Deploy runtime services (databases)
./scripts/deploy-layer2-runtime.sh

# 4. Validate deployment
./scripts/validate-data-quality.sh
./scripts/run-data-pipeline.sh --full-refresh
```

## 🔧 Configuration Management

### Database Connections
**Location**: `ansible/group_vars/data_processing.yml`

```yaml
# Source database (Pagila sample)
source_db:
  host: localhost
  port: 5432
  database: pagila
  schema: public

# Target data warehouse
target_db:
  host: localhost
  port: 5433
  database: data_warehouse
  schemas:
    bronze: bronze_pagila
    silver: silver_core
    gold: gold_analytics
```

### Data Processing Settings
```yaml
# Pipeline configuration
pipeline:
  batch_size: 10000
  parallel_jobs: 4
  retry_attempts: 3
  timeout_minutes: 30

# Data quality thresholds
data_quality:
  max_null_percentage: 5.0
  min_row_count: 100
  max_duplicate_percentage: 1.0
```

## 🚨 Troubleshooting

### Quick Reference Commands

**Teardown Options:**
```bash
./scripts/teardown-layer2.sh --help        # Show all options
./scripts/teardown-layer2.sh --full-clean  # Nuclear: remove everything
./scripts/teardown-layer2.sh --preserve-data # Quick: keep data volumes
```

**Build & Deploy:**
```bash
./scripts/setup-layer2.sh                  # All-in-one setup
./scripts/build-layer2-components.sh       # Build images & configs
./scripts/deploy-layer2-runtime.sh         # Deploy databases & services
```

### Common Issues

**Database Connection Failures**
```bash
# Check database connectivity
./scripts/test-db-connections.sh --verbose

# Common fixes:
# 1. Ensure PostgreSQL container is running
docker ps | grep postgres

# 2. Check port conflicts
netstat -tlnp | grep :543

# 3. Verify connection strings in configuration
```

**Data Pipeline Failures**
```bash
# Check pipeline status and logs
./scripts/pipeline-status.sh --detailed

# Debug specific component
docker logs datakit-bronze-pagila

# Validate data consistency
./scripts/validate-data-lineage.sh --table=actor
```

**DBT Transformation Issues**
```bash
# Test DBT models individually
cd layer2-dbt-projects/silver-core
dbt test --models silver_actor

# Check DBT logs
dbt run --debug --models silver_actor

# Validate DBT dependencies
dbt deps --debug
```

## 📈 Performance Optimization

### Scaling for Large Datasets
```yaml
# Configure for production workloads
pipeline:
  batch_size: 50000        # Increase for larger datasets
  parallel_jobs: 8         # Scale with available CPU cores
  memory_limit: "4Gi"      # Adjust based on data volume

spark:
  executor_memory: "2g"
  executor_cores: 2
  max_executors: 4
```

### Incremental Processing
```sql
-- Example incremental model pattern
{{ config(
    materialized='incremental',
    unique_key='id',
    on_schema_change='fail'
) }}

SELECT * FROM {{ source('bronze', 'br_actor') }}
{% if is_incremental() %}
  WHERE br_load_time > (SELECT MAX(br_load_time) FROM {{ this }})
{% endif %}
```

## 🎯 Success Criteria

After successful Layer 2 setup, you should have:

✅ **End-to-End Data Pipeline**
- Data flows seamlessly from source → bronze → silver → gold
- All pipeline components containerized and available in local registry
- Comprehensive logging and monitoring in place

✅ **Data Quality Framework**
- Automated data validation at each pipeline stage
- Clear data lineage and audit trails
- Business rule validation and quality scoring

✅ **Development Workflow**
- Rapid iteration cycle for data transformations
- Isolated testing capabilities for individual components
- Complete environment teardown/rebuild for clean testing

✅ **Analytics-Ready Data**
- Star schema optimized for analytical queries
- Pre-calculated metrics and KPIs available
- Business-friendly naming and documentation

## 🚀 Next Steps

With Layer 2 complete, you're ready for:
- **Layer 3**: Airflow orchestration and workflow management
- **BI Tool Integration**: Connect Tableau, PowerBI, or similar tools
- **Production Deployment**: Scale to cloud-based data warehouses
- **Custom Data Sources**: Extend with your organization's data

---

*This data processing foundation enables sophisticated analytics workflows while maintaining the ease of use established in Layer 1.*
