# DAG Patterns Guide

A comprehensive guide to Airflow DAG design patterns, best practices, and advanced orchestration techniques for building reliable, maintainable data pipelines.

## 🎯 DAG Design Principles

### **Core Principles**
1. **Idempotency**: Running a DAG multiple times produces the same result
2. **Atomicity**: Tasks either complete fully or rollback completely
3. **Determinism**: Same inputs always produce same outputs
4. **Modularity**: Reusable components and clear separation of concerns
5. **Observability**: Clear logging, monitoring, and alerting

## 📐 DAG Architecture Patterns

### **Pattern 1: ETL/ELT Pattern**

```python
# dags/etl_pattern.py
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['data-team@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
}

with DAG(
    'etl_pattern',
    default_args=default_args,
    description='Standard ETL pattern with Bronze → Silver → Gold',
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'pattern', 'daily'],
    doc_md="""
    # ETL Pattern DAG

    This DAG implements the standard ETL pattern:
    1. **Extract** - Pull data from source systems
    2. **Transform** - Clean and process data
    3. **Load** - Write to target warehouse

    ## Data Flow
    Source Systems → Bronze (Raw) → Silver (Clean) → Gold (Business)

    ## SLA
    - Expected completion: 2 hours
    - Critical path: customer data pipeline
    """,
) as dag:

    # Start and end markers
    start = DummyOperator(
        task_id='start',
        trigger_rule='all_success'
    )

    end = DummyOperator(
        task_id='end',
        trigger_rule='none_failed_min_one_success'
    )

    # Extract phase - parallel extraction
    with TaskGroup(group_id='extract_bronze') as extract_group:

        extract_customers = DockerOperator(
            task_id='extract_customers',
            image='registry.localhost/etl/postgres-extractor:1.0.0',
            command=['customers', '--date', '{{ ds }}'],
            environment={
                'SOURCE_DB': '{{ var.value.source_db_customers }}',
                'TARGET_SCHEMA': 'bronze',
                'EXTRACTION_MODE': 'incremental',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            mount_tmp_dir=False,
            auto_remove=True,
            pool='extraction_pool',
            priority_weight=10,  # Higher priority
        )

        extract_orders = DockerOperator(
            task_id='extract_orders',
            image='registry.localhost/etl/postgres-extractor:1.0.0',
            command=['orders', '--date', '{{ ds }}'],
            environment={
                'SOURCE_DB': '{{ var.value.source_db_orders }}',
                'TARGET_SCHEMA': 'bronze',
                'EXTRACTION_MODE': 'incremental',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            mount_tmp_dir=False,
            auto_remove=True,
            pool='extraction_pool',
            priority_weight=5,
        )

        extract_products = DockerOperator(
            task_id='extract_products',
            image='registry.localhost/etl/api-extractor:1.0.0',
            command=['products', '--date', '{{ ds }}'],
            environment={
                'API_ENDPOINT': '{{ var.value.products_api }}',
                'API_KEY': '{{ var.value.products_api_key }}',
                'TARGET_SCHEMA': 'bronze',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            mount_tmp_dir=False,
            auto_remove=True,
            pool='api_pool',  # Different pool for API calls
        )

    # Transform phase - Silver layer
    with TaskGroup(group_id='transform_silver') as transform_group:

        transform_customers = DockerOperator(
            task_id='transform_customers',
            image='registry.localhost/analytics/dbt-runner:1.0.0',
            command=['run', '--select', 'silver.customers'],
            environment={
                'DBT_PROFILES_DIR': '/profiles',
                'DBT_TARGET': '{{ var.value.environment }}',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            volumes=['dbt_profiles:/profiles:ro'],
            pool='transform_pool',
        )

        transform_orders = DockerOperator(
            task_id='transform_orders',
            image='registry.localhost/analytics/dbt-runner:1.0.0',
            command=['run', '--select', 'silver.orders'],
            environment={
                'DBT_PROFILES_DIR': '/profiles',
                'DBT_TARGET': '{{ var.value.environment }}',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            volumes=['dbt_profiles:/profiles:ro'],
            pool='transform_pool',
        )

    # Load phase - Gold layer
    with TaskGroup(group_id='load_gold') as load_group:

        build_dimensions = DockerOperator(
            task_id='build_dimensions',
            image='registry.localhost/analytics/dbt-runner:1.0.0',
            command=['run', '--select', 'gold.dimensions'],
            environment={
                'DBT_PROFILES_DIR': '/profiles',
                'DBT_TARGET': '{{ var.value.environment }}',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            volumes=['dbt_profiles:/profiles:ro'],
            pool='transform_pool',
        )

        build_facts = DockerOperator(
            task_id='build_facts',
            image='registry.localhost/analytics/dbt-runner:1.0.0',
            command=['run', '--select', 'gold.facts'],
            environment={
                'DBT_PROFILES_DIR': '/profiles',
                'DBT_TARGET': '{{ var.value.environment }}',
            },
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
            volumes=['dbt_profiles:/profiles:ro'],
            pool='transform_pool',
        )

        build_dimensions >> build_facts

    # Data quality checks
    with TaskGroup(group_id='quality_checks') as quality_group:

        check_bronze = DockerOperator(
            task_id='check_bronze_quality',
            image='registry.localhost/quality/great-expectations:1.0.0',
            command=['validate', '--suite', 'bronze_suite'],
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
        )

        check_silver = DockerOperator(
            task_id='check_silver_quality',
            image='registry.localhost/quality/great-expectations:1.0.0',
            command=['validate', '--suite', 'silver_suite'],
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
        )

        check_gold = DockerOperator(
            task_id='check_gold_quality',
            image='registry.localhost/quality/great-expectations:1.0.0',
            command=['validate', '--suite', 'gold_suite'],
            docker_url='unix://var/run/docker.sock',
            network_mode='edge',
        )

    # Define dependencies
    start >> extract_group >> transform_group >> load_group >> quality_group >> end
```

