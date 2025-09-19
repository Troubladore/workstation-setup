# Datakit Architecture

An in-depth exploration of the architectural decisions, design patterns, and technical implementation of datakits in our data platform.

## 🏗️ Architectural Principles

### **1. Single Responsibility**
Each datakit has exactly one job: extract data from a source system and write it to the Bronze layer without transformation.

```
Source System → Datakit → Bronze Layer
     (Raw)                  (Raw Copy)
```

### **2. Configuration Over Code**
Datakits are configured through environment variables and configuration files, not hard-coded values.

```python
# Good - Configurable
batch_size = int(os.getenv('BATCH_SIZE', '10000'))

# Bad - Hard-coded
batch_size = 10000
```

### **3. Fail-Safe Design**
Datakits should fail loudly and clearly, providing actionable error messages and maintaining data integrity.

```python
# Fail-safe extraction
def extract(self):
    checkpoint = self.load_checkpoint()
    try:
        data = self.fetch_data(since=checkpoint)
        self.write_to_bronze(data)
        self.save_checkpoint(data.max_timestamp)
    except Exception as e:
        self.log_error(e)
        self.alert_on_failure(e)
        raise  # Fail loudly
```

### **4. Idempotency**
Running the same extraction multiple times should produce the same result.

```python
# Idempotent write
df.to_sql(
    name=f'br_{table_name}',
    con=engine,
    if_exists='replace',  # Full refresh
    index=False
)

# Or for incremental
df.to_sql(
    name=f'br_{table_name}_staging',
    con=engine,
    if_exists='replace'
)
# Then MERGE or UPSERT
```

## 🔄 Datakit Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Startup    │────▶│   Execution  │────▶│   Cleanup    │
│              │     │              │     │              │
│ • Load config│     │ • Connect    │     │ • Close conn │
│ • Validate   │     │ • Extract    │     │ • Log metrics│
│ • Init logging│    │ • Write      │     │ • Alert      │
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
  Configuration         Data Flow             Observability
```

### **Phase 1: Startup**

```python
class DatakitLifecycle:
    def __init__(self):
        """Initialization phase."""
        # 1. Load configuration
        self.config = self._load_config()

        # 2. Validate configuration
        self._validate_config()

        # 3. Initialize logging
        self._setup_logging()

        # 4. Initialize metrics
        self._setup_metrics()

        # 5. Check prerequisites
        self._check_prerequisites()

    def _load_config(self) -> Config:
        """Load configuration from environment and files."""
        return Config(
            source_url=os.getenv('SOURCE_URL'),
            target_url=os.getenv('TARGET_URL'),
            batch_size=int(os.getenv('BATCH_SIZE', '10000')),
            timeout=int(os.getenv('TIMEOUT', '300'))
        )

    def _validate_config(self):
        """Validate all required configuration exists."""
        required = ['source_url', 'target_url']
        for field in required:
            if not getattr(self.config, field):
                raise ConfigurationError(f"Missing required config: {field}")

    def _check_prerequisites(self):
        """Check system prerequisites."""
        # Check disk space
        if shutil.disk_usage('/tmp').free < 1_000_000_000:  # 1GB
            raise ResourceError("Insufficient disk space")

        # Check network connectivity
        if not self._can_connect(self.config.source_url):
            raise ConnectionError("Cannot reach source system")
```

### **Phase 2: Execution**

```python
class Extractor(DatakitLifecycle):
    def execute(self):
        """Main execution phase."""
        start_time = time.time()

        try:
            # 1. Establish connections
            with self._get_connections() as (source_conn, target_conn):

                # 2. Determine extraction strategy
                strategy = self._determine_strategy()

                # 3. Extract data
                data = self._extract_data(source_conn, strategy)

                # 4. Validate extracted data
                self._validate_data(data)

                # 5. Write to Bronze
                rows_written = self._write_to_bronze(data, target_conn)

                # 6. Verify write
                self._verify_write(rows_written, target_conn)

                # 7. Update metadata
                self._update_metadata(rows_written)

            # 8. Record success metrics
            self._record_success(time.time() - start_time, rows_written)

        except Exception as e:
            # 9. Handle failure
            self._handle_failure(e, time.time() - start_time)
            raise

    def _determine_strategy(self) -> ExtractionStrategy:
        """Determine extraction strategy based on context."""
        if self.config.incremental and self._has_checkpoint():
            return IncrementalStrategy(self._load_checkpoint())
        elif self.config.partition_column:
            return PartitionedStrategy(self.config.partition_column)
        else:
            return FullRefreshStrategy()

    def _extract_data(self, conn, strategy: ExtractionStrategy):
        """Extract data using determined strategy."""
        return strategy.extract(conn, self.config)
