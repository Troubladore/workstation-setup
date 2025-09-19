# Performance & Scaling Guide

A comprehensive guide to optimizing performance and scaling your Astronomer Airflow data platform from development to enterprise production workloads.

## 🎯 Performance Architecture

Our performance optimization strategy operates at multiple levels:

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│         Query Optimization / Caching / Indexing             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Orchestration Layer                         │
│      Task Parallelism / Resource Allocation / Pooling       │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Container Layer                            │
│      Resource Limits / Image Optimization / Caching         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Infrastructure Layer                         │
│      Node Sizing / Auto-scaling / Network Optimization      │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Performance Baselines

### **Key Metrics to Track**

```python
# performance_metrics.py
from dataclasses import dataclass
from typing import Dict, Any
import time
import psutil
import docker
from prometheus_client import Histogram, Counter, Gauge, Summary

# Define performance metrics
task_duration = Histogram(
    'airflow_task_duration_seconds',
    'Task execution duration',
    ['dag_id', 'task_id', 'operator_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
)

data_processing_rate = Gauge(
    'data_processing_rate_mbps',
    'Data processing rate in MB/s',
    ['pipeline', 'stage']
)

memory_usage = Gauge(
    'task_memory_usage_bytes',
    'Memory usage per task',
    ['dag_id', 'task_id']
)

cpu_usage = Gauge(
    'task_cpu_usage_percent',
    'CPU usage percentage',
    ['dag_id', 'task_id']
)

@dataclass
class PerformanceBaseline:
    """Performance baseline for different workload types."""

    # Bronze extraction baselines
    bronze_extraction_rate_mbps: float = 100.0
    bronze_rows_per_second: int = 10000
    bronze_memory_usage_mb: int = 2048

    # Silver transformation baselines
    silver_processing_rate_mbps: float = 50.0
    silver_cpu_cores: float = 4.0
    silver_memory_usage_mb: int = 4096

    # Gold aggregation baselines
    gold_aggregation_rate_mbps: float = 25.0
    gold_cpu_cores: float = 8.0
    gold_memory_usage_mb: int = 8192

    # Airflow component baselines
    scheduler_cpu_cores: float = 2.0
    scheduler_memory_mb: int = 2048
    worker_cpu_cores: float = 1.0
    worker_memory_mb: int = 2048
    webserver_cpu_cores: float = 0.5
    webserver_memory_mb: int = 1024

    def validate_performance(self, actual_metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Validate actual metrics against baselines."""
        results = {}

        for metric, value in actual_metrics.items():
            baseline = getattr(self, metric, None)
            if baseline:
                # Allow 20% degradation from baseline
                results[metric] = value >= (baseline * 0.8)

        return results
```

## 🚀 Airflow Performance Optimization

### **1. Scheduler Optimization**

```python
# airflow.cfg optimizations
[scheduler]
# Parsing
parsing_processes = 8  # Parallel DAG parsing
file_parsing_sort_mode = modified_time
max_dagruns_to_create_per_loop = 30
max_dagruns_per_loop_to_schedule = 50

# Performance
scheduler_idle_sleep_time = 0.5  # Faster scheduling
min_file_process_interval = 30  # Cache DAG files
dag_dir_list_interval = 60  # Reduce filesystem scans
print_stats_interval = 30

# Cleanup
clean_before_timestamp = true
parsing_cleanup_interval = 60

# Database
pool_recycle = 1800
pool_pre_ping = true
pool_size = 20
max_overflow = 40

[core]
# Parallelism settings
parallelism = 128  # Total parallel tasks
max_active_tasks_per_dag = 32
max_active_runs_per_dag = 16

# Execution
execute_tasks_new_python_interpreter = false  # Reuse interpreters
killed_task_cleanup_time = 30

# Database
sql_alchemy_pool_enabled = true
sql_alchemy_pool_size = 20
sql_alchemy_max_overflow = 40
sql_alchemy_pool_recycle = 3600
sql_alchemy_pool_pre_ping = true

[webserver]
# Performance
workers = 4
worker_class = gevent
worker_refresh_interval = 30
web_server_worker_timeout = 120

# Limits
expose_config = false
page_size = 100
default_dag_run_display_number = 10
```

### **2. Task Execution Optimization**