### **Pattern 2: Fan-Out/Fan-In Pattern**

```python
# dags/fanout_fanin_pattern.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sensors.external_task import ExternalTaskSensor
import json

with DAG(
    'fanout_fanin_orchestrator',
    default_args=default_args,
    description='Orchestrator that fans out work and fans in results',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    def prepare_parallel_work(**context):
        """Split work into parallel chunks."""

        # Get list of tables to process
        tables = Variable.get('tables_to_process', deserialize_json=True)

        # Split into chunks for parallel processing
        chunk_size = 10
        chunks = [
            tables[i:i + chunk_size]
            for i in range(0, len(tables), chunk_size)
        ]

        # Store chunks for downstream tasks
        context['task_instance'].xcom_push(
            key='work_chunks',
            value=chunks
        )

        return len(chunks)

    def trigger_parallel_dags(**context):
        """Trigger parallel DAGs for each chunk."""

        chunks = context['task_instance'].xcom_pull(
            task_ids='prepare_work',
            key='work_chunks'
        )

        triggered_runs = []
        for i, chunk in enumerate(chunks):
            # Trigger a DAG for each chunk
            trigger = TriggerDagRunOperator(
                task_id=f'trigger_worker_{i}',
                trigger_dag_id='worker_dag',
                conf={
                    'chunk_id': i,
                    'tables': chunk,
                    'parent_dag_id': context['dag'].dag_id,
                    'parent_run_id': context['run_id']
                },
                wait_for_completion=False,
                poke_interval=30,
            )
            triggered_runs.append(trigger)

        return triggered_runs

    def aggregate_results(**context):
        """Aggregate results from parallel executions."""

        chunks = context['task_instance'].xcom_pull(
            task_ids='prepare_work',
            key='work_chunks'
        )

        results = []
        for i in range(len(chunks)):
            # Get results from each parallel execution
            chunk_result = context['task_instance'].xcom_pull(
                dag_id='worker_dag',
                task_ids='process_chunk',
                key=f'chunk_{i}_result'
            )
            results.append(chunk_result)

        # Aggregate results
        total_rows = sum(r.get('rows_processed', 0) for r in results)
        failed_tables = [
            table
            for r in results
            for table in r.get('failed_tables', [])
        ]

        summary = {
            'total_rows_processed': total_rows,
            'failed_tables': failed_tables,
            'chunks_processed': len(results),
            'success': len(failed_tables) == 0
        }

        return summary

    # Define tasks
    prepare = PythonOperator(
        task_id='prepare_work',
        python_callable=prepare_parallel_work,
    )

    # Dynamic task generation for parallel execution
    @task.dynamic
    def process_chunks(**context):
        chunks = context['task_instance'].xcom_pull(
            task_ids='prepare_work',
            key='work_chunks'
        )

        for i, chunk in enumerate(chunks):
            yield TriggerDagRunOperator(
                task_id=f'process_chunk_{i}',
                trigger_dag_id='worker_dag',
                conf={'chunk': chunk, 'chunk_id': i},
                wait_for_completion=True,
            )

    aggregate = PythonOperator(
        task_id='aggregate_results',
        python_callable=aggregate_results,
        trigger_rule='all_done',  # Run even if some chunks fail
    )

    # Dependencies
    prepare >> process_chunks() >> aggregate
```