```

### **Phase 3: Cleanup**

```python
class CleanupMixin:
    def cleanup(self):
        """Cleanup phase - always runs."""
        try:
            # 1. Close connections
            self._close_connections()

            # 2. Clean temporary files
            self._clean_temp_files()

            # 3. Flush logs
            self._flush_logs()

            # 4. Send final metrics
            self._send_final_metrics()

            # 5. Alert if needed
            if self.has_warnings:
                self._send_warnings()

        except Exception as e:
            # Cleanup errors shouldn't fail the job
            logger.error(f"Cleanup error: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.cleanup()
        return False  # Don't suppress exceptions
```

## 📊 Data Flow Patterns

### **Pattern 1: Full Refresh**

```python
class FullRefreshExtractor:
    """Replace entire table on each run."""

    def extract(self, source_conn, target_conn):
        # Read entire table
        df = pd.read_sql("SELECT * FROM source_table", source_conn)

        # Add metadata
        df['_bronze_loaded_at'] = datetime.now()
        df['_bronze_batch_id'] = str(uuid.uuid4())

        # Replace entire Bronze table
        df.to_sql(
            'br_table',
            target_conn,
            schema='bronze',
            if_exists='replace',
            index=False,
            method='multi'
        )
```

### **Pattern 2: Incremental Append**

```python
class IncrementalAppendExtractor:
    """Append new records based on timestamp."""

    def extract(self, source_conn, target_conn):
        # Get last checkpoint
        checkpoint = self._get_checkpoint(target_conn)

        # Extract new records
        query = """
            SELECT *
            FROM source_table
            WHERE modified_at > %s
            ORDER BY modified_at
        """
        df = pd.read_sql(query, source_conn, params=[checkpoint])

        if not df.empty:
            # Add metadata
            df['_bronze_loaded_at'] = datetime.now()

            # Append to Bronze
            df.to_sql(
                'br_table',
                target_conn,
                schema='bronze',
                if_exists='append',
                index=False
            )

            # Update checkpoint
            self._save_checkpoint(df['modified_at'].max(), target_conn)

    def _get_checkpoint(self, conn):
        """Get last successful checkpoint."""
        query = """
            SELECT COALESCE(MAX(checkpoint_value), '1900-01-01')
            FROM bronze.extraction_checkpoints
            WHERE table_name = 'br_table'
        """
        return pd.read_sql(query, conn).iloc[0, 0]
```

### **Pattern 3: Change Data Capture (CDC)**

```python
class CDCExtractor:
    """Extract using Change Data Capture."""

    def extract(self, source_conn, target_conn):
        # Get CDC changes
        changes = self._get_cdc_changes(source_conn)

        for batch in self._batch_changes(changes):
            # Process different change types
            inserts = batch[batch['operation'] == 'INSERT']
            updates = batch[batch['operation'] == 'UPDATE']
            deletes = batch[batch['operation'] == 'DELETE']

            # Apply changes to Bronze
            self._apply_inserts(inserts, target_conn)
            self._apply_updates(updates, target_conn)
            self._apply_deletes(deletes, target_conn)

            # Update CDC position
            self._update_cdc_position(batch['lsn'].max())

    def _get_cdc_changes(self, conn):
        """Get changes from CDC tables."""
        query = """
            SELECT
                __$operation as operation,
                __$start_lsn as lsn,
                *
            FROM cdc.dbo_source_table_CT
            WHERE __$start_lsn > %s
            ORDER BY __$start_lsn
        """
        return pd.read_sql(query, conn, params=[self.last_lsn])
```

### **Pattern 4: Partitioned Extraction**

```python
class PartitionedExtractor:
    """Extract data in partitions for large tables."""

    def extract(self, source_conn, target_conn):
        # Determine partitions
        partitions = self._get_partitions(source_conn)

        for partition in partitions:
            logger.info(f"Processing partition: {partition}")

            # Extract partition
            df = self._extract_partition(source_conn, partition)

            # Write partition to staging
            staging_table = f'br_table_partition_{partition}'
            df.to_sql(
                staging_table,
                target_conn,
                schema='bronze',
                if_exists='replace',
                index=False
            )

        # Combine partitions
        self._combine_partitions(target_conn, partitions)

    def _get_partitions(self, conn):
        """Determine partition boundaries."""
        query = """
            SELECT
                DATE_TRUNC('day', created_date) as partition_date
            FROM source_table
            GROUP BY DATE_TRUNC('day', created_date)
            ORDER BY partition_date
        """
        return pd.read_sql(query, conn)['partition_date'].tolist()
```

## 🔐 Security Architecture

### **Credential Management**

```python
class SecureCredentialManager:
    """Manage credentials securely."""

    def get_connection_string(self, source: str) -> str:
        """Get connection string from various sources."""

        # Priority 1: Environment variable
        if env_var := os.getenv(f'{source.upper()}_DATABASE_URL'):
            return env_var

        # Priority 2: Kubernetes secret
        if self._in_kubernetes():
            return self._get_k8s_secret(f'{source}-db-credentials')

        # Priority 3: AWS Secrets Manager
        if self._in_aws():
            return self._get_aws_secret(f'{source}-db-credentials')

        # Priority 4: HashiCorp Vault
        if self._has_vault():
            return self._get_vault_secret(f'database/{source}')

        raise CredentialError(f"No credentials found for {source}")

    def _get_k8s_secret(self, secret_name: str) -> str:
        """Get secret from Kubernetes."""
        with open(f'/var/run/secrets/{secret_name}/url', 'r') as f:
            return f.read().strip()

    def _get_aws_secret(self, secret_name: str) -> str:
        """Get secret from AWS Secrets Manager."""
        import boto3
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])['url']
```

### **Network Security**

```python
class SecureNetworkConnection:
    """Establish secure network connections."""

    def connect(self, url: str) -> Connection:
        """Create secure connection."""
        parsed = urlparse(url)

        # Enforce TLS for production
        if self._is_production() and parsed.scheme not in ['https', 'rediss', 'postgresql+ssl']:
            raise SecurityError("TLS required in production")

        # Set up SSL context
        ssl_context = self._create_ssl_context()

        # Create connection with security settings
        if parsed.scheme.startswith('postgresql'):
            return create_engine(
                url,
                connect_args={
                    'sslmode': 'require',
                    'sslcert': '/certs/client.crt',
                    'sslkey': '/certs/client.key',
                    'sslrootcert': '/certs/ca.crt'
                }
            )
