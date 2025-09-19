# Layer 3: Warehouse Orchestration

**🏭 Orchestrate validated components into complete data pipelines**

This layer focuses on pipeline integration and testing. Component building and validation happen in Layer 2.

## 📋 Prerequisites

You must have completed previous layers:
- ✅ **Layer 1**: Platform Foundation (Traefik, Registry)
- ✅ **Layer 2**: Component Validation (Datakits built and tested)

## 🎯 Pipeline Philosophy

**Layer 2 Focus**: Build and test individual components (datakits)
**Layer 3 Focus**: Orchestrate components into complete data pipelines

```
🔨 Components → 🏭 Orchestration → 🧪 Integration Testing → 📊 Production Pipelines
```

### Architecture Overview
```
Pipeline Orchestration (Layer 3):
├── Airflow DAGs               → Pipeline definitions
├── Database Environments     → Integration testing databases
├── Multi-tenant Warehouses   → Configurable warehouse instances
└── Integration Tests         → End-to-end validation

Using Components from Layer 2:
├── bronze-pagila:v1.0.0     → Raw data ingestion
├── postgres-runner:v1.0.0   → Database operations
├── dbt-runner:v1.0.0        → SQL transformations
├── sqlserver-runner:v1.0.0  → SQL Server operations
└── spark-runner:v1.0.0      → Large-scale processing (optional)
```

## 🚀 Quick Start

### Step 1: Set Up Pipeline Infrastructure
```bash
# Deploy database environments for integration testing
./layer3-warehouses/scripts/deploy-databases.sh

# Set up pipeline orchestration platform
./layer3-warehouses/scripts/setup-layer3.sh
```

### Step 2: Run Integration Tests
```bash
# Test complete pipeline flows using Layer 2 components
./layer3-warehouses/scripts/run-integration-tests.sh
```

### Step 3: Clean Up (When Needed)
```bash
# Remove pipeline infrastructure
./layer3-warehouses/scripts/teardown-layer3.sh
```

## 🔧 Component Integration

### How Layer 3 Uses Layer 2
Layer 3 orchestrates the validated Layer 2 components and reuses the deployment framework:

**Component Reuse**:
- **bronze-pagila:v1.0.0**: Ingests raw data from source systems
- **dbt-runner:v1.0.0**: Executes SQL transformations (Silver → Gold)
- **postgres-runner:v1.0.0**: Manages database operations and utilities
- **sqlserver-runner:v1.0.0**: Handles SQL Server specific operations

**Framework Reuse**:
- **data-platform-framework**: Deploy all datakit objects to integration environments
- **Multi-database targeting**: Test pipelines against PostgreSQL, MySQL, etc.
- **Disposable environments**: Create/destroy pipeline testing environments

### Database Environments
- **Source Database**: PostgreSQL with Pagila sample data
- **Data Warehouse**: PostgreSQL for Bronze/Silver/Gold layers
- **Integration Testing**: Isolated environments for pipeline testing

## 🏗️ Pipeline Architecture

### Data Flow
```
Source Systems → Bronze (Raw) → Silver (Cleaned) → Gold (Analytics)
```

### Component Orchestration
1. **Ingestion**: bronze-pagila extracts and loads raw data
2. **Transformation**: dbt-runner executes SQL transformations
3. **Quality**: Data validation and quality checks
4. **Analytics**: Gold layer ready for consumption

## 🧪 Integration Testing

### Test Scenarios
- Complete pipeline execution (Bronze → Silver → Gold)
- Multi-tenant warehouse configurations
- Data quality validation across all layers
- Component failure and recovery scenarios
- Performance testing with sample datasets

## 📁 Project Structure

```
layer3-warehouses/           # Pipeline orchestration
├── configs/warehouses/      # Multi-tenant configurations
│   ├── acme.yaml           # Example: ACME Corp warehouse
│   └── globex.yaml         # Example: Globex Corp warehouse
├── dags/                   # Airflow DAGs
│   ├── warehouse_factory.py # Multi-tenant warehouse DAG
│   └── pagila_pipeline.py  # Sample pipeline implementation
├── include/                # Shared configurations
│   └── .env.example       # Environment variables template
└── scripts/               # Layer 3 automation
    ├── setup-layer3.sh    # Set up orchestration platform
    ├── deploy-databases.sh # Deploy integration databases
    ├── run-integration-tests.sh # Run end-to-end tests
    └── teardown-layer3.sh  # Clean up Layer 3 environment

examples/                   # Complete examples
└── all-in-one/            # Full pipeline demonstration
    └── dags/pagila_pipeline.py
```

## 🔄 Framework Integration

### Layer 3 Uses Layer 2 Framework

Layer 3 imports and reuses the deployment framework from Layer 2:

```python
# In Layer 3 setup scripts
from layer2_datakits_framework.utils.deployment import (
    discover_datakit_modules,
    discover_sqlmodel_classes,
    deploy_data_objects
)
from layer2_datakits_framework.config.targets import (
    get_integration_target,
    create_custom_target
)

def setup_pipeline_environment():
    """Deploy all datakit components to integration environment"""
    target = get_integration_target()  # PostgreSQL container

    datakit_paths = [
        "/path/to/bronze-pagila",
        "/path/to/postgres-runner",
        "/path/to/dbt-runner"
    ]

    for datakit_path in datakit_paths:
        modules = discover_datakit_modules(datakit_path)
        tables = discover_sqlmodel_classes(modules)
        deploy_data_objects(tables, target)

    return target  # Ready for pipeline testing
```

### Multi-Tenant Configuration

```python
def setup_tenant_warehouse(tenant_name: str):
    """Create isolated warehouse for specific tenant"""
    target = create_custom_target(
        "postgres",
        f"warehouse_{tenant_name}",
        host="warehouse-db",
        port=5432,
        user=f"tenant_{tenant_name}"
    )

    # Deploy all datakit objects to tenant-specific database
    deploy_all_datakits(target)
    return target
```

## 🚀 Implementation Status

Layer 3 will be implemented using the validated Layer 2 components and framework:

**Current Status**:
- ✅ Architecture defined
- ✅ Directory structure created
- ✅ Reference materials organized
- ✅ Layer 2 framework available for reuse
- 🚧 Implementation in progress

## 🚀 Next Steps

1. **Complete Layer 2 Validation**: Ensure all datakits are built and tested
2. **Implement Database Deployment**: Create integration testing environments
3. **Build Pipeline Orchestration**: Implement Airflow DAGs using Layer 2 components
4. **Integration Testing**: Validate complete pipeline flows
5. **Multi-tenant Support**: Configure warehouse instances for different organizations

---

**🎯 Layer 3 Objective**: Prove that validated components work together in complete, production-ready data pipelines.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
