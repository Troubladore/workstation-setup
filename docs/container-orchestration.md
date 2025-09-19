# Container Orchestration: DockerOperator to KubernetesPodOperator

A comprehensive guide to understanding, implementing, and mastering the container orchestration strategy that enables true development-production parity in our Astronomer Airflow platform.

## 🎯 The Core Innovation

Our container orchestration strategy solves a fundamental challenge in data engineering: **How do you ensure that what works on a developer's laptop will work identically in production?**

The answer: **Use the exact same container images everywhere, with operators that adapt to the environment.**

```python
# The same image, two environments
IMAGE = "registry.localhost/etl/postgres-runner:0.1.0"

# Local Development
if ENVIRONMENT == "local":
    task = DockerOperator(
        image=IMAGE,
        command=["extract", "--table", "customers"]
    )

# Production
elif ENVIRONMENT == "production":
    task = KubernetesPodOperator(
        image=IMAGE,
        cmds=["extract", "--table", "customers"]
    )
```

## 📚 Foundation Concepts

### **What is Container Orchestration?**

Container orchestration is the automated management of containerized applications, including:
- **Scheduling**: Deciding when and where containers run
- **Scaling**: Adjusting container count based on load
- **Networking**: Enabling container communication
- **Storage**: Managing persistent data
- **Health**: Monitoring and restarting failed containers

### **Why Containers?**

Containers provide:
1. **Isolation**: Dependencies don't conflict
2. **Portability**: Run anywhere
3. **Reproducibility**: Same behavior every time
4. **Versioning**: Precise control over deployments
5. **Efficiency**: Lighter than virtual machines

### **The Operator Pattern**

Airflow operators are the bridge between orchestration and execution:
```
Airflow Scheduler → Operator → Container Runtime → Your Code
```

## 🐳 DockerOperator: Local Development

### **Architecture**

```
┌─────────────────────────────────────────────────────┐
│                 Airflow Worker                       │
│                                                      │
│  ┌────────────────────────────────────────────┐     │
│  │            DockerOperator Task             │     │
│  │                                             │     │
│  │  1. Parse parameters                        │     │
│  │  2. Pull image if needed                    │     │
│  │  3. Create container                        │     │
│  │  4. Attach to networks                      │     │
│  │  5. Mount volumes                           │     │
│  │  6. Set environment variables               │     │
│  │  7. Execute command                         │     │
│  │  8. Stream logs                             │     │
│  │  9. Capture exit code                       │     │
│  │  10. Clean up container                     │     │
│  └────────────────┬────────────────────────────┘     │
│                   │                                  │
└───────────────────┼──────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │    Docker Daemon     │
         │                      │
         │  ┌──────────────┐   │
         │  │  Container   │   │
         │  │              │   │
         │  │  Your Code   │   │
         │  └──────────────┘   │
         └──────────────────────┘
```

### **Complete DockerOperator Configuration**

```python
from airflow.providers.docker.operators.docker import DockerOperator
from datetime import datetime, timedelta

# Full example with all parameters
extract_task = DockerOperator(
    task_id='extract_customers',

    # Container configuration
    image='registry.localhost/etl/postgres-runner:0.1.0',
    api_version='auto',
    auto_remove=True,  # Remove container after completion

    # Command and arguments
    command=['python', '-m', 'datakit.extract'],
    entrypoint=None,  # Use image's ENTRYPOINT

    # Environment variables
    environment={
        'SOURCE_DB_HOST': '{{ var.value.source_host }}',
        'SOURCE_DB_PORT': '{{ var.value.source_port }}',
        'SOURCE_DB_NAME': '{{ var.value.source_database }}',
        'SOURCE_DB_USER': '{{ var.value.source_user }}',
        'SOURCE_DB_PASSWORD': '{{ conn.source_db.password }}',
        'TARGET_SCHEMA': 'bronze',
        'LOG_LEVEL': 'INFO',
    },

    # Networking
    docker_url='unix://var/run/docker.sock',
    network_mode='edge',  # Use custom network
    extra_hosts={
        'warehouse.internal': '172.17.0.1',  # Map internal hostnames
    },

    # Volumes and mounts
    volumes=[
        '/data/shared:/shared:ro',  # Read-only mount
        'named_volume:/data:rw',     # Named volume
    ],
    mounts=[
        Mount(
            source='airflow_logs',
            target='/airflow/logs',
            type='volume',
            read_only=False
        )
    ],

    # Resources
    mem_limit='2g',
    mem_reservation='1g',
    cpu_quota=100000,  # Microseconds per period

    # Security
    user='1000:1000',  # Run as specific user
    cap_add=['SYS_PTRACE'],  # Add capabilities if needed
    privileged=False,

    # Execution control
    force_pull=False,  # Don't always pull
    tty=True,  # Allocate pseudo-TTY
    xcom_all=False,  # Don't push all stdout to XCom
    retrieve_output=True,  # Capture last line for XCom
    retrieve_output_path='/tmp/output.json',  # Or read from file

    # Error handling
    on_failure_callback=alert_on_failure,
    retries=3,
    retry_delay=timedelta(minutes=5),

    dag=dag
)
```

