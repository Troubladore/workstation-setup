# API Reference Documentation

Comprehensive API reference for the Astronomer Airflow platform, including REST APIs, Python SDK, and CLI interfaces.

## 🎯 API Overview

Our platform provides multiple API interfaces for different use cases:

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│                  (Kong / Traefik)                       │
└─────────────┬───────────────────────────────────────────┘
              │
    ┌─────────┴─────────┬──────────────┬────────────────┐
    ▼                   ▼              ▼                ▼
┌─────────┐     ┌──────────┐   ┌──────────┐    ┌──────────┐
│Airflow  │     │Platform  │   │DataKit   │    │Analytics │
│REST API │     │Admin API │   │Registry  │    │Query API │
└─────────┘     └──────────┘   └──────────┘    └──────────┘
```

## 📚 API Documentation Structure

### Core APIs
- **[Airflow REST API](#airflow-rest-api)** - DAG and task management
- **[Platform Admin API](#platform-admin-api)** - Platform configuration
- **[DataKit Registry API](#datakit-registry-api)** - DataKit management
- **[Analytics Query API](#analytics-query-api)** - Data warehouse queries

### Client Libraries
- **[Python SDK](#python-sdk)** - Python client library
- **[CLI Reference](#cli-reference)** - Command-line interface
- **[GraphQL API](#graphql-api)** - GraphQL endpoint

## 🔐 Authentication

### **API Key Authentication**

```python
# Python example
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://airflow.example.com/api/v1/dags',
    headers=headers
)
```

```bash
# Curl example
curl -X GET https://airflow.example.com/api/v1/dags \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json"
```

### **OAuth 2.0 Authentication**

```python
# OAuth flow example
from requests_oauthlib import OAuth2Session

client_id = 'your-client-id'
client_secret = 'your-client-secret'
redirect_uri = 'https://your-app.com/callback'
authorization_base_url = 'https://airflow.example.com/oauth/authorize'
token_url = 'https://airflow.example.com/oauth/token'

# Create OAuth2 session
oauth = OAuth2Session(client_id, redirect_uri=redirect_uri)

# Get authorization URL
authorization_url, state = oauth.authorization_url(authorization_base_url)
print(f'Please authorize: {authorization_url}')

# After authorization, exchange code for token
authorization_response = input('Paste the full redirect URL here: ')
token = oauth.fetch_token(
    token_url,
    authorization_response=authorization_response,
    client_secret=client_secret
)

# Make authenticated requests
response = oauth.get('https://airflow.example.com/api/v1/dags')
```

## 📡 Airflow REST API

### **DAG Operations**

#### List DAGs
```http
GET /api/v1/dags
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Number of items to return (default: 100) |
| offset | integer | Number of items to skip |
| order_by | string | Field to order by |
| tags | array | Filter by tags |
| only_active | boolean | Only show active DAGs |

**Response:**
```json
{
  "dags": [
    {
      "dag_id": "bronze_to_silver_pipeline",
      "description": "ETL pipeline from bronze to silver layer",
      "file_token": "Ii9vcHQvYWlyZmxvdy9kYWdzL2Jyb256ZV90b19zaWx2ZXIucHki.YLhATQ.0K",
      "fileloc": "/opt/airflow/dags/bronze_to_silver.py",
      "has_import_errors": false,
      "has_task_concurrency_limits": false,
      "is_active": true,
      "is_paused": false,
      "is_subdag": false,
      "last_parsed_time": "2024-01-15T10:30:00Z",
      "max_active_runs": 1,
      "max_active_tasks": 16,
      "next_dagrun": "2024-01-16T00:00:00Z",
      "next_dagrun_create_after": "2024-01-16T00:00:00Z",
      "owners": ["data-team"],
      "root_dag_id": null,
      "schedule_interval": {
        "__type": "CronExpression",
        "value": "0 0 * * *"
      },
      "tags": [
        {"name": "production"},
        {"name": "etl"}
      ]
    }
  ],
  "total_entries": 15
}
```

