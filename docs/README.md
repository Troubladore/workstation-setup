# Documentation Hub

Welcome to the comprehensive documentation for the Astronomer Airflow Data Engineering Workstation. This hub provides detailed technical guides, architectural deep-dives, and practical workflows for data engineers and platform teams.

## 📍 Where to Start

### **New to the Platform?**
Begin your journey with these essentials:
1. **⚡ [Quick Start Guide](QUICK_START.md)** - Get running in 30 minutes
2. **📊 [Bronze → Silver → Gold Pattern](bronze-silver-gold.md)** - Understand our data architecture
3. **💻 [Developer Workflows](developer-workflows.md)** - Learn day-to-day development patterns

### **Setting Up Your Team?**
Platform setup and configuration:
1. **🏗️ [Architecture Overview](architecture-overview.md)** - System design and components
2. **🚀 [Journey to Production](journey/)** - Environment progression strategy
3. **👥 [Multi-Tenant Setup](multi-tenant-setup.md)** - Configure customer isolation

### **Building Pipelines?**
Hands-on development guides:
1. **🔧 [Creating Datakits](creating-datakits.md)** - Build custom data extractors
2. **🎯 [dbt Development](dbt-development.md)** - Transform data with SQL
3. **📝 [DAG Patterns](dag-patterns.md)** - Airflow best practices

## 📚 Documentation Categories

### **Architecture & Design**
Understanding the system's foundation and design decisions.

| Document | Description | Audience |
|----------|-------------|----------|
| **[Architecture Overview](architecture-overview.md)** | Three-layer system design, component interactions | Everyone |
| **[Bronze → Silver → Gold](bronze-silver-gold.md)** | Data layering pattern and rationale | Data Engineers |
| **[Container Orchestration](container-orchestration.md)** | DockerOperator to KubernetesPodOperator parity | Platform Engineers |
| **[Architecture Decisions](architecture-decisions.md)** | Key design choices and trade-offs | Architects |

### **Development Guides**
Practical guides for building and maintaining data pipelines.

| Document | Description | Audience |
|----------|-------------|----------|
| **[Developer Workflows](developer-workflows.md)** | Daily development patterns and practices | Data Engineers |
| **[Creating Datakits](creating-datakits.md)** | Building Python-based ETL containers | Data Engineers |
| **[dbt Development](dbt-development.md)** | SQL transformation development | Analytics Engineers |
| **[DAG Patterns](dag-patterns.md)** | Airflow DAG best practices | Data Engineers |
| **[Testing Strategies](testing-strategies.md)** | Unit, integration, and E2E testing | All Developers |

### **Configuration & Deployment**
Setting up and deploying the platform across environments.

| Document | Description | Audience |
|----------|-------------|----------|
| **[Multi-Tenant Setup](multi-tenant-setup.md)** | Customer isolation and configuration | Platform Engineers |
| **[Environment Migration](environment-migration.md)** | Moving from local to production | DevOps |
| **[Authentication & Security](authentication-kerberos.md)** | Kerberos and security patterns | Security Teams |
| **[Performance & Scaling](performance-scaling.md)** | Optimization and resource management | Platform Engineers |

### **Operations & Maintenance**
Running and maintaining the platform.

| Document | Description | Audience |
|----------|-------------|----------|
| **[Troubleshooting Guide](troubleshooting.md)** | Common issues and solutions | Everyone |
| **[Monitoring & Observability](monitoring-observability.md)** | Metrics, logs, and alerts | Operations |
| **[Backup & Recovery](backup-recovery.md)** | Data protection strategies | Operations |
| **[Upgrade Procedures](upgrade-procedures.md)** | Version migration paths | Platform Engineers |

### **Reference Material**
Deep technical references and specifications.

| Document | Description | Audience |
|----------|-------------|----------|
| **[API Reference](api-reference.md)** | Datakit and utility APIs | Developers |
| **[Configuration Reference](configuration-reference.md)** | All configuration options | Platform Engineers |
| **[CLI Commands](cli-commands.md)** | Command-line tools and scripts | Everyone |
| **[Glossary](glossary.md)** | Terms and definitions | New Team Members |

## 🗺️ Learning Paths by Role

### **Data Engineer Path**
Building reliable data pipelines from source to warehouse.