### **Volume Management Strategies**

```python
# Strategy 1: Shared data volume
shared_data_extract = DockerOperator(
    task_id='extract_to_shared',
    image='registry.localhost/etl/extractor:0.1.0',
    volumes=['shared_data:/data'],
    command=['extract', '--output', '/data/extract.parquet']
)

shared_data_transform = DockerOperator(
    task_id='transform_from_shared',
    image='registry.localhost/etl/transformer:0.1.0',
    volumes=['shared_data:/data:ro'],  # Read-only access
    command=['transform', '--input', '/data/extract.parquet']
)

# Strategy 2: Database as integration point
bronze_load = DockerOperator(
    task_id='load_bronze',
    image='registry.localhost/etl/loader:0.1.0',
    environment={
        'DB_URL': 'postgresql://user:pass@host/warehouse'
    },
    command=['load', '--table', 'bronze.raw_data']
)

# Strategy 3: Object storage (MinIO/S3)
s3_extract = DockerOperator(
    task_id='extract_to_s3',
    image='registry.localhost/etl/s3-extractor:0.1.0',
    environment={
        'S3_ENDPOINT': 'http://minio:9000',
        'S3_ACCESS_KEY': '{{ var.value.s3_access_key }}',
        'S3_SECRET_KEY': '{{ var.value.s3_secret_key }}',
    },
    command=['extract', '--bucket', 'bronze', '--key', 'data.parquet']
)
```

### **Network Configuration**

```yaml
# docker-compose.override.yml for Airflow
version: '3.8'

networks:
  edge:
    external: true
  internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

services:
  scheduler:
    networks:
      - edge
      - internal
      - default

  worker:
    networks:
      - edge
      - internal
      - default
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      DOCKER_HOST: unix:///var/run/docker.sock
```

### **Debugging DockerOperator Issues**

```python
# Enable verbose logging
debug_task = DockerOperator(
    task_id='debug_extraction',
    image='registry.localhost/etl/debugger:0.1.0',
    command=['sh', '-c', '''
        echo "Starting debug..."
        echo "Environment:" && env | sort
        echo "Network:" && ip addr
        echo "DNS:" && nslookup warehouse.internal
        echo "Disk:" && df -h
        echo "Memory:" && free -m
        python -m datakit.extract --debug
    '''],
    tty=True,
    dag=dag
)

# Interactive debugging
interactive_debug = BashOperator(
    task_id='interactive_shell',
    bash_command='''
        docker run -it --rm \
            --network edge \
            --entrypoint /bin/bash \
            registry.localhost/etl/debugger:0.1.0
    ''',
    dag=dag
)
```

## ☸️ KubernetesPodOperator: Production

### **Architecture**