```python
# optimized_operators.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from typing import Dict, Any, Optional
import resource
import os

class PerformanceOptimizedOperator(BaseOperator):
    """Base operator with performance optimizations."""

    @apply_defaults
    def __init__(
        self,
        memory_limit_mb: Optional[int] = None,
        cpu_limit: Optional[float] = None,
        enable_profiling: bool = False,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit = cpu_limit
        self.enable_profiling = enable_profiling

    def pre_execute(self, context: Dict[str, Any]):
        """Set resource limits before execution."""

        # Set memory limit
        if self.memory_limit_mb:
            memory_bytes = self.memory_limit_mb * 1024 * 1024
            resource.setrlimit(
                resource.RLIMIT_AS,
                (memory_bytes, memory_bytes)
            )

        # Set CPU affinity
        if self.cpu_limit:
            cpu_count = int(self.cpu_limit)
            os.sched_setaffinity(0, range(cpu_count))

        # Start profiling
        if self.enable_profiling:
            import cProfile
            self.profiler = cProfile.Profile()
            self.profiler.enable()

    def post_execute(self, context: Dict[str, Any], result: Any = None):
        """Collect performance metrics after execution."""

        if self.enable_profiling:
            self.profiler.disable()

            # Save profiling results
            stats_file = f"/tmp/profile_{self.task_id}_{context['ds']}.stats"
            self.profiler.dump_stats(stats_file)
            self.log.info(f"Profiling stats saved to {stats_file}")

        # Record metrics
        task_duration.labels(
            dag_id=self.dag_id,
            task_id=self.task_id,
            operator_type=self.__class__.__name__
        ).observe(context['task_instance'].duration.total_seconds())
```

### **3. Database Connection Pooling**

```python
# db_pool_manager.py
from sqlalchemy import create_engine, pool
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from contextlib import contextmanager
import threading
from typing import Dict, Any

class DatabasePoolManager:
    """Manage database connection pools for performance."""

    _pools: Dict[str, Any] = {}
    _lock = threading.Lock()

    @classmethod
    def get_pool(
        cls,
        connection_id: str,
        pool_size: int = 20,
        max_overflow: int = 40,
        pool_recycle: int = 3600,
        pool_type: str = 'queue'
    ):
        """Get or create a connection pool."""

        with cls._lock:
            if connection_id not in cls._pools:
                cls._pools[connection_id] = cls._create_pool(
                    connection_id,
                    pool_size,
                    max_overflow,
                    pool_recycle,
                    pool_type
                )

            return cls._pools[connection_id]

    @classmethod
    def _create_pool(
        cls,
        connection_id: str,
        pool_size: int,
        max_overflow: int,
        pool_recycle: int,
        pool_type: str
    ):
        """Create a new connection pool."""

        from airflow.hooks.base import BaseHook
        conn = BaseHook.get_connection(connection_id)

        # Build connection URL
        if conn.conn_type == 'postgres':
            url = (
                f"postgresql://{conn.login}:{conn.password}"
                f"@{conn.host}:{conn.port}/{conn.schema}"
            )
        elif conn.conn_type == 'mysql':
            url = (
                f"mysql+pymysql://{conn.login}:{conn.password}"
                f"@{conn.host}:{conn.port}/{conn.schema}"
            )
        else:
            raise ValueError(f"Unsupported connection type: {conn.conn_type}")

        # Select pool class
        pool_class = {
            'queue': QueuePool,
            'null': NullPool,
            'static': StaticPool
        }.get(pool_type, QueuePool)

        # Create engine with pooling
        engine = create_engine(
            url,
            poolclass=pool_class,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,
            echo_pool=True,  # Log pool checkouts/checkins

            # Performance options
            connect_args={
                'connect_timeout': 10,
                'options': '-c statement_timeout=300000'  # 5 minutes
            }
        )

        # Add event listeners for monitoring
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            connection_record.info['pid'] = os.getpid()

        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            # Log checkout for monitoring
            logger.debug(f"Connection checked out by PID {os.getpid()}")

        return engine

    @classmethod
    @contextmanager
    def get_connection(cls, connection_id: str):
        """Get a connection from the pool."""

        pool = cls.get_pool(connection_id)
        conn = pool.connect()

        try:
            yield conn
        finally:
            conn.close()  # Returns to pool
```

## 💾 Data Processing Optimization

### **1. Chunking Large Datasets**