### **Pattern 3: Dynamic DAG Generation**

```python
# dags/dynamic_dag_generator.py
from airflow import DAG
from airflow.models import Variable
import yaml
import os
from typing import Dict, Any

class DynamicDAGGenerator:
    """Generate DAGs dynamically from configuration."""

    def __init__(self, config_path: str = '/opt/airflow/dags/configs'):
        self.config_path = config_path

    def generate_dags(self) -> Dict[str, DAG]:
        """Generate DAGs from configuration files."""

        dags = {}

        # Read all configuration files
        for config_file in os.listdir(self.config_path):
            if config_file.endswith('.yaml'):
                with open(os.path.join(self.config_path, config_file)) as f:
                    config = yaml.safe_load(f)

                # Generate DAG from configuration
                dag = self._create_dag_from_config(config)
                dags[dag.dag_id] = dag

        return dags

    def _create_dag_from_config(self, config: Dict[str, Any]) -> DAG:
        """Create a DAG from configuration."""

        dag_config = config['dag']

        # Create DAG
        dag = DAG(
            dag_id=dag_config['id'],
            default_args=dag_config.get('default_args', {}),
            description=dag_config.get('description', ''),
            schedule_interval=dag_config.get('schedule', '@daily'),
            catchup=dag_config.get('catchup', False),
            tags=dag_config.get('tags', []),
        )

        # Create tasks
        tasks = {}
        for task_config in config.get('tasks', []):
            task = self._create_task_from_config(task_config, dag)
            tasks[task_config['id']] = task

        # Set dependencies
        for dep in config.get('dependencies', []):
            upstream = tasks[dep['upstream']]
            downstream = tasks[dep['downstream']]
            upstream >> downstream

        return dag

    def _create_task_from_config(self, task_config: Dict[str, Any], dag: DAG):
        """Create a task from configuration."""

        task_type = task_config['type']

        if task_type == 'docker':
            from airflow.providers.docker.operators.docker import DockerOperator
            return DockerOperator(
                task_id=task_config['id'],
                image=task_config['image'],
                command=task_config.get('command'),
                environment=task_config.get('environment', {}),
                dag=dag,
            )

        elif task_type == 'python':
            from airflow.operators.python import PythonOperator
            return PythonOperator(
                task_id=task_config['id'],
                python_callable=self._get_callable(task_config['callable']),
                op_kwargs=task_config.get('kwargs', {}),
                dag=dag,
            )

        elif task_type == 'sql':
            from airflow.providers.postgres.operators.postgres import PostgresOperator
            return PostgresOperator(
                task_id=task_config['id'],
                sql=task_config['sql'],
                postgres_conn_id=task_config.get('connection', 'postgres_default'),
                dag=dag,
            )

# Configuration example (configs/customer_pipeline.yaml)
"""
dag:
  id: customer_pipeline
  description: Customer data processing pipeline
  schedule: '@daily'
  tags: ['customer', 'daily']
  default_args:
    owner: data-team
    retries: 2

tasks:
  - id: extract_customers
    type: docker
    image: registry.localhost/etl/extractor:1.0.0
    command: ['customers']
    environment:
      SOURCE_DB: '{{ var.value.source_db }}'

  - id: transform_customers
    type: docker
    image: registry.localhost/analytics/dbt:1.0.0
    command: ['run', '--select', 'customers']

  - id: validate_customers
    type: sql
    sql: |
      SELECT COUNT(*) as count
      FROM silver.customers
      WHERE created_at >= '{{ ds }}'
    connection: warehouse

dependencies:
  - upstream: extract_customers
    downstream: transform_customers
  - upstream: transform_customers
    downstream: validate_customers
"""

# Register generated DAGs
generator = DynamicDAGGenerator()
globals().update(generator.generate_dags())
```