#### Get DAG Details
```http
GET /api/v1/dags/{dag_id}
```

**Example:**
```bash
curl -X GET "https://airflow.example.com/api/v1/dags/bronze_to_silver_pipeline" \
  -H "X-API-Key: your-api-key"
```

#### Trigger DAG Run
```http
POST /api/v1/dags/{dag_id}/dagRuns
```

**Request Body:**
```json
{
  "conf": {
    "batch_size": 1000,
    "parallel_tasks": 4,
    "target_table": "silver.customers"
  },
  "dag_run_id": "manual_2024_01_15",
  "data_interval_end": "2024-01-15T23:59:59Z",
  "data_interval_start": "2024-01-15T00:00:00Z",
  "note": "Manual trigger for customer data refresh"
}
```

**Response:**
```json
{
  "conf": {
    "batch_size": 1000,
    "parallel_tasks": 4,
    "target_table": "silver.customers"
  },
  "dag_id": "bronze_to_silver_pipeline",
  "dag_run_id": "manual_2024_01_15",
  "data_interval_end": "2024-01-15T23:59:59Z",
  "data_interval_start": "2024-01-15T00:00:00Z",
  "end_date": null,
  "execution_date": "2024-01-15T00:00:00Z",
  "external_trigger": true,
  "last_scheduling_decision": null,
  "logical_date": "2024-01-15T00:00:00Z",
  "note": "Manual trigger for customer data refresh",
  "run_type": "manual",
  "start_date": "2024-01-15T10:30:00Z",
  "state": "running"
}
```

#### Update DAG
```http
PATCH /api/v1/dags/{dag_id}
```

**Request Body:**
```json
{
  "is_paused": true
}
```

### **Task Operations**

#### List Tasks
```http
GET /api/v1/dags/{dag_id}/tasks
```

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "validate_source_data",
      "owner": "data-team",
      "start_date": "2024-01-01T00:00:00Z",
      "end_date": null,
      "trigger_rule": "all_success",
      "extra_links": [],
      "depends_on_past": false,
      "wait_for_downstream": false,
      "retries": 2,
      "retry_delay": {
        "__type": "TimeDelta",
        "days": 0,
        "seconds": 300,
        "microseconds": 0
      },
      "retry_exponential_backoff": false,
      "max_retry_delay": null,
      "ui_color": "#e8f7e4",
      "ui_fgcolor": "#000",
      "template_fields": ["source_table", "target_table"],
      "downstream_task_ids": ["transform_to_silver"],
      "upstream_task_ids": []
    }
  ],
  "total_entries": 5
}
```

#### Get Task Instance
```http
GET /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}
```

**Response:**
```json
{
  "dag_id": "bronze_to_silver_pipeline",
  "dag_run_id": "scheduled__2024-01-15T00:00:00+00:00",
  "duration": 125.5,
  "end_date": "2024-01-15T00:02:05.500000Z",
  "execution_date": "2024-01-15T00:00:00Z",
  "executor_config": {},
  "hostname": "airflow-worker-0",
  "map_index": -1,
  "max_tries": 2,
  "note": null,
  "operator": "PythonOperator",
  "pid": 12345,
  "pool": "default_pool",
  "pool_slots": 1,
  "priority_weight": 1,
  "queue": "default",
  "queued_when": "2024-01-15T00:00:00Z",
  "rendered_fields": {
    "source_table": "bronze.customers_raw",
    "target_table": "silver.customers"
  },
  "sla_miss": null,
  "start_date": "2024-01-15T00:00:00Z",
  "state": "success",
  "task_id": "validate_source_data",
  "try_number": 1,
  "unixname": "airflow"
}
```

#### Update Task Instance State
```http
PATCH /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances/{task_id}
```

**Request Body:**
```json
{
  "dry_run": false,
  "new_state": "success"
}
```

### **DAG Run Operations**

#### List DAG Runs
```http
GET /api/v1/dags/{dag_id}/dagRuns
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Number of items to return |
| offset | integer | Number of items to skip |
| execution_date_gte | string | Filter by execution date >= |
| execution_date_lte | string | Filter by execution date <= |
| state | array | Filter by state |