```
┌─────────────────────────────────────────────────────┐
│              Airflow Scheduler Pod                   │
│                                                      │
│  ┌────────────────────────────────────────────┐     │
│  │        KubernetesPodOperator Task          │     │
│  │                                             │     │
│  │  1. Generate pod specification              │     │
│  │  2. Apply pod template                      │     │
│  │  3. Create pod in Kubernetes                │     │
│  │  4. Wait for pod scheduling                 │     │
│  │  5. Monitor pod status                      │     │
│  │  6. Stream pod logs                         │     │
│  │  7. Capture exit code                       │     │
│  │  8. Extract XCom values                     │     │
│  │  9. Clean up pod (if configured)            │     │
│  └────────────────┬────────────────────────────┘     │
│                   │                                  │
└───────────────────┼──────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │   Kubernetes API     │
         └──────────┬───────────┘
                    │
         ┌──────────▼──────────┐
         │   Kubernetes Node    │
         │                      │
         │  ┌──────────────┐   │
         │  │     Pod      │   │
         │  │              │   │
         │  │ ┌──────────┐ │   │
         │  │ │Container │ │   │
         │  │ │Your Code │ │   │
         │  │ └──────────┘ │   │
         │  └──────────────┘   │
         └──────────────────────┘
```

### **Complete KubernetesPodOperator Configuration**

```python
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from kubernetes.client import models as k8s

# Full example with all parameters
extract_task = KubernetesPodOperator(
    task_id='extract_customers',

    # Pod identification
    name='extract-customers-{{ ds }}-{{ task_instance.try_number }}',
    namespace='airflow-production',

    # Container configuration
    image='registry.mycompany.com/etl/postgres-runner:0.1.0',
    image_pull_policy='IfNotPresent',
    cmds=['python', '-m', 'datakit.extract'],
    arguments=['--table', 'customers', '--date', '{{ ds }}'],

    # Environment variables
    env_vars={
        'SOURCE_DB_HOST': '{{ var.value.source_host }}',
        'SOURCE_DB_PORT': '{{ var.value.source_port }}',
        'LOG_LEVEL': 'INFO',
    },

    # Secrets
    secrets=[
        k8s.V1EnvFromSource(
            secret_ref=k8s.V1SecretEnvSource(
                name='database-credentials'
            )
        ),
    ],
    env_from=[
        k8s.V1EnvFromSource(
            config_map_ref=k8s.V1ConfigMapEnvSource(
                name='app-config'
            )
        )
    ],

    # Resources
    resources=k8s.V1ResourceRequirements(
        requests={
            'memory': '1Gi',
            'cpu': '500m',
            'ephemeral-storage': '2Gi'
        },
        limits={
            'memory': '2Gi',
            'cpu': '1000m',
            'ephemeral-storage': '5Gi'
        }
    ),

    # Volumes
    volumes=[
        k8s.V1Volume(
            name='shared-data',
            persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                claim_name='airflow-shared-pvc'
            )
        ),
        k8s.V1Volume(
            name='temp',
            empty_dir=k8s.V1EmptyDirVolumeSource()
        ),
    ],
    volume_mounts=[
        k8s.V1VolumeMount(
            name='shared-data',
            mount_path='/shared',
            read_only=False
        ),
        k8s.V1VolumeMount(
            name='temp',
            mount_path='/tmp'
        ),
    ],

    # Security context
    security_context=k8s.V1SecurityContext(
        run_as_user=1000,
        run_as_group=1000,
        fs_group=1000,
        run_as_non_root=True,
        capabilities=k8s.V1Capabilities(
            drop=['ALL'],
            add=['NET_BIND_SERVICE']
        )
    ),

    # Pod configuration
    pod_template_file='path/to/pod-template.yaml',
    full_pod_spec=None,  # Or provide complete spec

    # Scheduling
    affinity={
        'nodeAffinity': {
            'requiredDuringSchedulingIgnoredDuringExecution': {
                'nodeSelectorTerms': [{
                    'matchExpressions': [{
                        'key': 'node-type',
                        'operator': 'In',
                        'values': ['data-processing']
                    }]
                }]
            }
        },
        'podAntiAffinity': {
            'preferredDuringSchedulingIgnoredDuringExecution': [{
                'weight': 100,
                'podAffinityTerm': {
                    'labelSelector': {
                        'matchExpressions': [{
                            'key': 'app',
                            'operator': 'In',
                            'values': ['heavy-processing']
                        }]
                    },
                    'topologyKey': 'kubernetes.io/hostname'
                }
            }]
        }
    },

    tolerations=[
        k8s.V1Toleration(
            key='dedicated',
            operator='Equal',
            value='data-processing',
            effect='NoSchedule'
        )
    ],

    # Service account and RBAC
    service_account_name='airflow-worker',
    automount_service_account_token=True,

    # Networking
    host_network=False,
    dns_policy='ClusterFirst',
    dns_config=k8s.V1PodDNSConfig(
        nameservers=['8.8.8.8'],
        searches=['svc.cluster.local']
    ),

    # Execution control
    get_logs=True,
    log_events_on_failure=True,
    do_xcom_push=True,
    is_delete_operator_pod=True,
    startup_timeout_seconds=300,

    # Kubernetes configuration
    in_cluster=True,  # Use in-cluster config
    cluster_context=None,  # Or specify context
    config_file=None,  # Or path to kubeconfig

    # Labels and annotations
    labels={
        'app': 'airflow',
        'task': 'extract',
        'environment': 'production',
        'team': 'data-engineering'
    },
    annotations={
        'prometheus.io/scrape': 'true',
        'prometheus.io/port': '9090',
        'datadog.com/log-processing-pipeline': 'etl'
    },

    # Priority
    priority_class_name='high-priority',

    # Retry and error handling
    retries=3,
    retry_delay=timedelta(minutes=5),
    on_failure_callback=alert_team,

    dag=dag
)
```