### **Pattern 4: Conditional Branching Pattern**

```python
# dags/conditional_branching_pattern.py
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.trigger_rule import TriggerRule

with DAG(
    'conditional_branching_pattern',
    default_args=default_args,
    description='DAG with conditional execution paths',
    schedule_interval='@daily',
    catchup=False,
) as dag:

    def check_data_availability(**context):
        """Check which data sources are available."""

        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id='warehouse')

        # Check various data sources
        checks = {
            'customers': "SELECT COUNT(*) FROM bronze.br_customers WHERE date = '{{ ds }}'",
            'orders': "SELECT COUNT(*) FROM bronze.br_orders WHERE date = '{{ ds }}'",
            'products': "SELECT COUNT(*) FROM bronze.br_products WHERE date = '{{ ds }}'"
        }

        available_sources = []
        for source, query in checks.items():
            result = hook.get_first(query)[0]
            if result > 0:
                available_sources.append(f'process_{source}')

        # Return list of tasks to execute
        return available_sources if available_sources else ['no_data_available']

    def process_based_on_day(**context):
        """Branch based on day of week."""

        execution_date = context['execution_date']
        day_of_week = execution_date.weekday()

        if day_of_week == 0:  # Monday
            return 'weekly_aggregation'
        elif day_of_week in [5, 6]:  # Weekend
            return 'maintenance_tasks'
        else:  # Weekdays
            return 'daily_processing'

    def check_data_quality(**context):
        """Branch based on data quality."""

        # Check data quality metrics
        quality_score = context['task_instance'].xcom_pull(
            task_ids='calculate_quality_score'
        )

        if quality_score >= 0.95:
            return 'high_quality_path'
        elif quality_score >= 0.80:
            return 'medium_quality_path'
        else:
            return 'low_quality_path'

    # Branching tasks
    check_availability = BranchPythonOperator(
        task_id='check_data_availability',
        python_callable=check_data_availability,
    )

    day_branching = BranchPythonOperator(
        task_id='branch_by_day',
        python_callable=process_based_on_day,
    )

    quality_branching = BranchPythonOperator(
        task_id='branch_by_quality',
        python_callable=check_data_quality,
    )

    # Process branches
    process_customers = DummyOperator(task_id='process_customers')
    process_orders = DummyOperator(task_id='process_orders')
    process_products = DummyOperator(task_id='process_products')
    no_data_available = DummyOperator(task_id='no_data_available')

    # Day-based branches
    daily_processing = DummyOperator(task_id='daily_processing')
    weekly_aggregation = DummyOperator(task_id='weekly_aggregation')
    maintenance_tasks = DummyOperator(task_id='maintenance_tasks')

    # Quality-based branches
    high_quality_path = DummyOperator(task_id='high_quality_path')
    medium_quality_path = DummyOperator(task_id='medium_quality_path')
    low_quality_path = DummyOperator(task_id='low_quality_path')

    # Join point - runs after any branch completes
    join = DummyOperator(
        task_id='join',
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS
    )

    # Define dependencies
    check_availability >> [
        process_customers,
        process_orders,
        process_products,
        no_data_available
    ] >> join

    day_branching >> [
        daily_processing,
        weekly_aggregation,
        maintenance_tasks
    ] >> join

    quality_branching >> [
        high_quality_path,
        medium_quality_path,
        low_quality_path
    ] >> join
```

## 🔄 Advanced DAG Patterns

### **Pattern 5: Retry and Recovery Pattern**