#### Delete DAG Run
```http
DELETE /api/v1/dags/{dag_id}/dagRuns/{dag_run_id}
```

## 🛠️ Platform Admin API

### **Tenant Management**

#### Create Tenant
```http
POST /api/v1/platform/tenants
```

**Request Body:**
```json
{
  "tenant_id": "analytics-team",
  "display_name": "Analytics Team",
  "namespace": "analytics",
  "resource_limits": {
    "cpu": "4000m",
    "memory": "16Gi",
    "storage": "100Gi"
  },
  "features": {
    "datakits": true,
    "custom_operators": true,
    "external_connections": true
  },
  "admin_users": ["alice@example.com", "bob@example.com"],
  "metadata": {
    "cost_center": "CC-123",
    "department": "Analytics",
    "environment": "production"
  }
}
```

#### Update Tenant Configuration
```http
PATCH /api/v1/platform/tenants/{tenant_id}
```

**Request Body:**
```json
{
  "resource_limits": {
    "cpu": "8000m",
    "memory": "32Gi"
  },
  "features": {
    "gpu_support": true
  }
}
```

### **Connection Management**

#### Create Connection
```http
POST /api/v1/platform/connections
```

**Request Body:**
```json
{
  "connection_id": "warehouse_prod",
  "connection_type": "postgres",
  "host": "warehouse.example.com",
  "port": 5432,
  "schema": "analytics",
  "login": "airflow_user",
  "password": "encrypted_password",
  "extra": {
    "sslmode": "require",
    "connect_timeout": 10
  }
}
```

#### Test Connection
```http
POST /api/v1/platform/connections/{connection_id}/test
```

**Response:**
```json
{
  "status": "success",
  "message": "Connection successfully tested",
  "latency_ms": 45
}
```

## 📦 DataKit Registry API

### **DataKit Operations**

#### Register DataKit
```http
POST /api/v1/datakits
```

**Request Body:**
```json
{
  "name": "customer-360-datakit",
  "version": "1.2.0",
  "description": "Customer 360 view transformation pipeline",
  "image": "registry.localhost/datakits/customer-360:1.2.0",
  "type": "transformation",
  "inputs": [
    {
      "name": "customers",
      "type": "table",
      "schema": "bronze"
    },
    {
      "name": "orders",
      "type": "table",
      "schema": "bronze"
    }
  ],
  "outputs": [
    {
      "name": "customer_360",
      "type": "table",
      "schema": "gold"
    }
  ],
  "configuration": {
    "batch_size": {
      "type": "integer",
      "default": 1000,
      "description": "Processing batch size"
    },
    "parallel_tasks": {
      "type": "integer",
      "default": 4,
      "description": "Number of parallel tasks"
    }
  },
  "requirements": {
    "cpu": "2000m",
    "memory": "4Gi",
    "gpu": false
  },
  "tags": ["customer", "gold-layer", "analytics"]
}
```