### **Pod Template Management**

```yaml
# k8s/pod-templates/data-processing-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: placeholder
  labels:
    app: airflow-worker
    tier: data-processing
spec:
  initContainers:
    - name: init-permissions
      image: busybox:1.35
      command: ['sh', '-c', 'chown -R 1000:1000 /shared']
      volumeMounts:
        - name: shared-data
          mountPath: /shared

    - name: wait-for-db
      image: busybox:1.35
      command: ['sh', '-c', 'until nc -z postgres-service 5432; do sleep 1; done']

  containers:
    - name: base  # Will be replaced by KPO
      image: placeholder
      resources:
        requests:
          memory: "1Gi"
          cpu: "500m"
        limits:
          memory: "2Gi"
          cpu: "1000m"

  sidecars:
    - name: log-shipper
      image: fluentbit/fluent-bit:2.0
      volumeMounts:
        - name: logs
          mountPath: /logs

    - name: metrics-exporter
      image: prom/node-exporter:v1.5.0
      ports:
        - containerPort: 9100

  volumes:
    - name: shared-data
      persistentVolumeClaim:
        claimName: airflow-shared-pvc
    - name: logs
      emptyDir: {}
    - name: credentials
      secret:
        secretName: database-credentials

  nodeSelector:
    workload: data-processing

  tolerations:
    - key: "dedicated"
      operator: "Equal"
      value: "data-processing"
      effect: "NoSchedule"

  serviceAccountName: airflow-worker
  automountServiceAccountToken: true

  dnsPolicy: ClusterFirst
  restartPolicy: Never

  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    runAsNonRoot: true
```

### **Kubernetes Secrets and ConfigMaps**

```yaml
# k8s/secrets/database-credentials.yaml
apiVersion: v1
kind: Secret
metadata:
  name: database-credentials
  namespace: airflow-production
type: Opaque
stringData:
  SOURCE_DB_USER: "etl_user"
  SOURCE_DB_PASSWORD: "supersecretpassword"
  TARGET_DB_USER: "warehouse_user"
  TARGET_DB_PASSWORD: "anothersecretpassword"

---
# k8s/configmaps/app-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: airflow-production
data:
  SOURCE_DB_HOST: "source-db.internal.com"
  SOURCE_DB_PORT: "5432"
  SOURCE_DB_NAME: "operational"
  TARGET_DB_HOST: "warehouse-db.internal.com"
  TARGET_DB_PORT: "5432"
  TARGET_DB_NAME: "analytics"
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
```