```python
# dags/retry_recovery_pattern.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.exceptions import AirflowException
import time
from typing import Any, Dict

class RetryableOperator(BaseOperator):
    """Operator with advanced retry logic."""

    @apply_defaults
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: int = 60,
        exponential_backoff: bool = True,
        partial_recovery: bool = True,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.partial_recovery = partial_recovery

    def execute(self, context: Dict[str, Any]):
        """Execute with retry logic."""

        attempt = 0
        last_error = None
        checkpoint = self._load_checkpoint(context)

        while attempt < self.max_retries:
            try:
                self.log.info(f"Attempt {attempt + 1} of {self.max_retries}")

                # Execute with checkpoint for partial recovery
                result = self._execute_with_checkpoint(context, checkpoint)

                # Success - clear checkpoint
                self._clear_checkpoint(context)
                return result

            except Exception as e:
                last_error = e
                attempt += 1

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = self._calculate_delay(attempt)
                    self.log.warning(
                        f"Attempt {attempt} failed: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)

                    # Save checkpoint for partial recovery
                    if self.partial_recovery:
                        checkpoint = self._save_checkpoint(context, e)
                else:
                    # Max retries reached
                    self._handle_final_failure(context, last_error)
                    raise AirflowException(
                        f"Task failed after {self.max_retries} attempts: {last_error}"
                    )

    def _execute_with_checkpoint(
        self,
        context: Dict[str, Any],
        checkpoint: Dict[str, Any]
    ):
        """Execute task with checkpoint for partial recovery."""

        # Override this in subclasses
        raise NotImplementedError()

    def _calculate_delay(self, attempt: int) -> int:
        """Calculate retry delay with optional exponential backoff."""

        if self.exponential_backoff:
            return self.retry_delay * (2 ** (attempt - 1))
        return self.retry_delay

    def _save_checkpoint(
        self,
        context: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """Save checkpoint for partial recovery."""

        checkpoint = {
            'task_id': self.task_id,
            'execution_date': str(context['execution_date']),
            'attempt': context['task_instance'].try_number,
            'error': str(error),
            'timestamp': time.time(),
            'state': self._get_current_state()
        }

        # Store in XCom for persistence
        context['task_instance'].xcom_push(
            key='checkpoint',
            value=checkpoint
        )

        return checkpoint

    def _load_checkpoint(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Load checkpoint from previous attempt."""

        return context['task_instance'].xcom_pull(
            key='checkpoint',
            task_ids=self.task_id
        ) or {}

    def _clear_checkpoint(self, context: Dict[str, Any]):
        """Clear checkpoint after successful completion."""

        # Clear XCom checkpoint
        context['task_instance'].xcom_push(
            key='checkpoint',
            value=None
        )

    def _handle_final_failure(
        self,
        context: Dict[str, Any],
        error: Exception
    ):
        """Handle final failure after all retries exhausted."""

        # Send alert
        self._send_failure_alert(context, error)

        # Log to dead letter queue
        self._log_to_dlq(context, error)

        # Trigger recovery DAG if configured
        if Variable.get('enable_recovery_dag', False):
            self._trigger_recovery_dag(context, error)

with DAG(
    'retry_recovery_pattern',
    default_args=default_args,
    description='DAG with advanced retry and recovery',
) as dag:

    class DataExtractionOperator(RetryableOperator):
        """Data extraction with checkpointing."""

        def _execute_with_checkpoint(
            self,
            context: Dict[str, Any],
            checkpoint: Dict[str, Any]
        ):
            # Resume from checkpoint if available
            start_offset = checkpoint.get('last_offset', 0)

            # Process data in chunks
            chunk_size = 1000
            total_rows = self._get_total_rows()

            for offset in range(start_offset, total_rows, chunk_size):
                try:
                    # Process chunk
                    self._process_chunk(offset, chunk_size)

                    # Update checkpoint
                    checkpoint['last_offset'] = offset + chunk_size
                    self._save_checkpoint(context, checkpoint)

                except Exception as e:
                    # Save checkpoint and re-raise
                    checkpoint['last_offset'] = offset
                    self._save_checkpoint(context, checkpoint)
                    raise

            return {'rows_processed': total_rows}

    extract_with_retry = DataExtractionOperator(
        task_id='extract_with_retry',
        max_retries=5,
        retry_delay=30,
        exponential_backoff=True,
        partial_recovery=True,
    )
```

### **Pattern 6: SLA and Alerting Pattern**