#### List DataKits
```http
GET /api/v1/datakits
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| type | string | Filter by type (transformation, ingestion, export) |
| tags | array | Filter by tags |
| search | string | Search in name and description |

#### Deploy DataKit
```http
POST /api/v1/datakits/{datakit_id}/deploy
```

**Request Body:**
```json
{
  "environment": "production",
  "namespace": "analytics",
  "configuration": {
    "batch_size": 5000,
    "parallel_tasks": 8
  },
  "schedule": "0 2 * * *",
  "notifications": {
    "on_success": ["success@example.com"],
    "on_failure": ["alerts@example.com"]
  }
}
```

## 📊 Analytics Query API

### **Query Execution**

#### Execute Query
```http
POST /api/v1/analytics/query
```

**Request Body:**
```json
{
  "query": "SELECT customer_segment, COUNT(*) as customer_count, AVG(lifetime_value) as avg_ltv FROM gold.dim_customer WHERE is_active = true GROUP BY customer_segment ORDER BY avg_ltv DESC",
  "database": "warehouse",
  "limit": 1000,
  "timeout_seconds": 30,
  "parameters": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }
}
```

**Response:**
```json
{
  "query_id": "q_123456789",
  "status": "completed",
  "rows_returned": 4,
  "execution_time_ms": 245,
  "data": [
    {
      "customer_segment": "Diamond",
      "customer_count": 127,
      "avg_ltv": 15234.56
    },
    {
      "customer_segment": "Gold",
      "customer_count": 892,
      "avg_ltv": 7123.45
    }
  ],
  "metadata": {
    "database": "warehouse",
    "schema": "gold",
    "tables_accessed": ["dim_customer"],
    "bytes_scanned": 1048576,
    "cache_hit": false
  }
}
```

#### Get Query Status
```http
GET /api/v1/analytics/query/{query_id}
```

#### Cancel Query
```http
POST /api/v1/analytics/query/{query_id}/cancel
```

### **Saved Queries**

#### Save Query
```http
POST /api/v1/analytics/saved-queries
```

**Request Body:**
```json
{
  "name": "Monthly Revenue Report",
  "description": "Monthly revenue breakdown by region and product",
  "query": "SELECT DATE_TRUNC('month', order_date) as month, region, product_category, SUM(total_amount) as revenue FROM gold.fact_orders WHERE order_date >= :start_date GROUP BY 1, 2, 3",
  "parameters": [
    {
      "name": "start_date",
      "type": "date",
      "default": "2024-01-01",
      "required": true
    }
  ],
  "tags": ["revenue", "monthly", "report"],
  "schedule": "0 8 1 * *",
  "output_format": "csv",
  "destination": "s3://reports/monthly/"
}
```

## 🐍 Python SDK

### **Installation**

```bash
pip install airflow-platform-sdk
```

### **Client Initialization**

```python
from airflow_platform import PlatformClient

# Initialize client with API key
client = PlatformClient(
    base_url='https://airflow.example.com',
    api_key='your-api-key'
)

# Or with OAuth
client = PlatformClient(
    base_url='https://airflow.example.com',
    client_id='your-client-id',
    client_secret='your-client-secret'
)
```

### **DAG Management**

```python
# List DAGs
dags = client.dags.list(tags=['production'], only_active=True)
for dag in dags:
    print(f"{dag.dag_id}: {dag.description}")

# Get DAG details
dag = client.dags.get('bronze_to_silver_pipeline')
print(f"Schedule: {dag.schedule_interval}")
print(f"Next run: {dag.next_dagrun}")

# Trigger DAG
run = client.dags.trigger(
    dag_id='bronze_to_silver_pipeline',
    conf={'batch_size': 5000},
    run_id=f'manual_{datetime.now().isoformat()}'
)
print(f"Started run: {run.dag_run_id}")

# Monitor DAG run
while run.state not in ['success', 'failed']:
    time.sleep(30)
    run.refresh()
    print(f"Status: {run.state}")

# Pause/unpause DAG
client.dags.pause('bronze_to_silver_pipeline')
client.dags.unpause('bronze_to_silver_pipeline')
```

### **Task Management**

```python
# Get task instances
task_instances = client.tasks.get_instances(
    dag_id='bronze_to_silver_pipeline',
    dag_run_id='scheduled__2024-01-15T00:00:00+00:00'
)

for ti in task_instances:
    print(f"{ti.task_id}: {ti.state} (duration: {ti.duration}s)")