```python
# chunked_processor.py
import pandas as pd
from typing import Iterator, Callable, Any, Optional
import gc
import psutil

class ChunkedDataProcessor:
    """Process large datasets in memory-efficient chunks."""

    def __init__(
        self,
        chunk_size: int = 10000,
        memory_limit_mb: int = 2048
    ):
        self.chunk_size = chunk_size
        self.memory_limit_mb = memory_limit_mb
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024

    def process_sql_chunked(
        self,
        query: str,
        connection,
        processor: Callable[[pd.DataFrame], pd.DataFrame]
    ) -> Iterator[pd.DataFrame]:
        """Process SQL results in chunks."""

        # Use server-side cursor for memory efficiency
        with connection.execution_options(
            stream_results=True,
            max_row_buffer=self.chunk_size
        ).connect() as conn:

            # Process chunks
            for chunk in pd.read_sql(
                query,
                conn,
                chunksize=self.chunk_size
            ):
                # Check memory usage
                self._check_memory_usage()

                # Process chunk
                processed = processor(chunk)

                yield processed

                # Explicit garbage collection
                del chunk
                gc.collect()

    def process_file_chunked(
        self,
        filepath: str,
        processor: Callable[[pd.DataFrame], pd.DataFrame],
        file_format: str = 'csv'
    ) -> Iterator[pd.DataFrame]:
        """Process large files in chunks."""

        if file_format == 'csv':
            reader = pd.read_csv(
                filepath,
                chunksize=self.chunk_size,
                iterator=True
            )
        elif file_format == 'parquet':
            # For Parquet, use PyArrow for better memory control
            import pyarrow.parquet as pq

            parquet_file = pq.ParquetFile(filepath)

            for batch in parquet_file.iter_batches(
                batch_size=self.chunk_size
            ):
                chunk = batch.to_pandas()
                processed = processor(chunk)
                yield processed

                del chunk
                gc.collect()

        else:
            for chunk in reader:
                self._check_memory_usage()
                processed = processor(chunk)
                yield processed

                del chunk
                gc.collect()

    def _check_memory_usage(self):
        """Check if memory usage exceeds limit."""

        process = psutil.Process()
        memory_usage = process.memory_info().rss

        if memory_usage > self.memory_limit_bytes:
            # Force garbage collection
            gc.collect()

            # Check again
            memory_usage = process.memory_info().rss
            if memory_usage > self.memory_limit_bytes:
                raise MemoryError(
                    f"Memory usage ({memory_usage / 1024 / 1024:.2f}MB) "
                    f"exceeds limit ({self.memory_limit_mb}MB)"
                )

    def parallel_process(
        self,
        data_source: str,
        processor: Callable[[pd.DataFrame], pd.DataFrame],
        n_workers: int = 4
    ) -> pd.DataFrame:
        """Process data in parallel using multiple workers."""

        from concurrent.futures import ProcessPoolExecutor, as_completed
        import numpy as np

        # Split data into partitions
        partitions = self._create_partitions(data_source, n_workers)

        results = []
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            # Submit processing tasks
            futures = {
                executor.submit(self._process_partition, partition, processor): i
                for i, partition in enumerate(partitions)
            }

            # Collect results
            for future in as_completed(futures):
                partition_idx = futures[future]
                try:
                    result = future.result()
                    results.append((partition_idx, result))
                except Exception as e:
                    self.log.error(f"Partition {partition_idx} failed: {e}")
                    raise

        # Combine results in order
        results.sort(key=lambda x: x[0])
        return pd.concat([r[1] for r in results], ignore_index=True)
```

### **2. Query Optimization**

