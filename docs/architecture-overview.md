# Architecture Overview

A comprehensive guide to the three-layer architecture that powers our Astronomer Airflow data engineering platform, from local development to production deployment.

## 🎯 Architecture Goals

Our architecture achieves five critical objectives:

1. **Developer Fidelity**: What runs locally behaves identically in production
2. **Separation of Concerns**: Clear boundaries between data ingestion, transformation, and orchestration
3. **Multi-Tenancy**: Secure isolation between customer workloads
4. **Scalability**: Grow from single developer to enterprise deployment
5. **Maintainability**: Modular components that evolve independently

## 🏗️ Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 3: Orchestration                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Multi-Tenant │  │   Airflow    │  │   Warehouse  │          │
│  │   Configs    │──│     DAGs     │──│   Builders   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 2: Data Processing                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Datakits   │  │     dbt      │  │   Container  │          │
│  │   (Bronze)   │  │ (Silver/Gold)│  │   Runners    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 1: Platform Foundation                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Astronomer  │  │   Traefik    │  │    Docker    │          │
│  │   Runtime    │  │   Registry   │  │   Registry   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### **Layer 1: Platform Foundation**
The infrastructure layer that provides core services and runtime environment.

**Components:**
- **Astronomer Runtime 3.0-10**: Enterprise Airflow distribution
- **Traefik Proxy**: HTTPS routing and load balancing
- **Docker Registry**: Local container image storage
- **Base Images**: Customized Airflow images with required providers

**Key Features:**
- Standardized Airflow configuration
- Queue definitions and pod templates
- TLS certificate management
- Development tool integration

### **Layer 2: Data Processing**
Containerized data processing components that execute the actual work.

**Components:**
- **Datakits**: Python-based ETL for Bronze layer ingestion
- **dbt Projects**: SQL transformations for Silver and Gold layers
- **Container Runners**: Execution environments for different technologies

**Key Features:**
- Technology-specific runners (Postgres, SQL Server, Spark)
- Reusable transformation logic
- Isolated execution environments
- Version-controlled data models

### **Layer 3: Orchestration**
Multi-tenant orchestration layer that coordinates pipeline execution.

**Components:**
- **Warehouse Configurations**: YAML-based tenant specifications
- **DAG Generators**: Dynamic pipeline creation
- **Task Adapters**: Bridge between Airflow and containers

**Key Features:**
- Per-customer pipeline configuration
- Dynamic DAG generation
- Resource isolation
- Monitoring and alerting

## 🔄 Data Flow Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Source  │────▶│  Bronze  │────▶│  Silver  │────▶│   Gold   │
│ Systems  │     │   Raw    │     │ Business │     │Analytics │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                 │                │
     │           ┌────────┐       ┌────────┐      ┌────────┐
     └──────────▶│Datakit │       │  dbt   │      │  dbt   │
                 │Runner  │       │ Runner │      │ Runner │
                 └────────┘       └────────┘      └────────┘
                      │                 │                │
                 ┌────────────────────────────────────────┐
                 │         Airflow Orchestration          │
                 └────────────────────────────────────────┘
```

### **Bronze Layer (Raw Data)**
- Direct extracts from source systems
- No transformations, only type casting
- Append-only or full refresh patterns
- Schema matches source system

### **Silver Layer (Business Entities)**
- Cleaned and standardized data
- Business logic applied
- Slowly changing dimensions (SCD) handling
- One-to-one with business concepts

### **Gold Layer (Analytics Ready)**
- Dimensional models (facts and dimensions)
- Pre-aggregated metrics
- Optimized for query performance
- Business-specific data marts

## 🐳 Container Orchestration Strategy

### **Local Development (DockerOperator)**

```
┌─────────────────────────────────────┐
│         Airflow Worker              │
│  ┌────────────────────────────┐     │
│  │     DockerOperator         │     │
│  └──────────┬─────────────────┘     │
│             │                        │
└─────────────┼────────────────────────┘
              │
     ┌────────▼────────┐
     │  Docker Daemon  │
     │  ┌───────────┐  │
     │  │ Container │  │
     │  │  Runner   │  │
     │  └───────────┘  │
     └─────────────────┘
```

**Benefits:**
- Simple local setup
- Fast iteration cycles
- Direct container access
- Easy debugging

### **Production (KubernetesPodOperator)**

```
┌─────────────────────────────────────┐
│       Airflow Scheduler             │
│  ┌────────────────────────────┐     │
│  │  KubernetesPodOperator     │     │
│  └──────────┬─────────────────┘     │
│             │                        │
└─────────────┼────────────────────────┘
              │
     ┌────────▼────────┐
     │   Kubernetes    │
     │  ┌───────────┐  │
     │  │    Pod    │  │
     │  │  Runner   │  │
     │  └───────────┘  │
     └─────────────────┘
```

**Benefits:**
- Resource isolation
- Auto-scaling
- Pod security policies
- Resource quotas

### **Key Innovation: Operator Parity**

The same container images run in both environments:
```python
# Local Development
task = DockerOperator(
    task_id='bronze_extract',
    image='registry.localhost/etl/postgres-runner:0.1.0',
    command=['extract', '--table', 'customers']
)

# Production
task = KubernetesPodOperator(
    task_id='bronze_extract',
    image='registry.localhost/etl/postgres-runner:0.1.0',
    cmds=['extract', '--table', 'customers']
)
```

## 🔐 Security Architecture

### **Network Isolation**

```
┌─────────────────────────────────────────────┐
│                  Internet                    │
└──────────────────┬──────────────────────────┘
                   │
           ┌───────▼────────┐
           │    Traefik     │
           │  (TLS Term)    │
           └───────┬────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼─────┐ ┌───▼────┐ ┌────▼────┐
