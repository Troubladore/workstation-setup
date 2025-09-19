# Testing Strategies Guide

A comprehensive guide to testing Airflow DAGs, data pipelines, and ensuring data quality across all layers of the platform.

## 🎯 Testing Philosophy

Our testing strategy follows the **Testing Pyramid** principle adapted for data pipelines:

```
        ╱╲          E2E Tests
       ╱  ╲         (Production validation)
      ╱────╲
     ╱      ╲       Integration Tests
    ╱────────╲      (DAG runs, data flows)
   ╱          ╲
  ╱────────────╲    Unit Tests
 ╱              ╲   (Tasks, functions, transformations)
╱________________╲
```

### **Core Testing Principles**

1. **Test Early and Often** - Catch issues before production
2. **Data Quality as Code** - Define expectations programmatically
3. **Automated Validation** - CI/CD integration for all tests
4. **Production Monitoring** - Continuous validation in production
5. **Fast Feedback Loops** - Quick test execution for rapid iteration

## 📚 Documentation Structure

### Testing Guides
- **[Unit Testing](testing/unit-testing.md)** - Testing individual tasks and functions
- **[Integration Testing](testing/integration-testing.md)** - Testing complete DAG runs
- **[Data Quality Testing](testing/data-quality.md)** - Validating data expectations
- **[Performance Testing](testing/performance.md)** - Load and stress testing
- **[End-to-End Testing](testing/e2e-testing.md)** - Production validation

### Advanced Topics
- **[Mocking Strategies](testing/mocking.md)** - Simulating external dependencies
- **[Test Data Management](testing/test-data.md)** - Managing test datasets
- **[CI/CD Integration](testing/cicd.md)** - Automated testing pipelines
- **[Monitoring as Testing](testing/monitoring.md)** - Production validation

## 🧪 Testing Layers

### **1. Unit Tests** (Foundation)

Test individual components in isolation:

```python
# tests/unit/test_transformations.py
import pytest
from datetime import datetime
from airflow.models import DagBag
from dags.bronze_to_silver import BronzeToSilverPipeline

class TestTransformations:
    """Test individual transformation functions"""

    def test_clean_customer_data(self):
        """Test customer data cleaning logic"""
        # Arrange
        raw_data = {
            'customer_id': '  123  ',
            'email': 'USER@EXAMPLE.COM  ',
            'name': 'john doe',
            'age': '25',
            'created_at': '2024-01-15T10:30:00'
        }

        # Act
        pipeline = BronzeToSilverPipeline()
        cleaned = pipeline.clean_customer_data(raw_data)

        # Assert
        assert cleaned['customer_id'] == '123'
        assert cleaned['email'] == 'user@example.com'
        assert cleaned['name'] == 'John Doe'
        assert cleaned['age'] == 25
        assert isinstance(cleaned['created_at'], datetime)

    def test_validate_email_format(self):
        """Test email validation logic"""
        pipeline = BronzeToSilverPipeline()

        # Valid emails
        assert pipeline.validate_email('user@example.com') == True
        assert pipeline.validate_email('user.name+tag@example.co.uk') == True

        # Invalid emails
        assert pipeline.validate_email('invalid.email') == False
        assert pipeline.validate_email('@example.com') == False
        assert pipeline.validate_email('user@') == False

    def test_calculate_metrics(self):
        """Test metric calculation functions"""
        orders = [
            {'amount': 100, 'quantity': 2},
            {'amount': 200, 'quantity': 1},
            {'amount': 150, 'quantity': 3}
        ]

        pipeline = BronzeToSilverPipeline()
        metrics = pipeline.calculate_order_metrics(orders)

        assert metrics['total_revenue'] == 450
        assert metrics['total_quantity'] == 6
        assert metrics['average_order_value'] == 150
        assert metrics['order_count'] == 3

class TestDagStructure:
    """Test DAG configuration and structure"""

    def test_dag_loaded(self):
        """Test that DAG is properly loaded"""
        dagbag = DagBag(include_examples=False)
        assert 'bronze_to_silver_pipeline' in dagbag.dags

        dag = dagbag.dags['bronze_to_silver_pipeline']
        assert dag is not None
        assert dag.default_args['retries'] == 2
        assert dag.schedule_interval == '@daily'

    def test_task_dependencies(self):
        """Test task dependency structure"""
        dagbag = DagBag(include_examples=False)
        dag = dagbag.dags['bronze_to_silver_pipeline']

        # Check upstream/downstream relationships
        validate_task = dag.get_task('validate_source_data')
        transform_task = dag.get_task('transform_to_silver')

        assert transform_task in validate_task.downstream_list
        assert validate_task in transform_task.upstream_list

    def test_required_connections(self):
        """Test that required connections are defined"""
        from airflow.models import Connection
        from airflow.utils.db import create_session

        required_connections = ['warehouse_db', 's3_bronze', 'slack_alerts']

        with create_session() as session:
            for conn_id in required_connections:
                conn = session.query(Connection).filter(
                    Connection.conn_id == conn_id
                ).first()
                assert conn is not None, f"Required connection {conn_id} not found"
```

