# Multi-Tenant Setup Guide

A comprehensive guide to implementing, managing, and scaling multi-tenant data pipelines in our Astronomer Airflow platform, ensuring complete isolation, security, and performance for each customer.

## 🎯 Multi-Tenancy Goals

Our multi-tenant architecture achieves:

1. **Complete Isolation**: No data leakage between tenants
2. **Resource Fairness**: Guaranteed resources per tenant
3. **Independent Scaling**: Tenants scale without affecting others
4. **Centralized Management**: Single platform, multiple customers
5. **Cost Efficiency**: Shared infrastructure with isolated workloads

## 🏗️ Multi-Tenant Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Platform Control Plane                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Platform    │  │   Tenant     │  │  Monitoring  │             │
│  │   Admin UI    │  │  Management  │  │  & Billing   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
    ┌───────────────┬───────────────┼───────────────┬───────────────┐
    │               │               │               │               │
┌───▼───┐      ┌───▼───┐      ┌───▼───┐      ┌───▼───┐      ┌───▼───┐
│Tenant │      │Tenant │      │Tenant │      │Tenant │      │Tenant │
│  DEV  │      │   A   │      │   B   │      │   C   │      │   D   │
├───────┤      ├───────┤      ├───────┤      ├───────┤      ├───────┤
│Airflow│      │Airflow│      │Airflow│      │Airflow│      │Airflow│
│  NS   │      │  NS   │      │  NS   │      │  NS   │      │  NS   │
├───────┤      ├───────┤      ├───────┤      ├───────┤      ├───────┤
│  K8s  │      │  K8s  │      │  K8s  │      │  K8s  │      │  K8s  │
│ Quota │      │ Quota │      │ Quota │      │ Quota │      │ Quota │
├───────┤      ├───────┤      ├───────┤      ├───────┤      ├───────┤
│  DB   │      │  DB   │      │  DB   │      │  DB   │      │  DB   │
│Schema │      │Schema │      │Schema │      │Schema │      │Schema │
└───────┘      └───────┘      └───────┘      └───────┘      └───────┘
```

## 📋 Tenant Configuration

### **Tenant Specification YAML**

```yaml
# layer3-warehouses/configs/warehouses/acme-corp.yaml
tenant:
  # Tenant identification
  name: acme-corp
  display_name: "ACME Corporation"
  tier: enterprise  # basic, standard, enterprise
  environment: production  # dev, staging, production

  # Contact information
  contacts:
    technical:
      - name: "John Smith"
        email: "john.smith@acme.com"
        role: "Data Engineering Lead"
    business:
      - name: "Jane Doe"
        email: "jane.doe@acme.com"
        role: "Product Owner"

  # Authentication
  authentication:
    type: oauth2  # basic, oauth2, saml
    provider: okta
    config:
      client_id: "{{ vault.get('acme/oauth/client_id') }}"
      client_secret: "{{ vault.get('acme/oauth/client_secret') }}"
      redirect_uri: "https://airflow-acme.company.com/oauth-authorized"
      tenant_id: "acme-corp"

warehouse:
  # Data configuration
  name: acme_warehouse
  database:
    host: "warehouse-db.internal"
    port: 5432
    name: "acme_analytics"
    schema_prefix: "acme_"

  # Data sources
  bronze_jobs:
    - name: customers
      source: salesforce
      schedule: "0 2 * * *"  # 2 AM daily
      config:
        object: "Account"
        fields: ["Id", "Name", "Type", "Industry"]
        where: "IsDeleted = false"

    - name: orders
      source: postgres_operational
      schedule: "0 */4 * * *"  # Every 4 hours
      config:
        table: "public.orders"
        incremental_column: "modified_at"
        lookback_days: 2

    - name: products
      source: api_catalog
      schedule: "0 6 * * *"  # 6 AM daily
      config:
        endpoint: "/api/v2/products"
        pagination: true
        page_size: 1000

  # Transformations
  dbt:
    silver:
      enabled: true
      models:
        - "silver_customers"
        - "silver_orders"
        - "silver_products"
      schedule: "0 3 * * *"  # 3 AM daily

    gold:
      enabled: true
      dimensions:
        - "dim_customer"
        - "dim_product"
        - "dim_date"
      facts:
        - "fact_orders"
        - "fact_customer_lifetime"
      schedule: "0 4 * * *"  # 4 AM daily

  # Quality checks
  data_quality:
    enabled: true
    checks:
      - type: "row_count"
        tables: ["silver_*", "fact_*"]
        threshold: 0.1  # 10% variance allowed

      - type: "freshness"
        tables: ["bronze.*"]
        max_age_hours: 26

      - type: "schema_drift"
        tables: ["bronze.*"]
        action: "alert"  # alert, fail, ignore

