# Layer 2: Data Processing Components

**🔨 Build and validate modular data processing components (datakits)**

This layer focuses on building individual, reusable data processing tools. Pipeline orchestration and integration testing happen in Layer 3.

## 📋 Prerequisites

You must have completed **Layer 1: Platform Foundation** setup:
- ✅ Traefik reverse proxy running at https://traefik.localhost
- ✅ Container registry available at https://registry.localhost
- ✅ Platform validation passed: `ansible-playbook -i ansible/inventory/local-dev.ini ansible/validate-all.yml --ask-become-pass`

## 🎯 Component Philosophy

**Layer 2 Focus**: Build and test individual components
**Layer 3 Focus**: Orchestrate components into pipelines

```
🔨 Build → 🧪 Test → ✅ Validate → 📦 Package
```

### Datakit Components
```
Individual Processing Tools (not connected pipelines):
├── bronze-pagila     → Raw data ingestion with audit trails
├── postgres-runner   → PostgreSQL operations and utilities
├── dbt-runner        → DBT transformations orchestration
├── sqlserver-runner  → SQL Server operations and utilities
└── spark-runner      → Spark processing for large datasets (optional)

DBT Projects (SQL transformations):
├── silver-core       → Data cleaning and conformance
├── gold-dimensions   → Slowly changing dimensions
└── gold-facts        → Fact tables and metrics
```

## 🚀 Quick Start

### Step 1: Build Components
```bash
# Build all datakit container images
./scripts/build-layer2-components.sh

# Optional: Build complex components like Spark
./scripts/build-layer2-components.sh --build-optional
```

### Step 2: Test Components
```bash
# Run unit tests for all components (includes data object deployment)
./scripts/test-layer2-components.sh

# Test specific component
./scripts/test-layer2-components.sh bronze-pagila

# Test with PostgreSQL container target
./scripts/test-layer2-components.sh --deployment-target postgres_container
```

### Step 3: Clean Up (When Needed)
```bash
# Remove all components
./scripts/teardown-layer2.sh --full-clean

# Keep built images for faster rebuilds
./scripts/teardown-layer2.sh --preserve-images
```

## 🔧 Component Details

### Built Images
After successful build, you'll have:
- `registry.localhost/datakits/bronze-pagila:v1.0.0`
- `registry.localhost/datakits/postgres-runner:v1.0.0`
- `registry.localhost/datakits/dbt-runner:v1.0.0`
- `registry.localhost/datakits/sqlserver-runner:v1.0.0`

### DBT Projects
- **silver-core**: Data cleaning and validation transformations
- **gold-dimensions**: Slowly changing dimension management
- **gold-facts**: Fact table creation and metrics

## 🧪 Testing

### Unit Tests
Each component includes tests that validate:
- ✅ Container builds successfully
- ✅ Python packages install correctly
- ✅ CLI tools are accessible
- ✅ Data objects deploy to test databases
- ✅ SQLModel classes create tables successfully

### Test Coverage
```bash
# Test all components with data object deployment
./scripts/test-layer2-components.sh

# Expected output:
# ✅ bronze-pagila: Container builds, CLI accessible, data objects deployed
# ✅ postgres-runner: Container builds, CLI accessible, data objects deployed
# ✅ dbt-runner: Container builds, DBT available
# ✅ sqlserver-runner: Container builds, CLI accessible, data objects deployed
```

### Data Object Deployment Testing
Components with SQLModel classes are tested by deploying their data objects to disposable test databases:
- **Default**: SQLite in-memory (fastest)
- **Alternative**: PostgreSQL/MySQL containers for integration testing
- **Framework**: Uses `layer2-datakits-framework` for multi-database support

## 🧹 Teardown Options

### Quick Reference Commands
```bash
./scripts/teardown-layer2.sh --help         # Show all options
./scripts/teardown-layer2.sh --full-clean   # Remove everything
./scripts/teardown-layer2.sh --preserve-images  # Keep images, clean temp files
```

### Teardown Modes
- **--full-clean**: Remove all images and artifacts
- **--preserve-images**: Keep built images for fast rebuilds
- **Interactive**: Choose what to clean (default)

## 🚨 Troubleshooting

### Quick Reference Commands

**Build Issues**:
```bash
# Check build logs
ls /tmp/build_*.log

# Rebuild single component
./scripts/build-layer2-components.sh --component bronze-pagila
```

**Test Issues**:
```bash
# Test single component with verbose output
./scripts/test-layer2-components.sh bronze-pagila --verbose

# Check container logs
docker logs test-bronze-pagila
```

### Common Issues

**Build Failures**:
- Check `/tmp/build_*.log` for detailed error messages
- Verify Layer 1 registry is accessible: `curl -k https://registry.localhost/v2/_catalog`

**Test Failures**:
- Verify Docker daemon is running: `docker info`
- Check component-specific logs for detailed errors

## 🚀 Next Steps

After Layer 2 validation passes:

1. **Move to Layer 3**: Orchestration and pipeline integration
2. **Integration Testing**: Use Layer 3 to test component interactions
3. **Production Deployment**: Use validated components in real pipelines

## 📁 Project Structure

```
layer2-datakits/           # Component source code
├── bronze-pagila/         # Raw data ingestion
├── postgres-runner/       # PostgreSQL utilities
├── dbt-runner/           # DBT orchestration
├── sqlserver-runner/     # SQL Server utilities
└── spark-runner/         # Spark processing (optional)

layer2-dbt-projects/      # SQL transformation projects
├── silver-core/          # Data cleaning
├── gold-dimensions/      # Dimension tables
└── gold-facts/           # Fact tables

scripts/                  # Component management
├── build-layer2-components.sh   # Build all components
├── test-layer2-components.sh    # Test all components
└── teardown-layer2.sh          # Clean up components
```

---

**🎯 Layer 2 Objective**: Prove that individual components work in isolation.
**🎯 Layer 3 Objective**: Prove that components work together in pipelines.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