### **2. Integration Tests** (DAG Execution)

Test complete DAG runs with mock data:

```python
# tests/integration/test_dag_runs.py
import pytest
from datetime import datetime, timedelta
from airflow.models import DagRun, TaskInstance
from airflow.utils.state import State
from airflow.test.utils import TestExecutor

class TestDagExecution:
    """Test complete DAG execution flows"""

    @pytest.fixture
    def test_dag(self):
        """Fixture to provide test DAG"""
        from dags.bronze_to_silver import create_dag
        return create_dag()

    def test_successful_dag_run(self, test_dag):
        """Test successful end-to-end DAG execution"""
        # Create test execution date
        execution_date = datetime(2024, 1, 15)

        # Create DAG run
        dag_run = DagRun(
            dag_id=test_dag.dag_id,
            execution_date=execution_date,
            run_type='test'
        )

        # Execute DAG
        with TestExecutor() as executor:
            test_dag.run(
                start_date=execution_date,
                end_date=execution_date,
                executor=executor
            )

        # Verify all tasks succeeded
        task_instances = dag_run.get_task_instances()
        for ti in task_instances:
            assert ti.state == State.SUCCESS

    def test_retry_on_failure(self, test_dag, mock_external_api):
        """Test retry mechanism on task failure"""
        # Configure mock to fail twice then succeed
        mock_external_api.side_effect = [
            Exception("API Error"),
            Exception("API Error"),
            {"status": "success"}
        ]

        execution_date = datetime(2024, 1, 15)

        # Execute DAG
        test_dag.run(start_date=execution_date, end_date=execution_date)

        # Check that task was retried
        ti = TaskInstance(
            task=test_dag.get_task('fetch_external_data'),
            execution_date=execution_date
        )

        assert ti.try_number == 3
        assert ti.state == State.SUCCESS

    def test_data_quality_gates(self, test_dag, test_database):
        """Test data quality validation gates"""
        # Insert test data with quality issues
        test_database.insert_bronze_data([
            {'customer_id': None, 'email': 'test@example.com'},  # Missing ID
            {'customer_id': '123', 'email': 'invalid-email'},    # Invalid email
            {'customer_id': '124', 'email': 'valid@example.com'} # Valid record
        ])

        execution_date = datetime(2024, 1, 15)

        # Execute DAG
        test_dag.run(start_date=execution_date, end_date=execution_date)

        # Verify quality gate task caught issues
        quality_task = TaskInstance(
            task=test_dag.get_task('data_quality_check'),
            execution_date=execution_date
        )

        # Check that bad records were quarantined
        assert test_database.get_quarantine_count() == 2
        assert test_database.get_silver_count() == 1
```

### **3. Data Quality Tests** (Validation)

Implement comprehensive data quality checks:

```python
# tests/data_quality/test_data_expectations.py
import great_expectations as ge
from great_expectations.core import ExpectationSuite
from datakit.quality import DataQualityValidator

class TestDataQuality:
    """Test data quality expectations"""

    def test_bronze_data_schema(self, bronze_dataframe):
        """Test bronze layer data schema"""
        validator = DataQualityValidator()

        # Define expectations
        expectations = ExpectationSuite(
            expectation_suite_name="bronze_data_expectations"
        )

        # Schema expectations
        expectations.add_expectation(
            ge.expectations.expect_table_columns_to_match_set(
                column_set=['customer_id', 'email', 'name', 'created_at']
            )
        )

        # Data type expectations
        expectations.add_expectation(
            ge.expectations.expect_column_values_to_be_of_type(
                column='customer_id', type='string'
            )
        )

        # Run validation
        results = validator.validate(bronze_dataframe, expectations)
        assert results.success == True

    def test_silver_data_quality(self, silver_dataframe):
        """Test silver layer data quality"""
        validator = DataQualityValidator()

        # Create comprehensive expectations
        expectations = ExpectationSuite("silver_data_expectations")

        # Uniqueness constraints
        expectations.add_expectation(
            ge.expectations.expect_column_values_to_be_unique(
                column='customer_id'
            )
        )

        # Nullability constraints
        expectations.add_expectation(
            ge.expectations.expect_column_values_to_not_be_null(
                column='email'
            )
        )

        # Format validations
        expectations.add_expectation(
            ge.expectations.expect_column_values_to_match_regex(
                column='email',
                regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            )
        )

        # Business rule validations
        expectations.add_expectation(
            ge.expectations.expect_column_values_to_be_between(
                column='age',
                min_value=0,
                max_value=120
            )
        )

        results = validator.validate(silver_dataframe, expectations)
        assert results.success == True

    def test_gold_aggregation_accuracy(self, gold_metrics):
        """Test gold layer aggregation accuracy"""
        # Verify aggregations match source data
        source_total = self.calculate_source_metrics()
        gold_total = gold_metrics['total_revenue']

        # Allow for small floating point differences
        assert abs(source_total - gold_total) < 0.01

        # Verify completeness
        assert gold_metrics['record_count'] == self.get_expected_count()

        # Verify no data duplication
        assert gold_metrics['unique_customers'] == gold_metrics['total_customers']
```

### **4. Performance Tests** (Load Testing)

Test pipeline performance under load:

```python
# tests/performance/test_pipeline_performance.py
import time
import concurrent.futures
from locust import HttpUser, task, between

class TestPipelinePerformance:
    """Test pipeline performance characteristics"""

    def test_processing_speed(self, large_dataset):
        """Test processing speed with large dataset"""
        start_time = time.time()

        pipeline = BronzeToSilverPipeline()
        pipeline.process(large_dataset)  # 1M records

        elapsed_time = time.time() - start_time
        records_per_second = len(large_dataset) / elapsed_time

        # Performance assertions
        assert elapsed_time < 300  # Should complete in 5 minutes
        assert records_per_second > 3000  # At least 3k records/sec

    def test_memory_usage(self, memory_profiler):
        """Test memory usage during processing"""
        pipeline = BronzeToSilverPipeline()

        with memory_profiler.monitor() as monitor:
            pipeline.process_batch(size=100000)

        peak_memory = monitor.peak_memory_mb
        assert peak_memory < 2048  # Should use less than 2GB

    def test_concurrent_processing(self):
        """Test concurrent DAG execution"""
        def run_pipeline(execution_date):
            dag = create_dag()
            return dag.run(execution_date=execution_date)

        # Run 10 concurrent DAG executions
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                execution_date = datetime.now() - timedelta(days=i)
                futures.append(executor.submit(run_pipeline, execution_date))

            # Wait for all to complete
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.state == State.SUCCESS for r in results)

class LoadTestUser(HttpUser):
    """Locust load test for API endpoints"""
    wait_time = between(1, 3)

    @task
    def trigger_dag(self):
        """Test DAG trigger endpoint under load"""
        response = self.client.post(
            "/api/v1/dags/bronze_to_silver/dagRuns",
            json={"execution_date": "2024-01-15T00:00:00Z"}
        )
        assert response.status_code == 200

    @task
    def query_dag_status(self):
        """Test DAG status query endpoint"""
        response = self.client.get(
            "/api/v1/dags/bronze_to_silver/dagRuns/latest"
        )
        assert response.status_code == 200
```

## 🔧 Testing Infrastructure

### **Test Environment Setup**

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  test-postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: airflow_test
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
    ports:
      - "5433:5432"
    volumes:
      - ./tests/fixtures/init.sql:/docker-entrypoint-initdb.d/init.sql

  test-redis:
    image: redis:7
    ports:
      - "6380:6379"

  test-minio:
    image: minio/minio:latest
    command: server /data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9001:9000"
    volumes:
      - ./tests/fixtures/data:/data

  airflow-test:
    build:
      context: .
      dockerfile: Dockerfile.test
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@test-postgres/airflow_test
      AIRFLOW__CELERY__BROKER_URL: redis://test-redis:6379/0
      _AIRFLOW_DB_MIGRATE: 'true'
      _AIRFLOW_WWW_USER_CREATE: 'true'
    volumes:
      - ./dags:/opt/airflow/dags
      - ./tests:/opt/airflow/tests
      - ./plugins:/opt/airflow/plugins
    depends_on:
      - test-postgres
      - test-redis
      - test-minio