│  Airflow  │ │Registry│ │Services │
│  (:8080)  │ │ (:5000)│ │         │
└───────────┘ └────────┘ └─────────┘
      │                         │
      └────────┬────────────────┘
               │
        ┌──────▼──────┐
        │   Docker    │
        │   Network   │
        │   (edge)    │
        └─────────────┘
```

### **Authentication Layers**

1. **User Authentication**: Airflow RBAC with LDAP/OAuth
2. **Service Authentication**: mTLS between services
3. **Database Authentication**: Kerberos for enterprise systems
4. **Registry Authentication**: Token-based pull secrets

## 🚀 Deployment Topology

### **Local Development**
```
Developer Laptop
├── WSL2/Linux/macOS
├── Docker Desktop
├── Traefik + Registry
├── Airflow (Astro CLI)
└── Container Runners
```

### **Shared Development**
```
Development Cluster
├── Kubernetes Namespace: dev
├── Astronomer Platform
├── Shared Registry
├── Development Databases
└── Monitoring Stack
```

### **Production**
```
Production Clusters
├── Standard Enclave
│   ├── Customer Namespaces
│   ├── Isolated Airflow Instances
│   └── Dedicated Resources
└── High Security Enclave
    ├── Enhanced Isolation
    ├── Audit Logging
    └── Compliance Controls
```

## 📊 Multi-Tenant Architecture

### **Tenant Isolation Model**

```
┌──────────────────────────────────────┐
│         Platform Services             │
│  (Traefik, Registry, Monitoring)      │
└────────────┬─────────────────────────┘
             │
    ┌────────┼────────┬──────────┐
    │        │        │          │
┌───▼───┐ ┌─▼───┐ ┌──▼───┐ ┌───▼───┐
│Tenant │ │Tenant│ │Tenant│ │Tenant │
│  A    │ │  B   │ │  C   │ │  D    │
├───────┤ ├──────┤ ├──────┤ ├───────┤
│Airflow│ │Airflow│ │Airflow│ │Airflow│
│ Namespace │ Namespace │ Namespace │
├───────┤ ├──────┤ ├──────┤ ├───────┤
│Schema │ │Schema│ │Schema│ │Schema │
│  A    │ │  B   │ │  C   │ │  D    │
└───────┘ └──────┘ └──────┘ └───────┘
```

### **Resource Allocation**

Each tenant receives:
- Dedicated Airflow deployment
- Isolated database schemas
- Separate Kubernetes namespace
- Custom resource quotas
- Independent scaling policies

## 🔄 Component Interactions

### **DAG Execution Flow**

```
1. Scheduler picks up DAG
       │
       ▼
2. Task queued to worker
       │
       ▼
3. Worker starts operator
       │
       ▼
4. Container/Pod launched
       │
       ▼
5. Datakit/dbt executes
       │
       ▼
6. Results written to warehouse
       │
       ▼
7. Task marked complete
```

### **Configuration Flow**

```
warehouse.yaml ──┐
                 │
    ┌────────────▼──────────┐
    │   DAG Generator       │
    └────────────┬──────────┘
                 │
         ┌───────▼───────┐
         │  Dynamic DAG  │
         └───────┬───────┘
                 │
      ┌──────────┼──────────┐
      │          │          │
  ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
  │Bronze │ │Silver │ │ Gold  │
  │ Tasks │ │ Tasks │ │ Tasks │
  └───────┘ └───────┘ └───────┘
```

## 🎯 Key Design Decisions

### **Why Three Layers?**

1. **Separation of Concerns**: Each layer has a specific responsibility
2. **Independent Scaling**: Layers can scale based on their workload
3. **Technology Freedom**: Choose the best tool for each layer
4. **Maintainability**: Changes isolated to affected layer

### **Why Container-Based?**

1. **Consistency**: Same code runs everywhere
2. **Isolation**: Dependencies don't conflict
3. **Versioning**: Precise control over deployments
4. **Portability**: Works on any container platform

### **Why YAML Configuration?**

1. **Declarative**: Describe desired state, not procedures
2. **Version Control**: Track changes over time
3. **Validation**: Schema enforcement prevents errors
4. **Simplicity**: Non-programmers can configure

## 📈 Scaling Considerations

### **Horizontal Scaling**
- Add more Airflow workers
- Increase container runners
- Expand Kubernetes nodes

### **Vertical Scaling**
- Increase resource limits
- Optimize container sizes
- Upgrade node specifications

### **Performance Optimization**
- Connection pooling
- Query optimization
- Caching strategies
- Parallel execution

## 🔗 Related Documentation

- **[Container Orchestration](container-orchestration.md)** - Deep dive into Docker/K8s patterns
- **[Bronze → Silver → Gold](bronze-silver-gold.md)** - Data architecture patterns
- **[Multi-Tenant Setup](multi-tenant-setup.md)** - Tenant isolation details
- **[Performance & Scaling](performance-scaling.md)** - Optimization strategies

## 💡 Architecture Principles

1. **Immutability**: Containers and infrastructure as code
2. **Idempotency**: Repeatable executions produce same results
3. **Observability**: Comprehensive logging and monitoring
4. **Security**: Defense in depth with multiple layers
5. **Simplicity**: Complexity only where it adds value

---

*Next: Understand the [Bronze → Silver → Gold](bronze-silver-gold.md) data architecture pattern.*