```python
# Using in KubernetesPodOperator
task_with_secrets = KubernetesPodOperator(
    task_id='secure_extraction',
    secrets=[
        # Mount as environment variables
        k8s.V1EnvVar(
            name='DB_PASSWORD',
            value_from=k8s.V1EnvVarSource(
                secret_key_ref=k8s.V1SecretKeySelector(
                    name='database-credentials',
                    key='SOURCE_DB_PASSWORD'
                )
            )
        ),
        # Mount as file
        k8s.V1Volume(
            name='db-creds',
            secret=k8s.V1SecretVolumeSource(
                secret_name='database-credentials',
                items=[
                    k8s.V1KeyToPath(
                        key='SOURCE_DB_PASSWORD',
                        path='db_password.txt'
                    )
                ]
            )
        )
    ],
    volume_mounts=[
        k8s.V1VolumeMount(
            name='db-creds',
            mount_path='/secrets',
            read_only=True
        )
    ]
)
```

## 🔄 Achieving Operator Parity

### **The Abstraction Pattern**

Create a wrapper that automatically selects the right operator:

```python
# operators/adaptive_operator.py
import os
from typing import Dict, List, Any, Optional
from airflow.models import BaseOperator

def create_container_operator(
    task_id: str,
    image: str,
    command: List[str],
    environment: Dict[str, str],
    **kwargs
) -> BaseOperator:
    """
    Create the appropriate container operator based on environment.

    This function maintains complete parity between local and production
    by translating parameters appropriately for each operator type.
    """

    # Detect environment
    environment_type = os.getenv('AIRFLOW_ENVIRONMENT', 'local')

    if environment_type == 'local':
        from airflow.providers.docker.operators.docker import DockerOperator

        return DockerOperator(
            task_id=task_id,
            image=image,
            command=command,
            environment=environment,
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            auto_remove=True,
            **kwargs
        )

    elif environment_type in ['staging', 'production']:
        from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
        from kubernetes.client import models as k8s

        # Translate Docker parameters to Kubernetes
        k8s_kwargs = {}

        # Handle volumes differently
        if 'volumes' in kwargs:
            k8s_kwargs['volumes'] = _translate_volumes_to_k8s(kwargs.pop('volumes'))

        # Handle resource limits
        if 'mem_limit' in kwargs:
            k8s_kwargs['resources'] = k8s.V1ResourceRequirements(
                limits={'memory': kwargs.pop('mem_limit')},
                requests={'memory': kwargs.pop('mem_reservation', '512Mi')}
            )

        return KubernetesPodOperator(
            task_id=task_id,
            name=f"{task_id}-{{{{ ds }}}}-{{{{ task_instance.try_number }}}}",
            namespace=f"airflow-{environment_type}",
            image=image,
            cmds=command,
            env_vars=environment,
            is_delete_operator_pod=True,
            in_cluster=True,
            **k8s_kwargs,
            **kwargs
        )

    else:
        raise ValueError(f"Unknown environment: {environment_type}")


def _translate_volumes_to_k8s(docker_volumes: List[str]) -> List[k8s.V1Volume]:
    """Translate Docker volume syntax to Kubernetes volumes."""
    k8s_volumes = []

    for volume in docker_volumes:
        if ':' in volume:
            source, target = volume.split(':')[:2]

            # Named volume becomes PVC
            if not source.startswith('/'):
                k8s_volumes.append(
                    k8s.V1Volume(
                        name=source.replace('_', '-'),
                        persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                            claim_name=source
                        )
                    )
                )
            # Host path (use carefully in K8s)
            else:
                k8s_volumes.append(
                    k8s.V1Volume(
                        name=f"host-{len(k8s_volumes)}",
                        host_path=k8s.V1HostPathVolumeSource(
                            path=source
                        )
                    )
                )

    return k8s_volumes
```

### **Using the Abstraction in DAGs**

```python
# dags/portable_pipeline.py
from operators.adaptive_operator import create_container_operator

with DAG('portable_pipeline', ...) as dag:

    # This works identically in all environments
    extract = create_container_operator(
        task_id='extract_data',
        image='registry.localhost/etl/extractor:1.0.0',
        command=['python', '-m', 'extract', '--table', 'orders'],
        environment={
            'DB_HOST': '{{ var.value.db_host }}',
            'DB_PORT': '{{ var.value.db_port }}',
            'DB_NAME': '{{ var.value.db_name }}',
        },
        retries=3
    )

    transform = create_container_operator(
        task_id='transform_data',
        image='registry.localhost/analytics/dbt-runner:1.0.0',
        command=['dbt', 'run', '--select', 'orders'],
        environment={
            'DBT_PROFILES_DIR': '/profiles',
        }
    )

    extract >> transform
```