```

### **Pytest Configuration**

```python
# pytest.ini
[tool:pytest]
minversion = 6.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --cov=dags
    --cov=plugins
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --maxfail=1
    --disable-warnings
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    e2e: End-to-end tests
    slow: Tests that take more than 30 seconds

# conftest.py
import pytest
import os
from airflow import settings
from airflow.models import DagBag, Variable
from airflow.configuration import conf
from sqlalchemy import create_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def airflow_db():
    """Provide test Airflow database"""
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        settings.configure_orm(engine)
        yield engine

@pytest.fixture(scope="session")
def test_dagbag():
    """Provide DagBag for testing"""
    return DagBag(
        dag_folder=os.path.join(os.path.dirname(__file__), "../dags"),
        include_examples=False
    )

@pytest.fixture
def reset_db(airflow_db):
    """Reset database between tests"""
    yield
    # Clean up after test
    airflow_db.execute("TRUNCATE TABLE dag_run CASCADE")
    airflow_db.execute("TRUNCATE TABLE task_instance CASCADE")

@pytest.fixture
def mock_variables():
    """Mock Airflow Variables"""
    variables = {
        "warehouse_connection": "postgresql://user:pass@localhost/warehouse",
        "s3_bucket": "test-bucket",
        "slack_webhook": "https://hooks.slack.com/test"
    }

    for key, value in variables.items():
        Variable.set(key, value)

    yield variables

    # Cleanup
    for key in variables:
        Variable.delete(key)
```

## 🚀 Test Execution Strategies

### **Local Testing**

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit           # Unit tests only
pytest -m integration    # Integration tests only
pytest -m "not slow"     # Skip slow tests

# Run with coverage
pytest --cov=dags --cov-report=html

# Run specific test file
pytest tests/unit/test_transformations.py

# Run with parallel execution
pytest -n 4  # Run on 4 cores

# Debug failed tests
pytest --pdb --lf  # Drop to debugger on failure, run last failed
```

### **Docker Testing**

```bash
# Build test environment
docker-compose -f docker-compose.test.yml build

# Run tests in container
docker-compose -f docker-compose.test.yml run --rm airflow-test pytest

# Run with test watcher
docker-compose -f docker-compose.test.yml run --rm airflow-test ptw

# Clean up test containers
docker-compose -f docker-compose.test.yml down -v
```

### **CI/CD Integration**

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt

      - name: Run unit tests
        run: |
          pytest -m unit --cov=dags --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Run integration tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm airflow-test \
            pytest -m integration

  data-quality-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run data quality tests
        run: |
          docker-compose -f docker-compose.test.yml run --rm airflow-test \
            pytest tests/data_quality/
```

## 📊 Test Metrics and Reporting

### **Coverage Reports**

```python
# Generate coverage report
# coverage_report.py
import coverage
import json

def generate_coverage_report():
    """Generate detailed coverage report"""
    cov = coverage.Coverage()
    cov.load()

    # Generate JSON report
    json_report = cov.json_report()

    # Calculate metrics
    metrics = {
        'total_coverage': json_report['totals']['percent_covered'],
        'files': {}
    }

    for file_path, file_data in json_report['files'].items():
        metrics['files'][file_path] = {
            'coverage': file_data['summary']['percent_covered'],
            'missing_lines': file_data['missing_lines'],
            'excluded_lines': file_data['excluded_lines']
        }

    # Generate report
    with open('coverage_report.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    # Check thresholds
    if metrics['total_coverage'] < 80:
        raise Exception(f"Coverage {metrics['total_coverage']}% is below 80% threshold")

if __name__ == "__main__":
    generate_coverage_report()
```

### **Test Results Dashboard**

```python
# test_dashboard.py
from flask import Flask, render_template
import json
import sqlite3

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Display test results dashboard"""
    # Get latest test results
    conn = sqlite3.connect('test_results.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            run_date,
            total_tests,
            passed_tests,
            failed_tests,
            skipped_tests,
            duration_seconds,
            coverage_percent
        FROM test_runs
        ORDER BY run_date DESC
        LIMIT 30
    """)

    results = cursor.fetchall()

    return render_template('dashboard.html', results=results)

