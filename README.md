# Astronomer Airflow Data Engineering Workstation Setup

A comprehensive mono-repo for setting up a production-ready data engineering workstation with Astronomer-flavored Apache Airflow. This repository provides everything needed to go from a fresh development machine to a fully functional data engineering environment.

## 🎯 Why This Matters

**For Data Engineers**: Get a production-identical development environment running in under 30 minutes, with all the tools and patterns you need to build reliable data pipelines.

**For Platform Teams**: Deploy a standardized, maintainable data platform that scales from developer laptops to multi-tenant production clusters.

**For Organizations**: Achieve true development-production parity, reducing bugs and accelerating delivery while maintaining enterprise security standards.

## 🚀 Quick Navigation

### Getting Started
- **⚡ [Quick Start Guide](docs/QUICK_START.md)** - Up and running in 30 minutes
- **📚 [Complete Documentation](docs/README.md)** - Comprehensive guides and references
- **🏗️ [Architecture Overview](docs/architecture-overview.md)** - Understand the system design
- **💻 [Developer Workflows](docs/developer-workflows.md)** - Day-to-day development patterns

### Deep Dives
- **📊 [Bronze → Silver → Gold Pattern](docs/bronze-silver-gold.md)** - Data layering architecture
- **🐳 [Container Orchestration](docs/container-orchestration.md)** - DockerOperator to KubernetesPodOperator
- **🔐 [Authentication & Security](docs/authentication-kerberos.md)** - Enterprise authentication patterns
- **📈 [Performance & Scaling](docs/performance-scaling.md)** - Resource optimization and tuning

## 🏗️ Architecture Overview

The system follows a **three-layer architecture**:

### Layer 1: Platform Foundation
- **Astronomer Runtime**: Enterprise-grade Airflow distribution (Runtime 3.0-10 / Airflow 3.0.6)
- **Infrastructure**: Traefik reverse proxy, local Docker registry, TLS certificates
- **Configuration**: Queue definitions, pod templates, standardized settings

### Layer 2: Data Processing Components
- **Datakits**: Python-based ETL runners for Bronze layer data ingestion
  - Postgres, SQL Server (with Kerberos), Spark support
- **dbt Projects**: SQL transformations following Bronze → Silver → Gold pattern
  - Shared dimensions, domain-specific facts
  - Single source of truth for business logic

### Layer 3: Orchestration & Multi-tenancy
- **Warehouse Builder**: YAML-configured, tenant-aware data pipelines
- **Development Parity**: DockerOperator locally, KubernetesPodOperator in production
- **Per-customer Isolation**: Namespace and schema separation

## 🚀 Quick Start

### Prerequisites
- Windows 11 with WSL2 or Linux/macOS
- Docker Desktop or Docker Engine
- 16GB RAM minimum (32GB recommended)
- 50GB available disk space

### One-Command Setup
```bash
# Clone and enter the repository
git clone https://github.com/yourorg/workstation-setup.git
cd workstation-setup

# Run the automated setup (15-20 minutes)
./scripts/setup.sh

# Verify the installation
./scripts/verify.sh
```

## 📚 Documentation

- **[Philosophy](docs/philosophy/)**: Architectural principles and design decisions
- **[Journey](docs/journey/)**: Path from local development to production
- **[Developer Experience](docs/dev-local-experience/)**: Day-to-day workflow guides

## 🔧 Core Components

### Prerequisites & Infrastructure
- **[Windows/WSL2 Setup](prerequisites/windows-wsl2/)**: Development environment preparation
- **[Traefik + Registry](prerequisites/traefik-registry/)**: Local routing and image storage
- **[TLS Certificates](prerequisites/certificates/)**: Secure local HTTPS with mkcert

### Data Processing
- **[Platform Base](layer1-platform/)**: Airflow runtime and configuration
- **[Datakits](layer2-datakits/)**: Containerized ETL runners
- **[dbt Projects](layer2-dbt-projects/)**: SQL transformation layers

### Orchestration
- **[Warehouse Configs](layer3-warehouses/)**: Multi-tenant pipeline definitions
- **[Example Implementations](examples/)**: Complete working demonstrations

## 🎓 Core Principles

1. **Developer Fidelity**: Local development mirrors production behavior
2. **Separation of Concerns**: Bronze → Silver → Gold data layering
3. **Single Source of Truth**: Centralized dimension definitions
4. **Modularity**: Composable datakits and dbt projects
5. **Sustainability**: Reusable images, centralized configuration

## 📖 Learning Paths

### For New Data Engineers
1. Start with the [Quick Start Guide](docs/QUICK_START.md)
2. Understand [Bronze → Silver → Gold](docs/bronze-silver-gold.md) data patterns
3. Follow the [Developer Workflows](docs/developer-workflows.md)
4. Build your first pipeline with [examples](examples/)

### For Architects & Platform Engineers
1. Review the [Architecture Overview](docs/architecture-overview.md)
2. Understand the [Journey to Production](docs/journey/)
3. Study [Container Orchestration](docs/container-orchestration.md) patterns
4. Plan deployments with [Performance & Scaling](docs/performance-scaling.md)

## 🛠️ Technology Stack

- **Orchestration**: Apache Airflow 3.0.6 via Astronomer Runtime
- **Containerization**: Docker with local registry
- **Routing**: Traefik with .localhost domains
- **Transformations**: dbt-core for SQL-based ETL
- **Authentication**: Kerberos sidecar for enterprise systems
- **Languages**: Python, SQL, YAML configuration

## 🔧 Common Tasks

- **Add a new data source**: See [Creating Datakits](docs/creating-datakits.md)
- **Modify transformations**: See [dbt Development](docs/dbt-development.md)
- **Configure a new tenant**: See [Multi-Tenant Setup](docs/multi-tenant-setup.md)
- **Debug issues**: See [Troubleshooting Guide](docs/troubleshooting.md)

## 📚 Complete Documentation

Visit the **[Documentation Hub](docs/README.md)** for:
- Detailed technical guides
- Architecture decisions and rationale
- Migration and deployment strategies
- Performance tuning and optimization
- Security and compliance patterns

## 🤝 Support & Contributing

- **Documentation**: All guides are in [docs/](docs/)
- **Examples**: Working implementations in [examples/](examples/)
- **Issues**: Contact your platform team
- **Contributing**: Follow your organization's contribution guidelines

## 📄 License

Proprietary - Internal Use Only

---

*Built with a focus on developer experience and production readiness.*