```python
# dags/sla_alerting_pattern.py
from airflow import DAG
from airflow.models import SLA
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):
    """Handle SLA misses."""

    logger = logging.getLogger(__name__)

    # Build alert message
    message = f"""
    SLA Miss Alert!

    DAG: {dag.dag_id}
    Tasks Missing SLA: {[t.task_id for t in task_list]}
    Blocking Tasks: {[t.task_id for t in blocking_task_list]}

    SLA Details:
    """

    for sla in slas:
        message += f"""
        - Task: {sla.task_id}
        - Expected: {sla.timestamp}
        - Execution Date: {sla.execution_date}
        """

    # Send alerts
    send_slack_alert(message)
    send_pagerduty_alert(message, severity='warning')

    # Log to monitoring system
    logger.error(f"SLA Miss: {message}")

with DAG(
    'sla_alerting_pattern',
    default_args={
        **default_args,
        'sla': timedelta(hours=2),  # Default SLA for all tasks
    },
    description='DAG with SLA monitoring and alerting',
    schedule_interval='@daily',
    catchup=False,
    sla_miss_callback=sla_miss_callback,
) as dag:

    def critical_data_processing(**context):
        """Critical task that must complete within SLA."""

        import time
        import random

        # Simulate processing
        processing_time = random.randint(1, 10)
        time.sleep(processing_time)

        # Check if we're approaching SLA
        task_instance = context['task_instance']
        elapsed = (datetime.now() - task_instance.start_date).total_seconds()
        sla_seconds = task_instance.task.sla.total_seconds()

        if elapsed > (sla_seconds * 0.8):  # 80% of SLA
            # Send warning
            logger.warning(
                f"Task {task_instance.task_id} is approaching SLA. "
                f"Elapsed: {elapsed}s, SLA: {sla_seconds}s"
            )
            send_slack_alert(
                f"⚠️ Task {task_instance.task_id} at 80% of SLA",
                severity='warning'
            )

    # Tasks with different SLAs
    critical_task = PythonOperator(
        task_id='critical_processing',
        python_callable=critical_data_processing,
        sla=timedelta(minutes=30),  # Strict SLA
        execution_timeout=timedelta(minutes=45),  # Hard timeout
        on_failure_callback=lambda context: send_pagerduty_alert(
            f"Critical task {context['task'].task_id} failed!",
            severity='critical'
        ),
    )

    standard_task = PythonOperator(
        task_id='standard_processing',
        python_callable=lambda: None,
        sla=timedelta(hours=2),  # Standard SLA
    )

    best_effort_task = PythonOperator(
        task_id='best_effort_processing',
        python_callable=lambda: None,
        # No SLA - best effort
    )

    critical_task >> standard_task >> best_effort_task
```

## 🎭 Task Group Patterns

### **Pattern 7: Reusable Task Groups**

```python
# dags/task_group_patterns.py
from airflow.utils.task_group import TaskGroup
from typing import List, Optional

class DataQualityTaskGroup(TaskGroup):
    """Reusable task group for data quality checks."""

    def __init__(
        self,
        group_id: str,
        schema: str,
        tables: List[str],
        quality_checks: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(group_id=group_id, **kwargs)

        self.schema = schema
        self.tables = tables
        self.quality_checks = quality_checks or [
            'null_check',
            'uniqueness_check',
            'referential_integrity',
            'business_rules'
        ]

        self._create_quality_tasks()

    def _create_quality_tasks(self):
        """Create quality check tasks for each table."""

        from airflow.operators.python import PythonOperator

        for table in self.tables:
            with TaskGroup(
                group_id=f"{table}_checks",
                parent_group=self
            ) as table_group:

                for check in self.quality_checks:
                    PythonOperator(
                        task_id=f"{check}_{table}",
                        python_callable=self._run_quality_check,
                        op_kwargs={
                            'schema': self.schema,
                            'table': table,
                            'check_type': check
                        }
                    )

    @staticmethod
    def _run_quality_check(schema: str, table: str, check_type: str):
        """Run a specific quality check."""

        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id='warehouse')

        checks = {
            'null_check': f"""
                SELECT COUNT(*) as null_count
                FROM {schema}.{table}
                WHERE id IS NULL
            """,
            'uniqueness_check': f"""
                SELECT COUNT(*) - COUNT(DISTINCT id) as duplicates
                FROM {schema}.{table}
            """,
            'referential_integrity': f"""
                SELECT COUNT(*) as orphans
                FROM {schema}.{table} t
                LEFT JOIN {schema}.{table}_parent p
                ON t.parent_id = p.id
                WHERE p.id IS NULL AND t.parent_id IS NOT NULL
            """,
            'business_rules': f"""
                SELECT COUNT(*) as violations
                FROM {schema}.{table}
                WHERE created_at > updated_at
                   OR amount < 0
                   OR status NOT IN ('active', 'inactive', 'pending')
            """
        }

        query = checks.get(check_type)
        if query:
            result = hook.get_first(query)[0]
            if result > 0:
                raise AirflowException(
                    f"Quality check {check_type} failed for {schema}.{table}: "
                    f"{result} violations found"
                )

# Using the reusable task group
with DAG(
    'reusable_task_groups',
    default_args=default_args,
    description='DAG with reusable task groups',
) as dag:

    # Bronze quality checks
    bronze_quality = DataQualityTaskGroup(
        group_id='bronze_quality',
        schema='bronze',
        tables=['br_customers', 'br_orders', 'br_products'],
        quality_checks=['null_check']
    )

    # Silver quality checks
    silver_quality = DataQualityTaskGroup(
        group_id='silver_quality',
        schema='silver',
        tables=['customers', 'orders', 'products'],
        quality_checks=['null_check', 'uniqueness_check', 'business_rules']
    )

    # Gold quality checks
    gold_quality = DataQualityTaskGroup(
        group_id='gold_quality',
        schema='gold',
        tables=['dim_customer', 'fact_orders'],
        quality_checks=['null_check', 'uniqueness_check', 'referential_integrity']
    )

    bronze_quality >> silver_quality >> gold_quality
```