```

## 🎯 Performance Optimizations

### **Memory Management**

```python
class MemoryEfficientExtractor:
    """Extract data with minimal memory usage."""

    def extract_large_table(self, source_conn, target_conn):
        """Extract large table using chunking."""

        # Use server-side cursor for PostgreSQL
        with source_conn.execution_options(
            stream_results=True,
            max_row_buffer=1000
        ).connect() as conn:

            # Process in chunks
            for chunk in pd.read_sql(
                "SELECT * FROM large_table",
                conn,
                chunksize=10000
            ):
                # Process chunk
                chunk['_bronze_loaded_at'] = datetime.now()

                # Write chunk
                chunk.to_sql(
                    'br_large_table',
                    target_conn,
                    schema='bronze',
                    if_exists='append',
                    index=False,
                    method='multi'
                )

                # Explicit garbage collection
                del chunk
                gc.collect()
```

### **Parallel Processing**

```python
class ParallelExtractor:
    """Extract data in parallel."""

    def extract_parallel(self, tables: List[str]):
        """Extract multiple tables in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit extraction tasks
            futures = {
                executor.submit(self.extract_table, table): table
                for table in tables
            }

            # Process results
            for future in as_completed(futures):
                table = futures[future]
                try:
                    rows = future.result()
                    logger.info(f"Extracted {rows} rows from {table}")
                except Exception as e:
                    logger.error(f"Failed to extract {table}: {e}")
```

## 🔍 Observability

### **Structured Logging**

```python
import structlog

class ObservableExtractor:
    def __init__(self):
        self.logger = structlog.get_logger().bind(
            datakit='postgres-extractor',
            version='1.0.0',
            environment=os.getenv('ENVIRONMENT', 'development')
        )

    def extract(self, table: str):
        """Extract with structured logging."""
        log = self.logger.bind(
            table=table,
            operation='extract'
        )

        log.info("extraction_started")

        try:
            rows = self._do_extraction(table)
            log.info(
                "extraction_completed",
                rows_extracted=rows,
                duration_seconds=time.time() - start_time
            )
            return rows

        except Exception as e:
            log.error(
                "extraction_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

### **Metrics Collection**

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
extraction_total = Counter(
    'datakit_extraction_total',
    'Total number of extractions',
    ['datakit', 'table', 'status']
)

extraction_duration = Histogram(
    'datakit_extraction_duration_seconds',
    'Duration of extraction',
    ['datakit', 'table'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

rows_extracted = Counter(
    'datakit_rows_extracted_total',
    'Total rows extracted',
    ['datakit', 'table']
)

last_extraction_timestamp = Gauge(
    'datakit_last_extraction_timestamp',
    'Timestamp of last successful extraction',
    ['datakit', 'table']
)

class MetricsExtractor:
    def extract(self, table: str):
        """Extract with metrics collection."""
        with extraction_duration.labels(
            datakit='postgres-extractor',
            table=table
        ).time():
            try:
                rows = self._do_extraction(table)

                # Update metrics
                extraction_total.labels(
                    datakit='postgres-extractor',
                    table=table,
                    status='success'
                ).inc()

                rows_extracted.labels(
                    datakit='postgres-extractor',
                    table=table
                ).inc(rows)

                last_extraction_timestamp.labels(
                    datakit='postgres-extractor',
                    table=table
                ).set_to_current_time()

                return rows

            except Exception as e:
                extraction_total.labels(
                    datakit='postgres-extractor',
                    table=table,
                    status='failure'
                ).inc()
                raise
```

## 🔗 Integration Points

### **Airflow Integration**

```python
# In Airflow DAG
from airflow.providers.docker.operators.docker import DockerOperator

extract_task = DockerOperator(
    task_id='extract_customers',
    image='registry.localhost/etl/customer-datakit:1.0.0',
    command=['customers'],
    environment={
        'SOURCE_DATABASE_URL': '{{ conn.source_db.get_uri() }}',
        'WAREHOUSE_DATABASE_URL': '{{ conn.warehouse.get_uri() }}',
        'EXTRACTION_DATE': '{{ ds }}',
        'AIRFLOW_CONTEXT': json.dumps({
            'dag_id': '{{ dag.dag_id }}',
            'task_id': '{{ task.task_id }}',
            'execution_date': '{{ ds }}',
            'run_id': '{{ run_id }}'
        })
    },
    docker_url='unix://var/run/docker.sock',
    network_mode='bridge'
)
```

### **Schema Registry Integration**

```python
class SchemaAwareExtractor:
    """Extract with schema registry integration."""

    def __init__(self):
        self.schema_registry = SchemaRegistry(
            os.getenv('SCHEMA_REGISTRY_URL')
        )

    def extract(self, table: str):
        """Extract with schema validation."""
        # Get expected schema
        expected_schema = self.schema_registry.get_schema(
            subject=f'bronze.{table}',
            version='latest'
        )

        # Extract data
        df = self._extract_data(table)

        # Validate schema
        actual_schema = self._infer_schema(df)
        if not self._schemas_compatible(expected_schema, actual_schema):
            # Register new version if evolution is allowed
            if self.schema_registry.is_evolution_allowed(expected_schema, actual_schema):
                self.schema_registry.register_schema(
                    subject=f'bronze.{table}',
                    schema=actual_schema
                )
            else:
                raise SchemaError(f"Incompatible schema change for {table}")

        # Continue with extraction
        self._write_to_bronze(df, table)
```

## 📚 Related Documentation

- [Quick Start Tutorial](quick-start.md) - Build your first datakit
- [Development Workflow](development-workflow.md) - Step-by-step process
- [Testing Strategies](testing.md) - Comprehensive testing guide
- [Performance Optimization](performance.md) - Speed and efficiency

---

*[← Back to Creating Datakits](../creating-datakits.md)*