## 🔧 Advanced Patterns

### **Pattern 1: Sidecar Containers**

```python
# Kerberos authentication sidecar
class KerberosEnabledOperator(KubernetesPodOperator):
    """KPO with automatic Kerberos sidecar."""

    def __init__(self, *args, **kwargs):
        # Add Kerberos sidecar container
        if not kwargs.get('full_pod_spec'):
            kwargs['sidecars'] = kwargs.get('sidecars', []) + [
                k8s.V1Container(
                    name='krb-sidecar',
                    image='registry.localhost/platform/krb-renewer:1.0.0',
                    env=[
                        k8s.V1EnvVar(name='KRB_PRINCIPAL', value='{{ var.value.krb_principal }}'),
                        k8s.V1EnvVar(name='KRB_KEYTAB', value='/keytab/service.keytab'),
                    ],
                    volume_mounts=[
                        k8s.V1VolumeMount(
                            name='keytab',
                            mount_path='/keytab',
                            read_only=True
                        ),
                        k8s.V1VolumeMount(
                            name='krb-cache',
                            mount_path='/tmp/krb5cc'
                        )
                    ],
                    command=['sh', '-c', '''
                        while true; do
                            kinit -kt /keytab/service.keytab $KRB_PRINCIPAL
                            cp /tmp/krb5cc_$(id -u) /tmp/krb5cc/krb5cc
                            sleep 3600
                        done
                    ''']
                )
            ]

            # Add shared cache volume
            kwargs['volumes'] = kwargs.get('volumes', []) + [
                k8s.V1Volume(
                    name='krb-cache',
                    empty_dir=k8s.V1EmptyDirVolumeSource()
                )
            ]

            # Mount cache in main container
            kwargs['volume_mounts'] = kwargs.get('volume_mounts', []) + [
                k8s.V1VolumeMount(
                    name='krb-cache',
                    mount_path='/tmp/krb5cc',
                    read_only=True
                )
            ]

            # Set cache location
            kwargs['env_vars'] = kwargs.get('env_vars', {})
            kwargs['env_vars']['KRB5CCNAME'] = 'FILE:/tmp/krb5cc/krb5cc'

        super().__init__(*args, **kwargs)
```

### **Pattern 2: Dynamic Resource Allocation**

```python
def calculate_resources(table_name: str, date: str) -> dict:
    """Calculate resources based on expected data volume."""

    # Query historical metrics
    conn = BaseHook.get_connection('metrics_db')
    engine = create_engine(conn.get_uri())

    query = """
        SELECT AVG(row_count) as avg_rows, MAX(row_count) as max_rows
        FROM etl_metrics
        WHERE table_name = %s
        AND extract_date >= %s - INTERVAL '30 days'
    """

    result = pd.read_sql(query, engine, params=[table_name, date])

    # Calculate resources
    avg_rows = result['avg_rows'].iloc[0] or 1000000
    max_rows = result['max_rows'].iloc[0] or 5000000

    # Memory: 1GB per 1M rows (average)
    memory_request = f"{int(avg_rows / 1000000)}Gi"
    memory_limit = f"{int(max_rows / 1000000 * 1.5)}Gi"

    # CPU: 500m per 1M rows
    cpu_request = f"{int(avg_rows / 1000000 * 500)}m"
    cpu_limit = f"{int(max_rows / 1000000 * 1000)}m"

    return {
        'requests': {'memory': memory_request, 'cpu': cpu_request},
        'limits': {'memory': memory_limit, 'cpu': cpu_limit}
    }

# Use in operator
resources = calculate_resources('large_table', '{{ ds }}')
extract_task = KubernetesPodOperator(
    task_id='extract_large_table',
    resources=k8s.V1ResourceRequirements(**resources),
    ...
)
```

### **Pattern 3: Multi-Container Coordination**