```python
# query_optimizer.py
from typing import List, Dict, Any, Optional
import sqlparse
from sqlalchemy import text
import hashlib
import json

class QueryOptimizer:
    """Optimize SQL queries for performance."""

    def __init__(self):
        self.query_cache = {}
        self.statistics_cache = {}

    def optimize_query(
        self,
        query: str,
        hints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Optimize a SQL query."""

        # Parse query
        parsed = sqlparse.parse(query)[0]

        # Apply optimizations
        optimized = self._add_optimizer_hints(query, hints)
        optimized = self._optimize_joins(optimized)
        optimized = self._add_partition_pruning(optimized)
        optimized = self._optimize_aggregations(optimized)

        return optimized

    def _add_optimizer_hints(
        self,
        query: str,
        hints: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add database-specific optimizer hints."""

        if not hints:
            return query

        # PostgreSQL hints
        if hints.get('database') == 'postgresql':
            pg_hints = []

            if hints.get('parallel_workers'):
                pg_hints.append(
                    f"/*+ Parallel(t {hints['parallel_workers']}) */"
                )

            if hints.get('join_method'):
                pg_hints.append(
                    f"/*+ {hints['join_method']}Join(t1 t2) */"
                )

            if hints.get('index_name'):
                pg_hints.append(
                    f"/*+ IndexScan(t {hints['index_name']}) */"
                )

            if pg_hints:
                query = f"{' '.join(pg_hints)}\n{query}"

        return query

    def _optimize_joins(self, query: str) -> str:
        """Optimize JOIN operations."""

        # Reorder joins based on estimated cardinality
        # This is a simplified example - real implementation would
        # analyze table statistics

        import re

        # Extract joins
        join_pattern = r'(INNER|LEFT|RIGHT|FULL)\s+JOIN\s+(\w+)'
        joins = re.findall(join_pattern, query, re.IGNORECASE)

        if len(joins) > 1:
            # Sort joins by estimated selectivity
            # Smaller tables first for hash joins
            # Larger tables first for nested loop joins
            pass

        return query

    def _add_partition_pruning(self, query: str) -> str:
        """Add partition pruning hints."""

        # Look for date filters
        import re

        date_pattern = r"(\w+_date)\s*([><=]+)\s*'([^']+)'"
        date_filters = re.findall(date_pattern, query)

        for column, operator, value in date_filters:
            # Add partition pruning comment
            query = f"""
            -- Partition pruning on {column}
            {query}
            """

        return query

    def _optimize_aggregations(self, query: str) -> str:
        """Optimize aggregation operations."""

        # Push down filters before aggregations
        # Use materialized CTEs for repeated aggregations

        if 'GROUP BY' in query.upper():
            # Add FILTER clause for conditional aggregations
            # instead of CASE statements
            query = query.replace(
                "SUM(CASE WHEN",
                "SUM(1) FILTER (WHERE"
            )

        return query

    def cache_query_result(
        self,
        query: str,
        result: pd.DataFrame,
        ttl_seconds: int = 3600
    ):
        """Cache query results for repeated use."""

        query_hash = hashlib.sha256(query.encode()).hexdigest()
        self.query_cache[query_hash] = {
            'result': result,
            'cached_at': time.time(),
            'ttl': ttl_seconds
        }

    def get_cached_result(self, query: str) -> Optional[pd.DataFrame]:
        """Get cached query result if available."""

        query_hash = hashlib.sha256(query.encode()).hexdigest()
        cached = self.query_cache.get(query_hash)

        if cached:
            age = time.time() - cached['cached_at']
            if age < cached['ttl']:
                return cached['result'].copy()

        return None
```

### **3. dbt Performance Optimization**

```sql
-- dbt model with performance optimizations
{{
    config(
        -- Materialization strategy
        materialized='incremental',
        unique_key='order_id',
        on_schema_change='sync_all_columns',

        -- Partitioning for large tables
        partition_by={
            'field': 'order_date',
            'data_type': 'date',
            'granularity': 'day'
        },

        -- Clustering for query optimization
        cluster_by=['customer_id', 'order_date'],

        -- Incremental strategy
        incremental_strategy='merge',
        merge_exclude_columns=['created_at'],

        -- Performance hints
        sql_header="SET statement_timeout = '10min'",

        -- Pre and post hooks
        pre_hook="VACUUM ANALYZE {{ this }}",
        post_hook=[
            "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_customer ON {{ this }} (customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_{{ this.name }}_date ON {{ this }} (order_date)",
            "ANALYZE {{ this }}"
        ]
    )
}}

-- Use CTEs efficiently
WITH filtered_source AS (
    -- Push down filters early
    SELECT *
    FROM {{ source('bronze', 'br_orders') }}
    WHERE order_date >= '{{ var("start_date") }}'
    {% if is_incremental() %}
        AND updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),

-- Materialize expensive calculations
expensive_calculations AS MATERIALIZED (
    SELECT
        order_id,
        -- Complex calculation done once
        {{ complex_business_logic() }} as calculated_field
    FROM filtered_source
),

-- Final select with simple joins
final AS (
    SELECT
        s.*,
        c.calculated_field
    FROM filtered_source s
    INNER JOIN expensive_calculations c
        USING (order_id)
)

SELECT * FROM final
```