resources:
  # Kubernetes resources
  kubernetes:
    namespace: "airflow-acme"

    quotas:
      requests:
        cpu: "8"
        memory: "32Gi"
        storage: "100Gi"
        pods: "50"
      limits:
        cpu: "16"
        memory: "64Gi"
        storage: "500Gi"

    node_selector:
      workload: "data-processing"
      tenant-tier: "enterprise"

    tolerations:
      - key: "tenant"
        operator: "Equal"
        value: "acme-corp"
        effect: "NoSchedule"

  # Airflow configuration
  airflow:
    workers:
      min: 2
      max: 10
      autoscaling: true

    scheduler:
      replicas: 2
      resources:
        requests:
          cpu: "1"
          memory: "2Gi"
        limits:
          cpu: "2"
          memory: "4Gi"

    webserver:
      replicas: 2
      resources:
        requests:
          cpu: "500m"
          memory: "1Gi"
        limits:
          cpu: "1"
          memory: "2Gi"

  # Database resources
  database:
    connections:
      min: 10
      max: 50
    storage_gb: 100
    backup:
      enabled: true
      retention_days: 30

features:
  # Feature flags
  advanced_monitoring: true
  custom_plugins: true
  external_task_sensors: false
  cross_tenant_dependencies: false
  data_lineage: true
  audit_logging: true

sla:
  # Service level agreements
  uptime_percent: 99.9
  support_tier: "24x7"
  response_time:
    critical: "1 hour"
    high: "4 hours"
    medium: "1 business day"
    low: "3 business days"

billing:
  # Billing configuration
  model: "usage_based"  # fixed, usage_based, hybrid
  metrics:
    - type: "task_runs"
      rate: 0.01
    - type: "storage_gb"
      rate: 0.10
    - type: "compute_hours"
      rate: 0.50
  billing_contact: "billing@acme.com"
  cost_center: "DATA-001"
```

## 🚀 Tenant Provisioning

### **Automated Tenant Setup Script**

```python
# scripts/provision_tenant.py
import os
import yaml
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any
import psycopg2
from kubernetes import client, config
from airflow.models import Variable
import hvac  # HashiCorp Vault client