```python
class CoordinatedExtractOperator(KubernetesPodOperator):
    """
    Coordinates multiple containers for parallel extraction.
    Uses init container for setup and sidecars for support.
    """

    def __init__(self, tables: List[str], *args, **kwargs):

        # Init container to verify connections
        init_containers = [
            k8s.V1Container(
                name='verify-connections',
                image='registry.localhost/etl/connection-tester:1.0.0',
                env_from=[
                    k8s.V1EnvFromSource(
                        secret_ref=k8s.V1SecretEnvSource(name='db-credentials')
                    )
                ],
                command=['python', '-m', 'test_connections']
            )
        ]

        # Main container orchestrates
        kwargs['cmds'] = ['python', '-m', 'orchestrator']
        kwargs['arguments'] = ['--tables'] + tables

        # Sidecar for monitoring
        sidecars = [
            k8s.V1Container(
                name='progress-monitor',
                image='registry.localhost/etl/monitor:1.0.0',
                command=['python', '-m', 'monitor', '--port', '8080']
            )
        ]

        kwargs['init_containers'] = init_containers
        kwargs['sidecars'] = sidecars

        super().__init__(*args, **kwargs)
```

## 📊 Monitoring and Observability

### **Container Metrics Collection**

```python
class ObservableDockerOperator(DockerOperator):
    """DockerOperator with built-in metrics collection."""

    def execute(self, context):
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        import docker
        import time

        start_time = time.time()
        container_id = None

        try:
            # Start container
            container_id = super().execute(context)

            # Collect metrics
            client = docker.from_env()
            container = client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Parse metrics
            memory_usage = stats['memory_stats']['usage'] / 1024 / 1024  # MB
            cpu_usage = self._calculate_cpu_usage(stats)

            # Store metrics
            metrics_hook = PostgresHook('metrics_db')
            metrics_hook.run("""
                INSERT INTO container_metrics
                (task_id, execution_date, memory_mb, cpu_percent, duration_seconds)
                VALUES (%s, %s, %s, %s, %s)
            """, parameters=[
                self.task_id,
                context['execution_date'],
                memory_usage,
                cpu_usage,
                time.time() - start_time
            ])

        except Exception as e:
            self.log.error(f"Metrics collection failed: {e}")
            raise

        finally:
            if container_id:
                # Ensure cleanup
                client.containers.get(container_id).remove(force=True)

    def _calculate_cpu_usage(self, stats):
        """Calculate CPU usage percentage from Docker stats."""
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                   stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                      stats['precpu_stats']['system_cpu_usage']
        cpu_count = len(stats['cpu_stats']['cpu_usage'].get('percpu_usage', [1]))

        if system_delta > 0:
            return (cpu_delta / system_delta) * cpu_count * 100.0
        return 0.0
```

## 🚀 Migration Guide: Docker to Kubernetes

### **Step-by-Step Migration Process**

```python
# Step 1: Inventory your DockerOperator usage
def audit_docker_operators(dag_folder: str) -> pd.DataFrame:
    """Scan DAGs for DockerOperator usage."""
    import ast
    import glob

    operators = []
    for dag_file in glob.glob(f"{dag_folder}/*.py"):
        with open(dag_file) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if hasattr(node.func, 'id') and node.func.id == 'DockerOperator':
                    operators.append({
                        'file': dag_file,
                        'line': node.lineno,
                        'task_id': _extract_arg(node, 'task_id'),
                        'image': _extract_arg(node, 'image'),
                    })

    return pd.DataFrame(operators)

# Step 2: Create migration mapping
MIGRATION_MAP = {
    'DockerOperator': {
        'class': 'KubernetesPodOperator',
        'params': {
            'image': 'image',
            'command': 'cmds',
            'environment': 'env_vars',
            'volumes': '_translate_to_volumes',
            'network_mode': '_ignore',
            'docker_url': '_ignore',
        }
    }
}

# Step 3: Automated migration script
def migrate_operator(docker_code: str) -> str:
    """Convert DockerOperator to KubernetesPodOperator."""

    # Parse the operator call
    # ... (implementation)

    # Generate KPO equivalent
    kpo_code = docker_code.replace('DockerOperator', 'KubernetesPodOperator')
    kpo_code = kpo_code.replace('command=', 'cmds=')
    kpo_code = kpo_code.replace('environment=', 'env_vars=')

    # Add required KPO parameters
    kpo_code = kpo_code.replace(
        'task_id=',
        'namespace="airflow-prod",\n    task_id='
    )

    return kpo_code
```