## 🚁 Container Performance

### **1. Docker Image Optimization**

```dockerfile
# Optimized Dockerfile
# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Add non-root user
RUN useradd -m -u 1000 airflow
USER airflow

# Copy application
COPY --chown=airflow:airflow . /app
WORKDIR /app

# Set environment for performance
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    MALLOC_MMAP_THRESHOLD_=524288 \
    MALLOC_TRIM_THRESHOLD_=524288

ENTRYPOINT ["python"]
```

### **2. Resource Limits and Requests**

```yaml
# k8s/performance-pod-template.yaml
apiVersion: v1
kind: Pod
metadata:
  name: airflow-worker
spec:
  containers:
    - name: worker
      image: registry.localhost/platform/airflow:3.0-10

      # Resource requests (guaranteed)
      resources:
        requests:
          memory: "2Gi"
          cpu: "1"
          ephemeral-storage: "5Gi"

        # Resource limits (maximum)
        limits:
          memory: "4Gi"
          cpu: "2"
          ephemeral-storage: "10Gi"

      # JVM-style memory management for Python
      env:
        - name: MALLOC_ARENA_MAX
          value: "2"
        - name: PYTHONMALLOC
          value: "malloc"
        - name: OMP_NUM_THREADS
          value: "2"

      # Probes for health
      livenessProbe:
        exec:
          command:
            - python
            - -c
            - "import sys; sys.exit(0)"
        initialDelaySeconds: 30
        periodSeconds: 30

      readinessProbe:
        exec:
          command:
            - python
            - -c
            - "import airflow; print('ready')"
        initialDelaySeconds: 10
        periodSeconds: 10

  # Pod-level settings
  nodeSelector:
    workload: compute-optimized

  tolerations:
    - key: "compute-optimized"
      operator: "Equal"
      value: "true"
      effect: "NoSchedule"

  affinity:
    # Prefer nodes with available resources
    nodeAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          preference:
            matchExpressions:
              - key: node.kubernetes.io/instance-type
                operator: In
                values: ["c5.2xlarge", "c5.4xlarge"]

    # Spread pods across nodes
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            topologyKey: kubernetes.io/hostname
            labelSelector:
              matchLabels:
                app: airflow
                component: worker
```

## 📈 Auto-Scaling Strategies

### **1. Kubernetes HPA (Horizontal Pod Autoscaler)**

```yaml
# k8s/hpa-workers.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: airflow-workers-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: airflow-workers

  minReplicas: 2
  maxReplicas: 20

  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # Custom metrics from Prometheus
    - type: Pods
      pods:
        metric:
          name: airflow_task_queue_size
        target:
          type: AverageValue
          averageValue: "10"

  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      selectPolicy: Max
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60

    scaleDown:
      stabilizationWindowSeconds: 300
      selectPolicy: Min
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
        - type: Pods
          value: 1
          periodSeconds: 60
```

### **2. KEDA (Kubernetes Event-Driven Autoscaling)**

```yaml
# k8s/keda-scaler.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: airflow-workers-keda
spec:
  scaleTargetRef:
    name: airflow-workers

  minReplicaCount: 2
  maxReplicaCount: 50

  triggers:
    # Scale based on PostgreSQL query
    - type: postgresql
      metadata:
        connectionFromEnv: AIRFLOW_DB_CONN
        query: |
          SELECT COUNT(*)
          FROM task_instance
          WHERE state IN ('queued', 'running')
        targetQueryValue: "5"

    # Scale based on Redis queue length
    - type: redis
      metadata:
        address: redis:6379
        listName: celery
        listLength: "10"

    # Scale based on CPU
    - type: cpu
      metadata:
        type: Utilization
        value: "70"

    # Scale based on time
    - type: cron
      metadata:
        timezone: UTC
        start: 0 8 * * 1-5  # Scale up weekdays at 8 AM
        end: 0 20 * * 1-5   # Scale down weekdays at 8 PM
        desiredReplicas: "10"
```

### **3. Custom Auto-Scaling Logic**