class TenantProvisioner:
    """Automated tenant provisioning for multi-tenant Airflow."""

    def __init__(self, config_path: str, environment: str = 'production'):
        self.config = self._load_config(config_path)
        self.environment = environment
        self.tenant_name = self.config['tenant']['name']

        # Initialize connections
        self._init_kubernetes()
        self._init_database()
        self._init_vault()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate tenant configuration."""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required = ['tenant', 'warehouse', 'resources']
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")

        return config

    def _init_kubernetes(self):
        """Initialize Kubernetes client."""
        if os.getenv('KUBERNETES_SERVICE_HOST'):
            config.load_incluster_config()
        else:
            config.load_kube_config()

        self.k8s_core = client.CoreV1Api()
        self.k8s_apps = client.AppsV1Api()
        self.k8s_rbac = client.RbacAuthorizationV1Api()

    def _init_database(self):
        """Initialize database connection."""
        self.db_conn = psycopg2.connect(
            host=os.getenv('PLATFORM_DB_HOST'),
            port=os.getenv('PLATFORM_DB_PORT', 5432),
            database=os.getenv('PLATFORM_DB_NAME'),
            user=os.getenv('PLATFORM_DB_USER'),
            password=os.getenv('PLATFORM_DB_PASSWORD')
        )

    def _init_vault(self):
        """Initialize Vault client for secrets management."""
        self.vault = hvac.Client(
            url=os.getenv('VAULT_ADDR'),
            token=os.getenv('VAULT_TOKEN')
        )

    def provision(self) -> bool:
        """Execute complete tenant provisioning."""
        try:
            print(f"🚀 Provisioning tenant: {self.tenant_name}")

            # Step 1: Create Kubernetes namespace
            self._create_namespace()

            # Step 2: Set up RBAC
            self._setup_rbac()

            # Step 3: Create resource quotas
            self._create_resource_quotas()

            # Step 4: Deploy Airflow
            self._deploy_airflow()

            # Step 5: Create database schemas
            self._create_database_schemas()

            # Step 6: Configure secrets
            self._configure_secrets()

            # Step 7: Set up networking
            self._setup_networking()

            # Step 8: Deploy DAGs
            self._deploy_dags()

            # Step 9: Configure monitoring
            self._setup_monitoring()

            # Step 10: Validate deployment
            self._validate_deployment()

            print(f"✅ Tenant {self.tenant_name} provisioned successfully!")
            return True

        except Exception as e:
            print(f"❌ Provisioning failed: {e}")
            self._rollback()
            return False

    def _create_namespace(self):
        """Create Kubernetes namespace for tenant."""
        namespace_name = f"airflow-{self.tenant_name}"

        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels={
                    'tenant': self.tenant_name,
                    'environment': self.environment,
                    'tier': self.config['tenant']['tier'],
                    'managed-by': 'tenant-provisioner'
                },
                annotations={
                    'tenant/display-name': self.config['tenant']['display_name'],
                    'tenant/contact': self.config['tenant']['contacts']['technical'][0]['email']
                }
            )
        )

        try:
            self.k8s_core.create_namespace(namespace)
            print(f"  ✓ Created namespace: {namespace_name}")
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                print(f"  ℹ Namespace already exists: {namespace_name}")
            else:
                raise

    def _setup_rbac(self):
        """Set up RBAC for tenant isolation."""
        namespace = f"airflow-{self.tenant_name}"

        # Create service account
        service_account = client.V1ServiceAccount(
            metadata=client.V1ObjectMeta(
                name='airflow-worker',
                namespace=namespace
            )
        )
        self.k8s_core.create_namespaced_service_account(
            namespace=namespace,
            body=service_account
        )

        # Create role with tenant-specific permissions
        role = client.V1Role(
            metadata=client.V1ObjectMeta(
                name='airflow-worker-role',
                namespace=namespace
            ),
            rules=[
                client.V1PolicyRule(
                    api_groups=[''],
                    resources=['pods', 'pods/log', 'pods/exec'],
                    verbs=['*']
                ),
                client.V1PolicyRule(
                    api_groups=[''],
                    resources=['configmaps', 'secrets'],
                    verbs=['get', 'list']
                ),
                client.V1PolicyRule(
                    api_groups=['batch'],
                    resources=['jobs'],
                    verbs=['*']
                )
            ]
        )
        self.k8s_rbac.create_namespaced_role(
            namespace=namespace,
            body=role
        )

        # Create role binding
        role_binding = client.V1RoleBinding(
            metadata=client.V1ObjectMeta(
                name='airflow-worker-binding',
                namespace=namespace
            ),
            subjects=[
                client.V1Subject(
                    kind='ServiceAccount',
                    name='airflow-worker',
                    namespace=namespace
                )
            ],
            role_ref=client.V1RoleRef(
                api_group='rbac.authorization.k8s.io',
                kind='Role',
                name='airflow-worker-role'
            )
        )
        self.k8s_rbac.create_namespaced_role_binding(
            namespace=namespace,
            body=role_binding
        )

        print(f"  ✓ RBAC configured for namespace: {namespace}")

    def _create_resource_quotas(self):
        """Create resource quotas for tenant."""
        namespace = f"airflow-{self.tenant_name}"
        quotas = self.config['resources']['kubernetes']['quotas']

        resource_quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(
                name='tenant-quota',
                namespace=namespace
            ),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    'requests.cpu': quotas['requests']['cpu'],
                    'requests.memory': quotas['requests']['memory'],
                    'requests.storage': quotas['requests']['storage'],
                    'limits.cpu': quotas['limits']['cpu'],
                    'limits.memory': quotas['limits']['memory'],
                    'persistentvolumeclaims': '10',
                    'pods': quotas['requests']['pods'],
                    'services': '10'
                },
                scope_selector=client.V1ScopeSelector(
                    match_expressions=[
                        client.V1ScopedResourceSelectorRequirement(
                            operator='In',
                            scope_name='PriorityClass',
                            values=['tenant-priority']
                        )
                    ]
                )
            )
        )

        self.k8s_core.create_namespaced_resource_quota(
            namespace=namespace,
            body=resource_quota
        )

        # Create limit range for default pod resources
        limit_range = client.V1LimitRange(
            metadata=client.V1ObjectMeta(
                name='tenant-limits',
                namespace=namespace
            ),
            spec=client.V1LimitRangeSpec(
                limits=[
                    client.V1LimitRangeItem(
                        type='Container',
                        default={
                            'cpu': '1',
                            'memory': '1Gi'
                        },
                        default_request={
                            'cpu': '100m',
                            'memory': '128Mi'
                        },
                        max={
                            'cpu': '4',
                            'memory': '8Gi'
                        }
                    ),
                    client.V1LimitRangeItem(
                        type='PersistentVolumeClaim',
                        min={'storage': '1Gi'},
                        max={'storage': '100Gi'}
                    )
                ]
            )
        )

        self.k8s_core.create_namespaced_limit_range(
            namespace=namespace,
            body=limit_range
        )

        print(f"  ✓ Resource quotas created for namespace: {namespace}")

    def _deploy_airflow(self):
        """Deploy Airflow instance for tenant."""
        namespace = f"airflow-{self.tenant_name}"

        # Generate Helm values
        helm_values = self._generate_helm_values()

        # Save values to file
        values_path = f"/tmp/{self.tenant_name}-values.yaml"
        with open(values_path, 'w') as f:
            yaml.dump(helm_values, f)

        # Deploy using Helm
        cmd = [
            'helm', 'upgrade', '--install',
            f"airflow-{self.tenant_name}",
            'apache-airflow/airflow',
            '--namespace', namespace,
            '--create-namespace',
            '--values', values_path,
            '--version', '2.7.3',
            '--wait',
            '--timeout', '10m'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Helm deployment failed: {result.stderr}")

        print(f"  ✓ Airflow deployed for tenant: {self.tenant_name}")

    def _generate_helm_values(self) -> Dict[str, Any]:
        """Generate Helm values for Airflow deployment."""
        return {
            'airflow': {
                'image': {
                    'repository': 'registry.localhost/platform/airflow-base',
                    'tag': '3.0-10'
                },
                'config': {
                    'AIRFLOW__CORE__DAGS_FOLDER': '/opt/airflow/dags',
                    'AIRFLOW__CORE__EXECUTOR': 'KubernetesExecutor',
                    'AIRFLOW__CORE__LOAD_EXAMPLES': 'False',
                    'AIRFLOW__KUBERNETES__NAMESPACE': f"airflow-{self.tenant_name}",
                    'AIRFLOW__KUBERNETES__WORKER_SERVICE_ACCOUNT_NAME': 'airflow-worker',
                    'AIRFLOW__KUBERNETES__IN_CLUSTER': 'True',
                    'AIRFLOW__WEBSERVER__BASE_URL': f"https://airflow-{self.tenant_name}.company.com",
                    'AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX': 'True',
                    'AIRFLOW__API__AUTH_BACKENDS': 'airflow.api.auth.backend.session',
                    'AIRFLOW__CORE__PARALLELISM': '32',
                    'AIRFLOW__CORE__MAX_ACTIVE_TASKS_PER_DAG': '16',
                }
            },
            'scheduler': {
                'replicas': self.config['resources']['airflow']['scheduler']['replicas'],
                'resources': self.config['resources']['airflow']['scheduler']['resources']
            },
            'webserver': {
                'replicas': self.config['resources']['airflow']['webserver']['replicas'],
                'resources': self.config['resources']['airflow']['webserver']['resources']
            },
            'workers': {
                'resources': {
                    'requests': {
                        'cpu': '500m',
                        'memory': '1Gi'
                    },
                    'limits': {
                        'cpu': '2',
                        'memory': '4Gi'
                    }
                }
            },
            'postgresql': {
                'enabled': True,
                'postgresqlDatabase': f"airflow_{self.tenant_name}",
                'postgresqlUsername': f"airflow_{self.tenant_name}",
                'postgresqlPassword': self._generate_password(),
                'persistence': {
                    'enabled': True,
                    'size': '20Gi'
                }
            },
            'ingress': {
                'enabled': True,
                'web': {
                    'host': f"airflow-{self.tenant_name}.company.com",
                    'annotations': {
                        'kubernetes.io/ingress.class': 'nginx',
                        'cert-manager.io/cluster-issuer': 'letsencrypt-prod',
                        'nginx.ingress.kubernetes.io/auth-type': 'oauth2',
                        'nginx.ingress.kubernetes.io/auth-url': 'https://auth.company.com/oauth2/auth',
                        'nginx.ingress.kubernetes.io/auth-signin': 'https://auth.company.com/oauth2/start'
                    },
                    'tls': {
                        'enabled': True,
                        'secretName': f"airflow-{self.tenant_name}-tls"
                    }
                }
            }
        }

    def _create_database_schemas(self):
        """Create database schemas for tenant."""
        warehouse_config = self.config['warehouse']
        schema_prefix = warehouse_config['database']['schema_prefix']

        with self.db_conn.cursor() as cur:
            # Create warehouse database if needed
            db_name = warehouse_config['database']['name']
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cur.fetchone():
                cur.execute(f"CREATE DATABASE {db_name}")

            # Create schemas
            schemas = [
                f"{schema_prefix}bronze",
                f"{schema_prefix}silver",
                f"{schema_prefix}gold_mart",
                f"{schema_prefix}gold_reporting",
                f"{schema_prefix}staging",
                f"{schema_prefix}audit"
            ]

            for schema in schemas:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                cur.execute(f"GRANT ALL ON SCHEMA {schema} TO airflow_{self.tenant_name}")

            # Create audit table
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_prefix}audit.pipeline_runs (
                    run_id SERIAL PRIMARY KEY,
                    dag_id VARCHAR(255),
                    task_id VARCHAR(255),
                    execution_date TIMESTAMP,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    status VARCHAR(50),
                    rows_processed INTEGER,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.db_conn.commit()

        print(f"  ✓ Database schemas created for tenant: {self.tenant_name}")

    def _configure_secrets(self):
        """Configure secrets for tenant."""
        namespace = f"airflow-{self.tenant_name}"

        # Database credentials
        db_secret = client.V1Secret(
            metadata=client.V1ObjectMeta(
                name='database-credentials',
                namespace=namespace
            ),
            string_data={
                'SOURCE_DB_HOST': self.config['warehouse']['database']['host'],
                'SOURCE_DB_PORT': str(self.config['warehouse']['database']['port']),
                'SOURCE_DB_NAME': self.config['warehouse']['database']['name'],
                'SOURCE_DB_USER': f"etl_{self.tenant_name}",
                'SOURCE_DB_PASSWORD': self._generate_password(),
                'WAREHOUSE_DB_URL': self._get_warehouse_url()
            }
        )
        self.k8s_core.create_namespaced_secret(
            namespace=namespace,
            body=db_secret
        )

        # OAuth credentials if configured
        if self.config['tenant']['authentication']['type'] == 'oauth2':
            oauth_config = self.config['tenant']['authentication']['config']
            oauth_secret = client.V1Secret(
                metadata=client.V1ObjectMeta(
                    name='oauth-credentials',
                    namespace=namespace
                ),
                string_data={
                    'OAUTH_CLIENT_ID': self._resolve_vault_ref(oauth_config['client_id']),
                    'OAUTH_CLIENT_SECRET': self._resolve_vault_ref(oauth_config['client_secret']),
                    'OAUTH_REDIRECT_URI': oauth_config['redirect_uri']
                }
            )
            self.k8s_core.create_namespaced_secret(
                namespace=namespace,
                body=oauth_secret
            )

        # API keys for data sources
        for source in self.config['warehouse']['bronze_jobs']:
            if source['source'].startswith('api_'):
                api_secret = client.V1Secret(
                    metadata=client.V1ObjectMeta(
                        name=f"api-{source['source']}",
                        namespace=namespace
                    ),
                    string_data=self._get_api_credentials(source['source'])
                )
                self.k8s_core.create_namespaced_secret(
                    namespace=namespace,
                    body=api_secret
                )

        print(f"  ✓ Secrets configured for tenant: {self.tenant_name}")

    def _setup_networking(self):
        """Set up network policies for tenant isolation."""
        namespace = f"airflow-{self.tenant_name}"

        # Default deny all ingress except from same namespace
        network_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name='tenant-isolation',
                namespace=namespace
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(),  # All pods
                policy_types=['Ingress', 'Egress'],
                ingress=[
                    client.V1NetworkPolicyIngressRule(
                        from_=[
                            client.V1NetworkPolicyPeer(
                                pod_selector=client.V1LabelSelector()  # Same namespace
                            ),
                            client.V1NetworkPolicyPeer(
                                namespace_selector=client.V1LabelSelector(
                                    match_labels={'name': 'ingress-nginx'}  # Ingress controller
                                )
                            )
                        ]
                    )
                ],
                egress=[
                    client.V1NetworkPolicyEgressRule(
                        to=[
                            client.V1NetworkPolicyPeer(
                                pod_selector=client.V1LabelSelector()  # Same namespace
                            )
                        ]
                    ),
                    client.V1NetworkPolicyEgressRule(
                        ports=[
                            client.V1NetworkPolicyPort(
                                protocol='TCP',
                                port=5432  # Database
                            ),
                            client.V1NetworkPolicyPort(
                                protocol='TCP',
                                port=443  # HTTPS APIs
                            ),
                            client.V1NetworkPolicyPort(
                                protocol='UDP',
                                port=53  # DNS
                            )
                        ]
                    )
                ]
            )
        )

        self.k8s_core.create_namespaced_network_policy(
            namespace=namespace,
            body=network_policy
        )

        print(f"  ✓ Network policies configured for tenant: {self.tenant_name}")

    def _deploy_dags(self):
        """Deploy DAGs for tenant."""
        # Generate DAG from configuration
        dag_code = self._generate_tenant_dag()

        # Create ConfigMap with DAG
        namespace = f"airflow-{self.tenant_name}"
        dag_configmap = client.V1ConfigMap(
            metadata=client.V1ObjectMeta(
                name='tenant-dags',
                namespace=namespace
            ),
            data={
                f"{self.tenant_name}_pipeline.py": dag_code
            }
        )

        self.k8s_core.create_namespaced_config_map(
            namespace=namespace,
            body=dag_configmap
        )

        # Mount ConfigMap in Airflow pods (requires pod restart)
        # This would typically be done through Helm values

        print(f"  ✓ DAGs deployed for tenant: {self.tenant_name}")

    def _generate_tenant_dag(self) -> str:
        """Generate DAG code from tenant configuration."""
        bronze_jobs = self.config['warehouse']['bronze_jobs']
        dbt_config = self.config['warehouse'].get('dbt', {})

        dag_code = f"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.operators.dummy import DummyOperator

default_args = {{
    'owner': '{self.tenant_name}',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}}

dag = DAG(
    '{self.tenant_name}_warehouse_pipeline',
    default_args=default_args,
    description='Warehouse pipeline for {self.config["tenant"]["display_name"]}',
    schedule_interval='@daily',
    catchup=False,
    tags=['{self.tenant_name}', 'warehouse', 'production'],
)

# Bronze extraction tasks
bronze_tasks = []
"""

        for job in bronze_jobs:
            dag_code += f"""
extract_{job['name']} = KubernetesPodOperator(
    task_id='extract_{job['name']}',
    namespace='airflow-{self.tenant_name}',
    image='registry.localhost/etl/{job['source']}-runner:latest',
    cmds=['python', '-m', 'datakit.extract'],
    arguments=['--table', '{job['name']}'],
    env_from=[
        {{'secret_ref': {{'name': 'database-credentials'}}}}
    ],
    service_account_name='airflow-worker',
    is_delete_operator_pod=True,
    in_cluster=True,
    dag=dag,
)
bronze_tasks.append(extract_{job['name']})
"""

        if dbt_config.get('silver', {}).get('enabled'):
            dag_code += """
# Silver transformation
transform_silver = KubernetesPodOperator(
    task_id='transform_silver',
    namespace='airflow-{0}',
    image='registry.localhost/analytics/dbt-runner:latest',
    cmds=['dbt', 'run'],
    arguments=['--select', 'tag:silver', '--profiles-dir', '/profiles'],
    env_from=[
        {{'secret_ref': {{'name': 'database-credentials'}}}}
    ],
    service_account_name='airflow-worker',
    is_delete_operator_pod=True,
    in_cluster=True,
    dag=dag,
)

bronze_tasks >> transform_silver
""".format(self.tenant_name)

        if dbt_config.get('gold', {}).get('enabled'):
            dag_code += """
# Gold transformation
transform_gold = KubernetesPodOperator(
    task_id='transform_gold',
    namespace='airflow-{0}',
    image='registry.localhost/analytics/dbt-runner:latest',
    cmds=['dbt', 'run'],
    arguments=['--select', 'tag:gold', '--profiles-dir', '/profiles'],
    env_from=[
        {{'secret_ref': {{'name': 'database-credentials'}}}}
    ],
    service_account_name='airflow-worker',
    is_delete_operator_pod=True,
    in_cluster=True,
    dag=dag,
)

transform_silver >> transform_gold
""".format(self.tenant_name)

        return dag_code

    def _setup_monitoring(self):
        """Set up monitoring for tenant."""
        namespace = f"airflow-{self.tenant_name}"

        # Create ServiceMonitor for Prometheus
        service_monitor = {
            'apiVersion': 'monitoring.coreos.com/v1',
            'kind': 'ServiceMonitor',
            'metadata': {
                'name': f"airflow-{self.tenant_name}",
                'namespace': namespace,
                'labels': {
                    'tenant': self.tenant_name,
                    'monitoring': 'prometheus'
                }
            },
            'spec': {
                'selector': {
                    'matchLabels': {
                        'app': 'airflow'
                    }
                },
                'endpoints': [
                    {
                        'port': 'metrics',
                        'interval': '30s',
                        'path': '/metrics'
                    }
                ]
            }
        }

        # Apply using kubectl (ServiceMonitor is a CRD)
        import json
        cmd = ['kubectl', 'apply', '-f', '-']
        subprocess.run(cmd, input=json.dumps(service_monitor), text=True)

        # Create Grafana dashboard
        dashboard = self._generate_grafana_dashboard()
        self._upload_grafana_dashboard(dashboard)

        print(f"  ✓ Monitoring configured for tenant: {self.tenant_name}")

    def _generate_grafana_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana dashboard for tenant."""
        return {
            'dashboard': {
                'title': f"Airflow - {self.config['tenant']['display_name']}",
                'tags': ['airflow', self.tenant_name],
                'timezone': 'UTC',
                'panels': [
                    {
                        'title': 'DAG Success Rate',
                        'targets': [
                            {
                                'expr': f'rate(airflow_dag_success{{namespace="airflow-{self.tenant_name}"}}[5m])'
                            }
                        ]
                    },
                    {
                        'title': 'Task Duration',
                        'targets': [
                            {
                                'expr': f'histogram_quantile(0.95, airflow_task_duration{{namespace="airflow-{self.tenant_name}"}})'
                            }
                        ]
                    },
                    {
                        'title': 'Resource Usage',
                        'targets': [
                            {
                                'expr': f'sum(container_memory_usage_bytes{{namespace="airflow-{self.tenant_name}"}}) / 1024 / 1024 / 1024'
                            }
                        ]
                    }
                ]
            },
            'folderId': 0,
            'overwrite': True
        }

    def _validate_deployment(self):
        """Validate that tenant is properly deployed."""
        namespace = f"airflow-{self.tenant_name}"
        checks = []

        # Check namespace exists
        try:
            self.k8s_core.read_namespace(namespace)
            checks.append(('Namespace exists', True))
        except:
            checks.append(('Namespace exists', False))

        # Check pods are running
        pods = self.k8s_core.list_namespaced_pod(namespace)
        running_pods = [p for p in pods.items if p.status.phase == 'Running']
        checks.append(('Pods running', len(running_pods) > 0))

        # Check database connectivity
        try:
            with self.db_conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM pg_namespace WHERE nspname = '{self.config['warehouse']['database']['schema_prefix']}bronze'")
                checks.append(('Database schemas exist', cur.fetchone() is not None))
        except:
            checks.append(('Database schemas exist', False))

        # Check Airflow webserver is accessible
        import requests
        try:
            response = requests.get(
                f"https://airflow-{self.tenant_name}.company.com/health",
                timeout=5
            )
            checks.append(('Airflow accessible', response.status_code == 200))
        except:
            checks.append(('Airflow accessible', False))

        # Print validation results
        print("\n📋 Validation Results:")
        for check, passed in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")

        if not all(passed for _, passed in checks):
            raise Exception("Validation failed")

    def _rollback(self):
        """Rollback tenant provisioning on failure."""
        print(f"⚠️ Rolling back tenant: {self.tenant_name}")

        namespace = f"airflow-{self.tenant_name}"

        try:
            # Delete namespace (will cascade delete all resources)
            self.k8s_core.delete_namespace(namespace)

            # Drop database schemas
            with self.db_conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {self.config['warehouse']['database']['schema_prefix']}bronze CASCADE")
                cur.execute(f"DROP SCHEMA IF EXISTS {self.config['warehouse']['database']['schema_prefix']}silver CASCADE")
                cur.execute(f"DROP SCHEMA IF EXISTS {self.config['warehouse']['database']['schema_prefix']}gold_mart CASCADE")
                self.db_conn.commit()

            # Remove from Vault
            self.vault.delete(f"secret/tenants/{self.tenant_name}")

            print(f"  ✓ Rollback completed for tenant: {self.tenant_name}")

        except Exception as e:
            print(f"  ✗ Rollback failed: {e}")

    def _generate_password(self) -> str:
        """Generate secure password for tenant."""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(secrets.choice(alphabet) for _ in range(32))

    def _resolve_vault_ref(self, value: str) -> str:
        """Resolve Vault reference like {{ vault.get('path') }}."""
        if value.startswith('{{ vault.get'):
            import re
            match = re.search(r"vault\.get\('([^']+)'\)", value)
            if match:
                path = match.group(1)
                secret = self.vault.read(f"secret/{path}")
                return secret['data']['value']
        return value

    def _get_warehouse_url(self) -> str:
        """Get warehouse database URL."""
        config = self.config['warehouse']['database']
        return f"postgresql://etl_{self.tenant_name}:password@{config['host']}:{config['port']}/{config['name']}"

    def _get_api_credentials(self, source: str) -> Dict[str, str]:
        """Get API credentials for data source."""
        # This would fetch from Vault or another secure store
        return {
            'API_KEY': self.vault.read(f"secret/apis/{source}/key")['data']['value'],
            'API_SECRET': self.vault.read(f"secret/apis/{source}/secret")['data']['value']
        }

    def _upload_grafana_dashboard(self, dashboard: Dict[str, Any]):
        """Upload dashboard to Grafana."""
        import requests

        grafana_url = os.getenv('GRAFANA_URL', 'http://grafana.monitoring.svc.cluster.local')
        grafana_token = os.getenv('GRAFANA_API_TOKEN')

        response = requests.post(
            f"{grafana_url}/api/dashboards/db",
            json=dashboard,
            headers={
                'Authorization': f"Bearer {grafana_token}",
                'Content-Type': 'application/json'
            }
        )

        if response.status_code != 200:
            print(f"  ⚠️ Failed to upload Grafana dashboard: {response.text}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Provision tenant for multi-tenant Airflow')
    parser.add_argument('config', help='Path to tenant configuration YAML')
    parser.add_argument('--environment', default='production', help='Target environment')
    parser.add_argument('--dry-run', action='store_true', help='Validate without provisioning')

    args = parser.parse_args()

    provisioner = TenantProvisioner(args.config, args.environment)

    if args.dry_run:
        print("🔍 Dry run mode - validating configuration only")
        # Validate configuration without provisioning
    else:
        success = provisioner.provision()
        exit(0 if success else 1)
```

## 🔒 Security & Isolation

### **Network Isolation**

```yaml
# k8s/network-policies/tenant-isolation.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-isolation-strict
  namespace: airflow-{{ tenant_name }}
spec:
  podSelector: {}  # Apply to all pods in namespace
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Allow from same namespace only
    - from:
        - podSelector: {}

    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
        - podSelector:
            matchLabels:
              app.kubernetes.io/name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8080

  egress:
    # Allow to same namespace
    - to:
        - podSelector: {}

    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53

    # Allow to specific databases only
    - to:
        - ipBlock:
            cidr: 10.0.0.0/8
            except:
              - 10.0.1.0/24  # Exclude other tenant subnets
      ports:
        - protocol: TCP
          port: 5432

    # Allow to specific APIs
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
            except:
              - 10.0.0.0/8
              - 192.168.0.0/16
              - 172.16.0.0/12
      ports:
        - protocol: TCP
          port: 443
```

### **Database Isolation**

```sql
-- Create tenant-specific database user
CREATE USER etl_acme WITH PASSWORD 'secure_password';

-- Create tenant-specific schemas
CREATE SCHEMA acme_bronze;
CREATE SCHEMA acme_silver;
CREATE SCHEMA acme_gold_mart;
CREATE SCHEMA acme_staging;

-- Grant permissions only to tenant schemas
GRANT ALL PRIVILEGES ON SCHEMA acme_bronze TO etl_acme;
GRANT ALL PRIVILEGES ON SCHEMA acme_silver TO etl_acme;
GRANT ALL PRIVILEGES ON SCHEMA acme_gold_mart TO etl_acme;
GRANT ALL PRIVILEGES ON SCHEMA acme_staging TO etl_acme;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA acme_bronze
    GRANT ALL ON TABLES TO etl_acme;
ALTER DEFAULT PRIVILEGES IN SCHEMA acme_silver
    GRANT ALL ON TABLES TO etl_acme;

-- Row-level security for shared tables
CREATE POLICY tenant_isolation ON shared_metadata
    FOR ALL
    TO etl_acme
    USING (tenant_id = 'acme');

-- Enable row-level security
ALTER TABLE shared_metadata ENABLE ROW LEVEL SECURITY;
```

## 📊 Monitoring & Metering

### **Tenant Metrics Collection**

```python
# monitoring/tenant_metrics.py
from prometheus_client import Gauge, Counter, Histogram
import psutil
import docker
from kubernetes import client, config

# Define metrics
tenant_cpu_usage = Gauge(
    'tenant_cpu_usage_cores',
    'CPU usage per tenant',
    ['tenant', 'namespace']
)

tenant_memory_usage = Gauge(
    'tenant_memory_usage_bytes',
    'Memory usage per tenant',
    ['tenant', 'namespace']
)

tenant_task_count = Counter(
    'tenant_task_total',
    'Total tasks executed per tenant',
    ['tenant', 'dag', 'task', 'status']
)

tenant_task_duration = Histogram(
    'tenant_task_duration_seconds',
    'Task execution duration per tenant',
    ['tenant', 'dag', 'task'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

tenant_data_processed = Counter(
    'tenant_data_processed_bytes',
    'Data processed per tenant',
    ['tenant', 'source', 'destination']
)

class TenantMetricsCollector:
    """Collect and export tenant metrics."""

    def __init__(self):
        config.load_incluster_config()
        self.k8s = client.CoreV1Api()
        self.docker = docker.from_env()

    def collect_metrics(self):
        """Collect metrics for all tenants."""

        # Get all tenant namespaces
        namespaces = self.k8s.list_namespace(
            label_selector='managed-by=tenant-provisioner'
        )

        for ns in namespaces.items:
            tenant = ns.metadata.labels['tenant']
            namespace = ns.metadata.name

            # Collect resource metrics
            self._collect_resource_metrics(tenant, namespace)

            # Collect task metrics
            self._collect_task_metrics(tenant, namespace)

            # Collect data metrics
            self._collect_data_metrics(tenant, namespace)

    def _collect_resource_metrics(self, tenant: str, namespace: str):
        """Collect resource usage metrics."""

        # Get pods in namespace
        pods = self.k8s.list_namespaced_pod(namespace)

        total_cpu = 0
        total_memory = 0

        for pod in pods.items:
            if pod.status.phase == 'Running':
                # Get container metrics
                for container in pod.spec.containers:
                    # Parse resource requests/limits
                    if container.resources.requests:
                        cpu = container.resources.requests.get('cpu', '0')
                        memory = container.resources.requests.get('memory', '0')

                        # Convert to standard units
                        total_cpu += self._parse_cpu(cpu)
                        total_memory += self._parse_memory(memory)

        tenant_cpu_usage.labels(
            tenant=tenant,
            namespace=namespace
        ).set(total_cpu)

        tenant_memory_usage.labels(
            tenant=tenant,
            namespace=namespace
        ).set(total_memory)
```

## 🎯 Best Practices

### **1. Tenant Onboarding Checklist**

```markdown
## New Tenant Onboarding Checklist

### Pre-Provisioning
- [ ] Validate business approval
- [ ] Review resource requirements
- [ ] Confirm SLA tier
- [ ] Collect technical contacts
- [ ] Verify data source access

### Technical Setup
- [ ] Create tenant configuration YAML
- [ ] Validate configuration
- [ ] Run provisioning script
- [ ] Verify deployment
- [ ] Configure monitoring

### Access Configuration
- [ ] Set up authentication (OAuth/SAML)
- [ ] Create user accounts
- [ ] Configure RBAC
- [ ] Test access

### Data Pipeline Setup
- [ ] Configure data sources
- [ ] Deploy DAGs
- [ ] Test bronze extraction
- [ ] Validate silver transformations
- [ ] Verify gold layer

### Validation
- [ ] Run end-to-end test
- [ ] Verify data quality
- [ ] Check monitoring
- [ ] Test alerting
- [ ] Validate billing

### Handover
- [ ] Document access details
- [ ] Provide training
- [ ] Share runbooks
- [ ] Schedule review meeting
- [ ] Get sign-off
```

### **2. Tenant Maintenance**

```bash
# Regular maintenance tasks
#!/bin/bash

# Daily tasks
check_tenant_health() {
    tenant=$1
    namespace="airflow-${tenant}"

    # Check pod status
    kubectl get pods -n $namespace

    # Check resource usage
    kubectl top pods -n $namespace

    # Check recent errors
    kubectl logs -n $namespace -l app=airflow --tail=100 | grep ERROR

    # Check data freshness
    psql $WAREHOUSE_DB -c "
        SELECT
            schema_name,
            MAX(modified_at) as last_update,
            NOW() - MAX(modified_at) as age
        FROM information_schema.tables
        WHERE schema_name LIKE '${tenant}_%'
        GROUP BY schema_name
    "
}

# Weekly tasks
optimize_tenant_resources() {
    tenant=$1

    # Analyze resource usage patterns
    prometheus_query="
        avg_over_time(tenant_cpu_usage_cores{tenant='$tenant'}[7d])
    "

    # Adjust resource quotas if needed
    # ...
}

# Monthly tasks
audit_tenant_access() {
    tenant=$1

    # Review user access
    # Check for unused credentials
    # Rotate secrets
    # ...
}
```

## 🔗 Related Documentation

- **[Architecture Overview](architecture-overview.md)** - System design
- **[Container Orchestration](container-orchestration.md)** - Docker/Kubernetes patterns
- **[Authentication & Security](authentication-kerberos.md)** - Security patterns
- **[Performance & Scaling](performance-scaling.md)** - Optimization strategies
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues

---

*Next: Learn about [Creating Datakits](creating-datakits.md) for custom data extraction.*