# Retry failed task
client.tasks.clear(
    dag_id='bronze_to_silver_pipeline',
    task_id='transform_to_silver',
    dag_run_id='scheduled__2024-01-15T00:00:00+00:00'
)

# Get task logs
logs = client.tasks.get_logs(
    dag_id='bronze_to_silver_pipeline',
    task_id='validate_source_data',
    dag_run_id='scheduled__2024-01-15T00:00:00+00:00',
    try_number=1
)
print(logs)
```

### **Connection Management**

```python
# Create connection
conn = client.connections.create(
    connection_id='new_warehouse',
    connection_type='postgres',
    host='warehouse.example.com',
    port=5432,
    schema='analytics',
    login='user',
    password='password'
)

# Test connection
result = client.connections.test('new_warehouse')
if result.status == 'success':
    print("Connection successful!")

# Update connection
client.connections.update(
    connection_id='new_warehouse',
    extra={'sslmode': 'require'}
)

# Delete connection
client.connections.delete('new_warehouse')
```

### **DataKit Operations**

```python
# Register DataKit
datakit = client.datakits.register(
    name='customer-etl',
    version='1.0.0',
    image='registry.localhost/datakits/customer-etl:1.0.0',
    inputs=[{'name': 'customers', 'type': 'table'}],
    outputs=[{'name': 'dim_customer', 'type': 'table'}]
)

# Deploy DataKit
deployment = client.datakits.deploy(
    datakit_id=datakit.id,
    environment='production',
    schedule='0 2 * * *',
    configuration={'batch_size': 1000}
)

# Monitor deployment
status = client.datakits.get_deployment_status(deployment.id)
print(f"Deployment status: {status}")
```

### **Analytics Queries**

```python
# Execute query
result = client.analytics.query(
    """
    SELECT
        DATE_TRUNC('day', order_date) as date,
        COUNT(*) as order_count,
        SUM(total_amount) as revenue
    FROM gold.fact_orders
    WHERE order_date >= :start_date
    GROUP BY 1
    ORDER BY 1
    """,
    parameters={'start_date': '2024-01-01'}
)

# Convert to DataFrame
import pandas as pd
df = pd.DataFrame(result.data)
print(df.describe())

# Save query for reuse
saved_query = client.analytics.save_query(
    name='Daily Revenue',
    query=result.query,
    parameters=result.parameters,
    tags=['revenue', 'daily']
)

# Execute saved query
result = client.analytics.execute_saved_query(
    saved_query.id,
    parameters={'start_date': '2024-02-01'}
)
```

## 💻 CLI Reference

### **Installation**

```bash
# Install CLI
pip install airflow-platform-cli

# Configure authentication
airflow-cli config set api_key your-api-key
airflow-cli config set base_url https://airflow.example.com
```

### **DAG Commands**

```bash
# List DAGs
airflow-cli dags list
airflow-cli dags list --tags production,critical

# Get DAG details
airflow-cli dags get bronze_to_silver_pipeline

# Trigger DAG
airflow-cli dags trigger bronze_to_silver_pipeline
airflow-cli dags trigger bronze_to_silver_pipeline --conf '{"batch_size": 5000}'

# Pause/unpause DAG
airflow-cli dags pause bronze_to_silver_pipeline
airflow-cli dags unpause bronze_to_silver_pipeline

# Backfill DAG
airflow-cli dags backfill bronze_to_silver_pipeline \
  --start-date 2024-01-01 \
  --end-date 2024-01-31
```

### **Task Commands**

```bash
# List tasks
airflow-cli tasks list bronze_to_silver_pipeline

# Get task details
airflow-cli tasks get bronze_to_silver_pipeline validate_source_data

# Clear task instance
airflow-cli tasks clear bronze_to_silver_pipeline \
  --task validate_source_data \
  --execution-date 2024-01-15

# Get task logs
airflow-cli tasks logs bronze_to_silver_pipeline \
  --task validate_source_data \
  --execution-date 2024-01-15 \
  --follow