## 🎓 Best Practices

### **1. Image Management**

```python
# Use semantic versioning
IMAGE_REGISTRY = "registry.localhost"
IMAGE_VERSION = "{{ var.value.etl_version | default('latest') }}"

# Centralize image definitions
IMAGES = {
    'postgres_extractor': f"{IMAGE_REGISTRY}/etl/postgres:{IMAGE_VERSION}",
    'dbt_runner': f"{IMAGE_REGISTRY}/analytics/dbt:{IMAGE_VERSION}",
    'spark_processor': f"{IMAGE_REGISTRY}/processing/spark:{IMAGE_VERSION}",
}

# Use in operators
task = create_container_operator(
    task_id='extract',
    image=IMAGES['postgres_extractor'],
    ...
)
```

### **2. Error Handling**

```python
class RobustContainerOperator(DockerOperator):
    """Container operator with comprehensive error handling."""

    def execute(self, context):
        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # Pre-execution checks
                self._verify_image_exists()
                self._check_resources_available()

                # Execute
                result = super().execute(context)

                # Post-execution validation
                self._validate_output(result)

                return result

            except ImageNotFound as e:
                self.log.error(f"Image not found, pulling: {e}")
                self._pull_image()
                retry_count += 1

            except ResourceExhausted as e:
                self.log.warning(f"Resources exhausted, waiting: {e}")
                time.sleep(30 * retry_count)
                retry_count += 1

            except Exception as e:
                last_error = e
                self.log.error(f"Execution failed (attempt {retry_count + 1}): {e}")
                retry_count += 1

        raise AirflowException(f"Task failed after {max_retries} attempts: {last_error}")
```

### **3. Testing Strategies**

```python
# tests/test_container_operators.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from airflow.models import DagBag

class TestContainerOperators:
    """Test container operator configurations."""

    def test_docker_operator_locally(self):
        """Test DockerOperator configuration."""
        with patch.dict('os.environ', {'AIRFLOW_ENVIRONMENT': 'local'}):
            from operators.adaptive_operator import create_container_operator

            operator = create_container_operator(
                task_id='test_task',
                image='test:latest',
                command=['echo', 'test'],
                environment={'TEST': 'value'}
            )

            assert operator.__class__.__name__ == 'DockerOperator'
            assert operator.image == 'test:latest'
            assert operator.command == ['echo', 'test']

    def test_kubernetes_operator_in_prod(self):
        """Test KubernetesPodOperator configuration."""
        with patch.dict('os.environ', {'AIRFLOW_ENVIRONMENT': 'production'}):
            from operators.adaptive_operator import create_container_operator

            operator = create_container_operator(
                task_id='test_task',
                image='test:latest',
                command=['echo', 'test'],
                environment={'TEST': 'value'}
            )

            assert operator.__class__.__name__ == 'KubernetesPodOperator'
            assert operator.image == 'test:latest'
            assert operator.cmds == ['echo', 'test']

    @patch('docker.from_env')
    def test_container_execution(self, mock_docker):
        """Test actual container execution."""
        # Mock Docker client
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_container.logs.return_value = b'Success'
        mock_container.wait.return_value = {'StatusCode': 0}
        mock_client.containers.run.return_value = mock_container
        mock_docker.return_value = mock_client

        # Execute operator
        operator = DockerOperator(
            task_id='test',
            image='test:latest',
            command='echo test'
        )

        result = operator.execute({})

        # Verify execution
        mock_client.containers.run.assert_called_once()
        assert result is not None
```

## 🔗 Related Documentation

- **[Architecture Overview](architecture-overview.md)** - System design and components
- **[Developer Workflows](developer-workflows.md)** - Daily development patterns
- **[Performance & Scaling](performance-scaling.md)** - Optimization strategies
- **[Troubleshooting Guide](troubleshooting.md)** - Common issues and solutions
- **[Multi-Tenant Setup](multi-tenant-setup.md)** - Tenant isolation patterns

---

*Next: Learn about [Multi-Tenant Setup](multi-tenant-setup.md) for customer isolation.*