```python
# autoscaler.py
import kubernetes
from datetime import datetime, timedelta
from typing import Dict, Any
import numpy as np

class IntelligentAutoscaler:
    """ML-based autoscaling for Airflow workers."""

    def __init__(self):
        self.k8s = kubernetes.client.AppsV1Api()
        self.metrics = []
        self.scaling_history = []

    def predict_required_workers(self) -> int:
        """Predict required workers using ML model."""

        # Collect metrics
        current_metrics = self._collect_metrics()

        # Time-based features
        now = datetime.now()
        hour_of_day = now.hour
        day_of_week = now.weekday()
        is_business_hours = 8 <= hour_of_day <= 18 and day_of_week < 5

        # Historical patterns
        avg_tasks_per_worker = self._calculate_avg_tasks_per_worker()
        peak_multiplier = 1.5 if is_business_hours else 1.0

        # Queue-based calculation
        queued_tasks = current_metrics['queued_tasks']
        running_tasks = current_metrics['running_tasks']
        avg_task_duration = current_metrics['avg_task_duration']

        # Calculate required workers
        base_workers = max(
            2,  # Minimum
            int(np.ceil((queued_tasks + running_tasks) / avg_tasks_per_worker))
        )

        # Apply multipliers
        required_workers = int(base_workers * peak_multiplier)

        # Apply limits
        required_workers = max(2, min(50, required_workers))

        return required_workers

    def scale_workers(self, target_replicas: int):
        """Scale worker deployment."""

        deployment = self.k8s.read_namespaced_deployment(
            name='airflow-workers',
            namespace='airflow'
        )

        current_replicas = deployment.spec.replicas

        if target_replicas != current_replicas:
            # Update deployment
            deployment.spec.replicas = target_replicas
            self.k8s.patch_namespaced_deployment(
                name='airflow-workers',
                namespace='airflow',
                body=deployment
            )

            # Log scaling event
            self.scaling_history.append({
                'timestamp': datetime.now(),
                'from_replicas': current_replicas,
                'to_replicas': target_replicas,
                'reason': 'predictive_scaling'
            })

    def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics."""

        from airflow.models import DagRun, TaskInstance
        from airflow.utils.state import State

        # Query Airflow database
        session = settings.Session()

        try:
            queued_tasks = session.query(TaskInstance).filter(
                TaskInstance.state == State.QUEUED
            ).count()

            running_tasks = session.query(TaskInstance).filter(
                TaskInstance.state == State.RUNNING
            ).count()

            # Average task duration
            recent_tasks = session.query(TaskInstance).filter(
                TaskInstance.state == State.SUCCESS,
                TaskInstance.end_date >= datetime.now() - timedelta(hours=1)
            ).all()

            if recent_tasks:
                durations = [
                    (t.end_date - t.start_date).total_seconds()
                    for t in recent_tasks
                ]
                avg_duration = np.mean(durations)
            else:
                avg_duration = 300  # Default 5 minutes

            return {
                'queued_tasks': queued_tasks,
                'running_tasks': running_tasks,
                'avg_task_duration': avg_duration,
                'timestamp': datetime.now()
            }

        finally:
            session.close()
```

## 🔍 Performance Monitoring

### **Performance Dashboard**