```

### **Connection Commands**

```bash
# List connections
airflow-cli connections list

# Create connection
airflow-cli connections create warehouse_prod \
  --type postgres \
  --host warehouse.example.com \
  --port 5432 \
  --schema analytics \
  --login airflow \
  --password-stdin < password.txt

# Test connection
airflow-cli connections test warehouse_prod

# Export connections
airflow-cli connections export --output connections.yaml

# Import connections
airflow-cli connections import --file connections.yaml
```

### **DataKit Commands**

```bash
# List DataKits
airflow-cli datakits list
airflow-cli datakits list --type transformation

# Register DataKit
airflow-cli datakits register \
  --file datakit.yaml \
  --image registry.localhost/datakits/my-datakit:1.0.0

# Deploy DataKit
airflow-cli datakits deploy customer-360-datakit \
  --environment production \
  --schedule "0 2 * * *"

# Get deployment status
airflow-cli datakits status customer-360-datakit

# Rollback deployment
airflow-cli datakits rollback customer-360-datakit --version 1.1.0
```

## 🔄 GraphQL API

### **Schema**

```graphql
type Query {
  dag(id: ID!): DAG
  dags(
    filter: DAGFilter
    limit: Int = 100
    offset: Int = 0
  ): DAGConnection!

  dagRun(dagId: ID!, runId: ID!): DAGRun
  dagRuns(
    dagId: ID!
    filter: DAGRunFilter
    limit: Int = 100
    offset: Int = 0
  ): DAGRunConnection!

  taskInstance(
    dagId: ID!
    runId: ID!
    taskId: ID!
  ): TaskInstance

  metrics(
    dagId: ID
    startDate: DateTime!
    endDate: DateTime!
  ): Metrics!
}

type Mutation {
  triggerDAG(
    dagId: ID!
    conf: JSON
    runId: String
  ): DAGRun!

  pauseDAG(dagId: ID!): DAG!
  unpauseDAG(dagId: ID!): DAG!

  clearTask(
    dagId: ID!
    runId: ID!
    taskId: ID!
  ): TaskInstance!

  createConnection(input: ConnectionInput!): Connection!
  updateConnection(
    id: ID!
    input: ConnectionUpdateInput!
  ): Connection!
  deleteConnection(id: ID!): Boolean!
}

type DAG {
  id: ID!
  description: String
  isPaused: Boolean!
  isActive: Boolean!
  scheduleInterval: String
  tags: [Tag!]!
  owners: [String!]!
  tasks: [Task!]!
  runs(
    filter: DAGRunFilter
    limit: Int = 10
  ): DAGRunConnection!
  metrics(
    startDate: DateTime!
    endDate: DateTime!
  ): DAGMetrics!
}

type DAGRun {
  id: ID!
  dagId: ID!
  executionDate: DateTime!
  state: DAGRunState!
  startDate: DateTime
  endDate: DateTime
  duration: Float
  conf: JSON
  taskInstances: [TaskInstance!]!
}

type TaskInstance {
  id: ID!
  taskId: ID!
  dagId: ID!
  runId: ID!
  state: TaskState!
  startDate: DateTime
  endDate: DateTime
  duration: Float
  tryNumber: Int!
  maxTries: Int!
  logs(tryNumber: Int): String
}
```

### **Query Examples**

```graphql
# Get DAG with recent runs
query GetDAGWithRuns {
  dag(id: "bronze_to_silver_pipeline") {
    id
    description
    isPaused
    scheduleInterval
    tags {
      name
    }
    runs(limit: 5) {
      edges {
        node {
          id
          executionDate
          state
          duration
          taskInstances {
            taskId
            state
            duration
          }
        }
      }
    }
    metrics(
      startDate: "2024-01-01T00:00:00Z"
      endDate: "2024-01-31T23:59:59Z"
    ) {
      totalRuns
      successfulRuns
      failedRuns
      averageDuration
      successRate
    }
  }
}