@app.route('/api/metrics')
def metrics():
    """API endpoint for test metrics"""
    conn = sqlite3.connect('test_results.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            AVG(coverage_percent) as avg_coverage,
            AVG(duration_seconds) as avg_duration,
            SUM(passed_tests) * 100.0 / SUM(total_tests) as pass_rate
        FROM test_runs
        WHERE run_date >= date('now', '-30 days')
    """)

    metrics = cursor.fetchone()

    return json.dumps({
        'average_coverage': metrics[0],
        'average_duration': metrics[1],
        'pass_rate': metrics[2]
    })
```

## 🛡️ Best Practices

### **DO's**
✅ Write tests before code (TDD approach)
✅ Keep tests independent and isolated
✅ Use meaningful test names that describe behavior
✅ Mock external dependencies
✅ Test both happy path and edge cases
✅ Maintain test data fixtures
✅ Regular test maintenance and updates
✅ Monitor test execution time

### **DON'Ts**
❌ Test implementation details
❌ Create interdependent tests
❌ Use production data in tests
❌ Skip testing error conditions
❌ Ignore flaky tests
❌ Hard-code test data
❌ Test third-party libraries

## 🔍 Common Testing Patterns

### **Fixture Management**

```python
# fixtures/data_fixtures.py
import json
from pathlib import Path

class DataFixtures:
    """Manage test data fixtures"""

    def __init__(self, fixture_path='tests/fixtures'):
        self.fixture_path = Path(fixture_path)

    def load_json(self, name):
        """Load JSON fixture"""
        with open(self.fixture_path / f"{name}.json") as f:
            return json.load(f)

    def load_csv(self, name):
        """Load CSV fixture"""
        import pandas as pd
        return pd.read_csv(self.fixture_path / f"{name}.csv")

    def create_sample_data(self, record_count=1000):
        """Generate sample data for testing"""
        from faker import Faker
        fake = Faker()

        data = []
        for _ in range(record_count):
            data.append({
                'customer_id': fake.uuid4(),
                'name': fake.name(),
                'email': fake.email(),
                'address': fake.address(),
                'phone': fake.phone_number(),
                'created_at': fake.date_time_this_year()
            })

        return data
```

### **Mock Patterns**

```python
# mocks/external_mocks.py
from unittest.mock import MagicMock, patch
import responses

class ExternalServiceMocks:
    """Mock external service interactions"""

    @staticmethod
    @patch('airflow.providers.amazon.aws.hooks.s3.S3Hook')
    def mock_s3(mock_hook):
        """Mock S3 interactions"""
        mock_s3 = MagicMock()
        mock_s3.check_for_key.return_value = True
        mock_s3.read_key.return_value = '{"data": "test"}'
        mock_hook.return_value = mock_s3
        return mock_s3

    @staticmethod
    @responses.activate
    def mock_api_endpoint():
        """Mock HTTP API endpoints"""
        responses.add(
            responses.GET,
            'https://api.example.com/data',
            json={'status': 'success', 'data': []},
            status=200
        )

    @staticmethod
    @patch('psycopg2.connect')
    def mock_database(mock_connect):
        """Mock database connections"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor.fetchall.return_value = [
            (1, 'Test User', 'test@example.com')
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        return mock_conn
```

## 💡 Quick Reference

### **Test Commands**

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests with coverage
pytest tests/integration/ --cov=dags

# Performance tests
pytest tests/performance/ -m performance

# Data quality tests
great_expectations checkpoint run bronze_quality_check

# Run specific test
pytest tests/unit/test_transformations.py::TestTransformations::test_clean_customer_data

# Debug test failures
pytest --pdb --lf

# Generate HTML coverage report
pytest --cov=dags --cov-report=html
open htmlcov/index.html

# Run tests in watch mode
ptw -- -x tests/

# Profile test performance
pytest --profile tests/performance/
```

### **Testing Checklist**

- [ ] Unit tests for all transformation functions
- [ ] Integration tests for complete DAG runs
- [ ] Data quality validation tests
- [ ] Performance benchmarks established
- [ ] Mock external dependencies
- [ ] Test data fixtures created
- [ ] CI/CD pipeline configured
- [ ] Coverage thresholds enforced (>80%)
- [ ] Test documentation updated
- [ ] Monitoring for test failures

---

*Continue with [Monitoring and Observability Guide](monitoring-observability.md) for production validation strategies.*