```python
# performance_dashboard.py
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Any

class PerformanceMonitor:
    """Monitor and report on performance metrics."""

    def __init__(self):
        self.metrics_store = []

    def generate_performance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate comprehensive performance report."""

        report = {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'summary': {},
            'bottlenecks': [],
            'recommendations': []
        }

        # Task performance
        task_metrics = self._get_task_metrics(start_date, end_date)
        report['summary']['avg_task_duration'] = task_metrics['avg_duration']
        report['summary']['p95_task_duration'] = task_metrics['p95_duration']
        report['summary']['failed_tasks'] = task_metrics['failed_count']

        # Resource utilization
        resource_metrics = self._get_resource_metrics(start_date, end_date)
        report['summary']['avg_cpu_usage'] = resource_metrics['avg_cpu']
        report['summary']['avg_memory_usage'] = resource_metrics['avg_memory']
        report['summary']['peak_memory_usage'] = resource_metrics['peak_memory']

        # Identify bottlenecks
        if task_metrics['p95_duration'] > 1800:  # 30 minutes
            report['bottlenecks'].append({
                'type': 'slow_tasks',
                'severity': 'high',
                'description': 'P95 task duration exceeds 30 minutes',
                'tasks': task_metrics['slowest_tasks']
            })

        if resource_metrics['avg_memory'] > 0.8:
            report['bottlenecks'].append({
                'type': 'memory_pressure',
                'severity': 'high',
                'description': 'Average memory usage exceeds 80%',
                'nodes': resource_metrics['memory_constrained_nodes']
            })

        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)

        return report

    def _generate_recommendations(
        self,
        report: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate performance improvement recommendations."""

        recommendations = []

        for bottleneck in report['bottlenecks']:
            if bottleneck['type'] == 'slow_tasks':
                recommendations.append({
                    'priority': 'high',
                    'category': 'optimization',
                    'recommendation': 'Optimize slow tasks',
                    'actions': [
                        'Review query execution plans',
                        'Add appropriate indexes',
                        'Consider task parallelization',
                        'Implement incremental processing'
                    ]
                })

            elif bottleneck['type'] == 'memory_pressure':
                recommendations.append({
                    'priority': 'high',
                    'category': 'scaling',
                    'recommendation': 'Address memory constraints',
                    'actions': [
                        'Increase worker memory limits',
                        'Implement chunked processing',
                        'Add more worker nodes',
                        'Optimize memory-intensive operations'
                    ]
                })

        return recommendations

# Grafana dashboard query examples
GRAFANA_QUERIES = {
    'task_duration_p95': """
        histogram_quantile(
            0.95,
            sum(rate(airflow_task_duration_seconds_bucket[5m])) by (le, dag_id)
        )
    """,

    'worker_cpu_usage': """
        avg(
            rate(container_cpu_usage_seconds_total{
                namespace="airflow",
                pod=~"airflow-worker-.*"
            }[5m])
        ) by (pod)
    """,

    'memory_usage_by_dag': """
        max(
            container_memory_working_set_bytes{
                namespace="airflow",
                pod=~"airflow-worker-.*"
            }
        ) by (pod, dag_id) / 1024 / 1024 / 1024
    """,

    'queue_size': """
        sum(
            airflow_task_instance_state{state="queued"}
        )
    """,

    'data_processing_rate': """
        rate(
            data_rows_processed_total[5m]
        )
    """
}
```

## 🎯 Performance Best Practices

### **1. DAG Design**
```python
# ✅ Good: Parallel tasks
with DAG('optimized_dag', ...) as dag:
    start = DummyOperator(task_id='start')

    # Parallel extraction
    extract_tasks = []
    for table in tables:
        task = DockerOperator(
            task_id=f'extract_{table}',
            ...
        )
        extract_tasks.append(task)
        start >> task

    # Single merge point
    merge = DummyOperator(task_id='merge')
    extract_tasks >> merge

# ❌ Bad: Sequential tasks
with DAG('slow_dag', ...) as dag:
    prev_task = None
    for table in tables:
        task = DockerOperator(
            task_id=f'extract_{table}',
            ...
        )
        if prev_task:
            prev_task >> task
        prev_task = task
```

### **2. Resource Allocation**
```python
# ✅ Good: Appropriate resource limits
task = KubernetesPodOperator(
    task_id='process_data',
    resources=k8s.V1ResourceRequirements(
        requests={'memory': '2Gi', 'cpu': '1'},
        limits={'memory': '4Gi', 'cpu': '2'}
    )
)

# ❌ Bad: No resource limits
task = KubernetesPodOperator(
    task_id='process_data'
    # No resources specified - can consume unlimited
)
```

### **3. Query Optimization**
```sql
-- ✅ Good: Optimized query
WITH filtered_data AS (
    SELECT /*+ PARALLEL(4) */
        customer_id,
        order_date,
        amount
    FROM orders
    WHERE order_date >= '2024-01-01'  -- Partition pruning
        AND status = 'completed'       -- Filter early
)
SELECT
    customer_id,
    SUM(amount) as total
FROM filtered_data
GROUP BY customer_id;

-- ❌ Bad: Unoptimized query
SELECT
    customer_id,
    SUM(amount) as total
FROM orders
WHERE YEAR(order_date) = 2024  -- Function prevents index use
GROUP BY customer_id
HAVING SUM(amount) > 0;  -- Filter after aggregation
```

## 🔗 Related Documentation

- [Architecture Overview](architecture-overview.md) - System design
- [Container Orchestration](container-orchestration.md) - Container optimization
- [Monitoring & Observability](monitoring-observability.md) - Performance monitoring
- [Troubleshooting Guide](troubleshooting.md) - Performance issues

---

*Performance is not about doing things fast, it's about doing the right things efficiently.*