# Trigger DAG
mutation TriggerDAG {
  triggerDAG(
    dagId: "bronze_to_silver_pipeline"
    conf: {
      batch_size: 5000
      parallel_tasks: 8
    }
  ) {
    id
    state
    executionDate
  }
}

# Get task logs
query GetTaskLogs {
  taskInstance(
    dagId: "bronze_to_silver_pipeline"
    runId: "scheduled__2024-01-15T00:00:00+00:00"
    taskId: "validate_source_data"
  ) {
    taskId
    state
    startDate
    endDate
    duration
    logs(tryNumber: 1)
  }
}
```

## 🔒 Rate Limiting

API rate limits are enforced per API key:

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| GET requests | 1000 req | 1 minute |
| POST/PUT/PATCH | 100 req | 1 minute |
| DELETE | 50 req | 1 minute |
| Analytics queries | 100 req | 1 hour |
| Bulk operations | 10 req | 1 minute |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
```

## 🚨 Error Handling

### **Error Response Format**

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "DAG 'non_existent_dag' not found",
    "details": {
      "dag_id": "non_existent_dag",
      "available_dags": ["dag1", "dag2", "dag3"]
    },
    "request_id": "req_123456789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### **Common Error Codes**

| Code | HTTP Status | Description |
|------|-------------|-------------|
| AUTHENTICATION_FAILED | 401 | Invalid or missing credentials |
| PERMISSION_DENIED | 403 | Insufficient permissions |
| RESOURCE_NOT_FOUND | 404 | Resource does not exist |
| VALIDATION_ERROR | 400 | Invalid request parameters |
| CONFLICT | 409 | Resource already exists |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable |

## 📦 Webhooks

### **Webhook Configuration**

```json
{
  "webhook_id": "wh_123456",
  "name": "DAG Success Notifier",
  "url": "https://your-app.com/webhooks/airflow",
  "events": [
    "dag.success",
    "dag.failure",
    "task.failure"
  ],
  "filters": {
    "dag_ids": ["bronze_to_silver_pipeline", "silver_to_gold_pipeline"],
    "tags": ["production"]
  },
  "headers": {
    "X-Webhook-Secret": "your-secret-key"
  },
  "retry_policy": {
    "max_attempts": 3,
    "backoff_seconds": [10, 30, 60]
  }
}
```

### **Webhook Payload**

```json
{
  "event": "dag.success",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "dag_id": "bronze_to_silver_pipeline",
    "dag_run_id": "scheduled__2024-01-15T00:00:00+00:00",
    "execution_date": "2024-01-15T00:00:00Z",
    "start_date": "2024-01-15T00:00:00Z",
    "end_date": "2024-01-15T00:05:30Z",
    "duration_seconds": 330,
    "state": "success",
    "conf": {},
    "external_trigger": false
  }
}
```

## 💡 API Best Practices

### **Pagination**
```python
# Paginate through large result sets
all_dags = []
offset = 0
limit = 100

while True:
    response = client.dags.list(limit=limit, offset=offset)
    all_dags.extend(response.dags)

    if len(response.dags) < limit:
        break

    offset += limit
```

### **Error Handling**
```python
from airflow_platform.exceptions import (
    RateLimitError,
    AuthenticationError,
    ResourceNotFoundError
)

try:
    dag = client.dags.get('my_dag')
except ResourceNotFoundError:
    print("DAG not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    time.sleep(e.retry_after)
except AuthenticationError:
    print("Authentication failed. Check your credentials")
```

### **Async Operations**
```python
import asyncio
from airflow_platform import AsyncPlatformClient

async def trigger_multiple_dags():
    async with AsyncPlatformClient(api_key='your-key') as client:
        tasks = [
            client.dags.trigger(f'dag_{i}')
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        return results
```

---

*Continue with [Deployment and CI/CD Guide](deployment-cicd.md) for production deployment strategies.*