## 📋 DAG Best Practices

### **1. DAG Configuration**

```python
# ✅ Good: Comprehensive DAG configuration
with DAG(
    dag_id='well_configured_dag',

    # Clear ownership
    default_args={
        'owner': 'data-team',
        'depends_on_past': False,
        'email': ['data-team@company.com'],
        'email_on_failure': True,
        'email_on_retry': False,
    },

    # Proper scheduling
    start_date=datetime(2024, 1, 1),
    schedule_interval='0 2 * * *',  # Explicit cron
    catchup=False,

    # Resource management
    max_active_runs=1,
    max_active_tasks=10,

    # Documentation
    description='Process customer data daily',
    doc_md="""
    ## Purpose
    This DAG processes customer data daily

    ## SLA
    Must complete by 4 AM

    ## Contacts
    - Data Team: data-team@company.com
    - On-call: #data-oncall
    """,

    # Monitoring
    tags=['production', 'critical', 'customer'],
    sla_miss_callback=alert_on_sla_miss,
    on_failure_callback=alert_on_failure,

) as dag:
    # Tasks here
    pass

# ❌ Bad: Minimal configuration
with DAG(
    'poorly_configured_dag',
    start_date=datetime(2024, 1, 1),
) as dag:
    # No owner, no docs, no alerts
    pass
```

### **2. Task Dependencies**

```python
# ✅ Good: Clear, logical dependencies
extract >> validate >> transform >> load >> quality_check

# ✅ Good: Using task groups for clarity
with TaskGroup('extraction') as extract:
    extract_a >> extract_b

with TaskGroup('transformation') as transform:
    transform_a >> transform_b

extract >> transform

# ❌ Bad: Complex, hard to follow dependencies
task1 >> task2
task3 >> task2
task1 >> task4
task4 >> task5
task2 >> task5
task3 >> task5
```

### **3. Error Handling**

```python
# ✅ Good: Comprehensive error handling
def robust_task(**context):
    try:
        # Main logic
        result = process_data()

        # Validate result
        if not validate_result(result):
            raise ValueError("Result validation failed")

        return result

    except ConnectionError as e:
        # Specific handling for connection issues
        logger.error(f"Connection failed: {e}")
        # Retry with different connection
        return process_data(backup_connection)

    except Exception as e:
        # Log error with context
        logger.error(
            f"Task {context['task'].task_id} failed: {e}",
            extra={
                'dag_id': context['dag'].dag_id,
                'execution_date': context['execution_date'],
                'try_number': context['task_instance'].try_number
            }
        )
        # Send alert
        send_alert(context, e)
        raise

# ❌ Bad: No error handling
def fragile_task(**context):
    return process_data()  # Will fail silently
```

## 🔗 Related Documentation

- [Developer Workflows](developer-workflows.md) - Development patterns
- [Testing Strategies](testing-strategies.md) - Testing DAGs
- [Performance & Scaling](performance-scaling.md) - DAG optimization
- [Monitoring & Observability](monitoring-observability.md) - DAG monitoring

---

*Well-designed DAGs are the foundation of reliable data pipelines.*