1. **Foundation** (Week 1)
   - [Quick Start Guide](QUICK_START.md)
   - [Bronze → Silver → Gold Pattern](bronze-silver-gold.md)
   - [Developer Workflows](developer-workflows.md)

2. **Pipeline Development** (Week 2)
   - [Creating Datakits](creating-datakits.md)
   - [dbt Development](dbt-development.md)
   - [DAG Patterns](dag-patterns.md)

3. **Advanced Topics** (Week 3+)
   - [Testing Strategies](testing-strategies.md)
   - [Performance & Scaling](performance-scaling.md)
   - [Troubleshooting Guide](troubleshooting.md)

### **Platform Engineer Path**
Deploying and maintaining the data platform.

1. **System Understanding** (Week 1)
   - [Architecture Overview](architecture-overview.md)
   - [Container Orchestration](container-orchestration.md)
   - [Multi-Tenant Setup](multi-tenant-setup.md)

2. **Deployment** (Week 2)
   - [Environment Migration](environment-migration.md)
   - [Authentication & Security](authentication-kerberos.md)
   - [Configuration Reference](configuration-reference.md)

3. **Operations** (Week 3+)
   - [Monitoring & Observability](monitoring-observability.md)
   - [Performance & Scaling](performance-scaling.md)
   - [Upgrade Procedures](upgrade-procedures.md)

### **Analytics Engineer Path**
Transforming data for business insights.

1. **Core Concepts** (Week 1)
   - [Bronze → Silver → Gold Pattern](bronze-silver-gold.md)
   - [dbt Development](dbt-development.md)
   - [Quick Start Guide](QUICK_START.md)

2. **Modeling** (Week 2)
   - [Dimensional Modeling](dimensional-modeling.md)
   - [Testing Strategies](testing-strategies.md)
   - [DAG Patterns](dag-patterns.md)

3. **Optimization** (Week 3+)
   - [Performance & Scaling](performance-scaling.md)
   - [Monitoring & Observability](monitoring-observability.md)

## 🔍 Quick Reference

### **Common Commands**
```bash
# Start local environment
cd examples/all-in-one && astro dev start

# Build all images
./scripts/build-all.sh

# Verify setup
./scripts/verify.sh

# Run a specific datakit
docker run registry.localhost/etl/postgres-runner:0.1.0

# Execute dbt models
docker run registry.localhost/analytics/dbt-runner:1.0.0 dbt run
```

### **Key Configuration Files**
- `layer1-platform/airflow_settings.yaml` - Airflow configuration
- `layer3-warehouses/configs/warehouses/*.yaml` - Tenant configurations
- `prerequisites/traefik-registry/docker-compose.yml` - Infrastructure services
- `.env` files - Environment-specific settings

### **Important Paths**
- **DAGs**: `layer3-warehouses/dags/`
- **Datakits**: `layer2-datakits/*/`
- **dbt Projects**: `layer2-dbt-projects/*/`
- **Examples**: `examples/*/`

## 📖 Philosophy Documents

Understanding the "why" behind our architectural decisions:

- **[Core Principles](philosophy/01_principles.md)** - Guiding design principles
- **[Key Choices](philosophy/02_choices.md)** - Major architectural decisions
- **[Alternatives Considered](philosophy/03_options.md)** - Options we evaluated
- **[Future Direction](philosophy/04_future.md)** - Roadmap and evolution

## 🚀 Journey Documents

The path from local development to production:

- **[Local Development](journey/01_local.md)** - Developer workstation setup
- **[Shared Development](journey/02_shared_dev.md)** - Team collaboration environment
- **[Integration & QA](journey/03_int_qa.md)** - Testing and validation
- **[Production](journey/04_prod.md)** - Final deployment

## 💡 Tips for Using This Documentation

1. **Use the search function** (Ctrl+F) to quickly find topics
2. **Follow the learning paths** for structured onboarding
3. **Check the troubleshooting guide** before asking for help
4. **Bookmark frequently used references** for quick access
5. **Contribute improvements** when you find gaps or errors

## 📝 Documentation Standards

When contributing to these docs:
- Use clear, concise language
- Include practical examples
- Add diagrams for complex concepts
- Keep code examples runnable
- Update cross-references when moving content
- Test all commands before documenting

---

*Need help? Can't find what you're looking for? Contact your platform team or check the [Troubleshooting Guide](troubleshooting.md).*