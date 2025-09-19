# Monitoring and Observability Guide

A comprehensive guide to monitoring, observability, and alerting for the Astronomer Airflow platform across all layers.

## 🎯 Observability Philosophy

Our observability strategy follows the **Three Pillars of Observability**:

```
     Metrics                  Logs                    Traces
        │                      │                         │
   ┌────▼────┐           ┌─────▼─────┐           ┌──────▼──────┐
   │ What's  │           │   What    │           │     How     │
   │ broken? │           │ happened? │           │   requests  │
   └────┬────┘           └─────┬─────┘           │    flow?    │
        │                      │                  └──────┬──────┘
        └──────────┬───────────┘                         │
                   ▼                                      ▼
            ┌──────────────┐                    ┌────────────────┐
            │  Prometheus  │                    │     Jaeger     │
            │   Grafana    │                    │    Zipkin      │
            └──────────────┘                    └────────────────┘
                   │                                      │
                   └──────────────┬───────────────────────┘
                                  ▼
                        ┌──────────────────┐
                        │   Correlation    │
                        │   & Analysis     │
                        └──────────────────┘
```

## 📚 Documentation Structure

### Core Monitoring
- **[Metrics Collection](monitoring/metrics.md)** - Prometheus metrics and exporters
- **[Logging Strategy](monitoring/logging.md)** - Centralized logging with ELK stack
- **[Distributed Tracing](monitoring/tracing.md)** - Request flow tracking
- **[Alerting Rules](monitoring/alerting.md)** - PagerDuty and Slack integration

### Advanced Topics
- **[Custom Metrics](monitoring/custom-metrics.md)** - Application-specific metrics
- **[SLA Monitoring](monitoring/sla.md)** - Service level tracking
- **[Cost Monitoring](monitoring/cost.md)** - Resource usage and optimization
- **[Security Monitoring](monitoring/security.md)** - Audit logs and compliance

## 🔍 Monitoring Stack

### **Infrastructure Overview**

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  # Metrics Collection
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/rules:/etc/prometheus/rules
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    networks:
      - monitoring

  # Visualization
  grafana:
    image: grafana/grafana:10.0.0
    container_name: grafana
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    ports:
      - "3000:3000"
    networks:
      - monitoring

  # Log Aggregation
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - monitoring

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: logstash
    volumes:
      - ./monitoring/logstash/pipeline:/usr/share/logstash/pipeline
      - ./monitoring/logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml
    ports:
      - "5000:5000/tcp"
      - "5000:5000/udp"
      - "9600:9600"
    environment:
      LS_JAVA_OPTS: "-Xmx256m -Xms256m"
    networks:
      - monitoring
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_URL: http://elasticsearch:9200
      ELASTICSEARCH_HOSTS: '["http://elasticsearch:9200"]'
    networks:
      - monitoring
    depends_on:
      - elasticsearch

  # Distributed Tracing
  jaeger:
    image: jaegertracing/all-in-one:1.48
    container_name: jaeger
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"
      - "14250:14250"
      - "14268:14268"
      - "14269:14269"
      - "9411:9411"
    networks:
      - monitoring

  # Alert Manager
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    volumes:
      - ./monitoring/alertmanager/config.yml:/etc/alertmanager/config.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:
  elasticsearch_data:
  alertmanager_data:

networks:
  monitoring:
    driver: bridge
```

## 📊 Metrics Collection

### **Airflow Metrics**

```python
# plugins/monitoring/airflow_metrics.py
from airflow.plugins_manager import AirflowPlugin
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client import push_to_gateway
import time

# Define metrics
dag_duration = Histogram(
    'airflow_dag_duration_seconds',
    'Duration of DAG in seconds',
    ['dag_id', 'execution_date']
)

task_duration = Histogram(
    'airflow_task_duration_seconds',
    'Duration of task in seconds',
    ['dag_id', 'task_id', 'execution_date']
)

dag_success_count = Counter(
    'airflow_dag_success_total',
    'Total successful DAG runs',
    ['dag_id']
)

dag_failure_count = Counter(
    'airflow_dag_failure_total',
    'Total failed DAG runs',
    ['dag_id']
)

task_success_count = Counter(
    'airflow_task_success_total',
    'Total successful task runs',
    ['dag_id', 'task_id']
)

task_failure_count = Counter(
    'airflow_task_failure_total',
    'Total failed task runs',
    ['dag_id', 'task_id']
)

active_dag_runs = Gauge(
    'airflow_active_dag_runs',
    'Number of active DAG runs',
    ['dag_id']
)

queued_tasks = Gauge(
    'airflow_queued_tasks',
    'Number of queued tasks'
)

class MetricsCollector:
    """Collect and export Airflow metrics"""

    def __init__(self, pushgateway_url='localhost:9091'):
        self.pushgateway_url = pushgateway_url
        self.registry = CollectorRegistry()

    def on_dag_success(self, context):
        """Record successful DAG execution"""
        dag_id = context['dag'].dag_id
        execution_date = context['execution_date']
        duration = context['dag_run'].end_date - context['dag_run'].start_date

        dag_success_count.labels(dag_id=dag_id).inc()
        dag_duration.labels(
            dag_id=dag_id,
            execution_date=str(execution_date)
        ).observe(duration.total_seconds())

        self.push_metrics()

    def on_dag_failure(self, context):
        """Record failed DAG execution"""
        dag_id = context['dag'].dag_id
        dag_failure_count.labels(dag_id=dag_id).inc()
        self.push_metrics()

    def on_task_success(self, context):
        """Record successful task execution"""
        dag_id = context['dag'].dag_id
        task_id = context['task'].task_id
        duration = context['task_instance'].end_date - context['task_instance'].start_date

        task_success_count.labels(dag_id=dag_id, task_id=task_id).inc()
        task_duration.labels(
            dag_id=dag_id,
            task_id=task_id,
            execution_date=str(context['execution_date'])
        ).observe(duration.total_seconds())

        self.push_metrics()

    def on_task_failure(self, context):
        """Record failed task execution"""
        dag_id = context['dag'].dag_id
        task_id = context['task'].task_id
        task_failure_count.labels(dag_id=dag_id, task_id=task_id).inc()
        self.push_metrics()

    def push_metrics(self):
        """Push metrics to Prometheus pushgateway"""
        try:
            push_to_gateway(
                self.pushgateway_url,
                job='airflow',
                registry=self.registry
            )
        except Exception as e:
            print(f"Failed to push metrics: {e}")

# Create global collector instance
metrics_collector = MetricsCollector()

class MetricsPlugin(AirflowPlugin):
    name = "metrics_plugin"
    callbacks = {
        'on_success_callback': metrics_collector.on_dag_success,
        'on_failure_callback': metrics_collector.on_dag_failure,
        'on_task_success_callback': metrics_collector.on_task_success,
        'on_task_failure_callback': metrics_collector.on_task_failure,
    }
```

### **Custom Business Metrics**

```python
# dags/metrics/business_metrics_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from prometheus_client import Gauge, push_to_gateway, CollectorRegistry
from datetime import datetime, timedelta

# Business metrics
revenue_metric = Gauge('business_revenue_total', 'Total revenue', ['region'])
order_count_metric = Gauge('business_orders_total', 'Total orders', ['status'])
customer_count_metric = Gauge('business_customers_active', 'Active customers')
inventory_metric = Gauge('business_inventory_level', 'Inventory level', ['product_category'])

def collect_business_metrics(**context):
    """Collect business metrics from data warehouse"""
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    # Connect to warehouse
    warehouse_hook = PostgresHook(postgres_conn_id='warehouse')

    # Collect revenue metrics
    revenue_query = """
        SELECT region, SUM(amount) as total_revenue
        FROM fact_orders
        WHERE order_date = CURRENT_DATE - 1
        GROUP BY region
    """
    revenue_results = warehouse_hook.get_records(revenue_query)

    for region, revenue in revenue_results:
        revenue_metric.labels(region=region).set(revenue)

    # Collect order metrics
    order_query = """
        SELECT status, COUNT(*) as order_count
        FROM fact_orders
        WHERE order_date = CURRENT_DATE - 1
        GROUP BY status
    """
    order_results = warehouse_hook.get_records(order_query)

    for status, count in order_results:
        order_count_metric.labels(status=status).set(count)

    # Collect customer metrics
    customer_query = """
        SELECT COUNT(DISTINCT customer_id) as active_customers
        FROM fact_orders
        WHERE order_date >= CURRENT_DATE - 30
    """
    customer_count = warehouse_hook.get_first(customer_query)[0]
    customer_count_metric.set(customer_count)

    # Push metrics to Prometheus
    registry = CollectorRegistry()
    registry.register(revenue_metric)
    registry.register(order_count_metric)
    registry.register(customer_count_metric)

    push_to_gateway('localhost:9091', job='business_metrics', registry=registry)

# Define DAG
dag = DAG(
    'business_metrics_collection',
    default_args={
        'owner': 'analytics',
        'depends_on_past': False,
        'email_on_failure': True,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5)
    },
    description='Collect business metrics for monitoring',
    schedule_interval='0 */1 * * *',  # Every hour
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['monitoring', 'metrics']
)

collect_metrics_task = PythonOperator(
    task_id='collect_business_metrics',
    python_callable=collect_business_metrics,
    dag=dag
)
```

## 📝 Logging Strategy

### **Structured Logging**

```python
# plugins/logging/structured_logger.py
import json
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging"""

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

        # Add Airflow context if available
        if hasattr(record, 'dag_id'):
            log_record['dag_id'] = record.dag_id
        if hasattr(record, 'task_id'):
            log_record['task_id'] = record.task_id
        if hasattr(record, 'execution_date'):
            log_record['execution_date'] = record.execution_date

class AirflowStructuredLogger:
    """Structured logger for Airflow tasks"""

    def __init__(self, name='airflow'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Configure JSON formatter
        logHandler = logging.StreamHandler()
        formatter = CustomJsonFormatter()
        logHandler.setFormatter(formatter)
        self.logger.addHandler(logHandler)

    def log_task_start(self, context):
        """Log task start event"""
        self.logger.info(
            "Task started",
            extra={
                'event': 'task_start',
                'dag_id': context['dag'].dag_id,
                'task_id': context['task'].task_id,
                'execution_date': str(context['execution_date']),
                'try_number': context['task_instance'].try_number
            }
        )

    def log_task_success(self, context, metrics=None):
        """Log task success event"""
        log_data = {
            'event': 'task_success',
            'dag_id': context['dag'].dag_id,
            'task_id': context['task'].task_id,
            'execution_date': str(context['execution_date']),
            'duration': str(context['task_instance'].end_date - context['task_instance'].start_date)
        }

        if metrics:
            log_data['metrics'] = metrics

        self.logger.info("Task completed successfully", extra=log_data)

    def log_task_failure(self, context, error=None):
        """Log task failure event"""
        self.logger.error(
            "Task failed",
            extra={
                'event': 'task_failure',
                'dag_id': context['dag'].dag_id,
                'task_id': context['task'].task_id,
                'execution_date': str(context['execution_date']),
                'error': str(error) if error else context.get('exception', 'Unknown error')
            }
        )

    def log_data_quality_issue(self, table, issue_type, details):
        """Log data quality issues"""
        self.logger.warning(
            "Data quality issue detected",
            extra={
                'event': 'data_quality_issue',
                'table': table,
                'issue_type': issue_type,
                'details': details,
                'timestamp': datetime.utcnow().isoformat()
            }
        )

# Usage in DAG
structured_logger = AirflowStructuredLogger()

def process_data(**context):
    structured_logger.log_task_start(context)

    try:
        # Process data
        records_processed = 1000
        structured_logger.log_task_success(
            context,
            metrics={'records_processed': records_processed}
        )
    except Exception as e:
        structured_logger.log_task_failure(context, error=e)
        raise
```

### **Logstash Configuration**

```ruby
# monitoring/logstash/pipeline/logstash.conf
input {
  # Airflow logs
  file {
    path => "/opt/airflow/logs/**/*.log"
    start_position => "beginning"
    codec => json
    type => "airflow"
  }

  # Application logs
  tcp {
    port => 5000
    codec => json_lines
    type => "application"
  }

  # Syslog
  syslog {
    port => 5514
    type => "syslog"
  }
}

filter {
  # Parse Airflow logs
  if [type] == "airflow" {
    grok {
      match => {
        "message" => "\[%{TIMESTAMP_ISO8601:timestamp}\] \{%{DATA:dag_id}:%{DATA:task_id}\} %{LOGLEVEL:level} - %{GREEDYDATA:message}"
      }
      overwrite => ["message"]
    }

    date {
      match => ["timestamp", "ISO8601"]
      target => "@timestamp"
    }

    mutate {
      add_field => {
        "environment" => "${ENVIRONMENT:dev}"
        "service" => "airflow"
      }
    }
  }

  # Parse application logs
  if [type] == "application" {
    json {
      source => "message"
    }

    if [level] {
      mutate {
        add_field => { "severity" => "%{level}" }
      }
    }
  }

  # Add geo-location for IP addresses
  if [client_ip] {
    geoip {
      source => "client_ip"
      target => "geoip"
    }
  }
}

output {
  # Send to Elasticsearch
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{type}-%{+YYYY.MM.dd}"
    template_name => "logs"
    template => "/usr/share/logstash/templates/logs.json"
    template_overwrite => true
  }

  # Send critical errors to stdout
  if [level] == "ERROR" or [level] == "CRITICAL" {
    stdout {
      codec => rubydebug
    }
  }
}
```

## 🔍 Distributed Tracing

### **OpenTelemetry Integration**

```python
# plugins/tracing/opentelemetry_config.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def configure_tracing():
    """Configure OpenTelemetry tracing"""
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
        collector_endpoint="http://jaeger:14268/api/traces"
    )

    # Add span processor
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Instrument libraries
    RequestsInstrumentor().instrument()
    Psycopg2Instrumentor().instrument()
    RedisInstrumentor().instrument()

    return trace.get_tracer(__name__)

# Initialize tracing
tracer = configure_tracing()

class TracedOperator:
    """Base class for operators with tracing"""

    def execute_with_tracing(self, context):
        """Execute operator with distributed tracing"""
        dag_id = context['dag'].dag_id
        task_id = context['task'].task_id

        with tracer.start_as_current_span(
            f"{dag_id}.{task_id}",
            attributes={
                "dag_id": dag_id,
                "task_id": task_id,
                "execution_date": str(context['execution_date']),
                "try_number": context['task_instance'].try_number
            }
        ) as span:
            try:
                result = self.execute(context)
                span.set_status(trace.Status(trace.StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(
                    trace.Status(trace.StatusCode.ERROR, str(e))
                )
                span.record_exception(e)
                raise
```

## 🚨 Alerting Configuration

### **Prometheus Alert Rules**

```yaml
# monitoring/prometheus/rules/airflow_alerts.yml
groups:
  - name: airflow_alerts
    interval: 30s
    rules:
      # DAG failure alerts
      - alert: HighDAGFailureRate
        expr: |
          rate(airflow_dag_failure_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          team: data-engineering
        annotations:
          summary: "High DAG failure rate detected"
          description: "DAG {{ $labels.dag_id }} has failure rate of {{ $value }} failures/sec"

      # Task queue alerts
      - alert: TaskQueueBacklog
        expr: |
          airflow_queued_tasks > 100
        for: 10m
        labels:
          severity: warning
          team: data-engineering
        annotations:
          summary: "Task queue backlog detected"
          description: "{{ $value }} tasks queued for more than 10 minutes"

      # Resource utilization alerts
      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes{name="airflow-scheduler"} / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          team: infrastructure
        annotations:
          summary: "High memory usage in Airflow scheduler"
          description: "Memory usage is {{ $value | humanizePercentage }} of limit"

      # SLA breach alerts
      - alert: SLABreach
        expr: |
          airflow_sla_missed_total > 0
        for: 1m
        labels:
          severity: critical
          team: data-engineering
        annotations:
          summary: "SLA breach detected"
          description: "DAG {{ $labels.dag_id }} missed SLA"

  - name: data_quality_alerts
    interval: 60s
    rules:
      - alert: DataFreshnessIssue
        expr: |
          time() - data_last_updated_timestamp > 7200
        for: 5m
        labels:
          severity: warning
          team: analytics
        annotations:
          summary: "Data freshness issue"
          description: "Table {{ $labels.table }} hasn't been updated for {{ $value | humanizeDuration }}"

      - alert: DataQualityCheckFailed
        expr: |
          data_quality_check_failed_total > 0
        for: 1m
        labels:
          severity: critical
          team: analytics
        annotations:
          summary: "Data quality check failed"
          description: "Quality check failed for {{ $labels.table }}: {{ $labels.check_type }}"
```

### **AlertManager Configuration**

```yaml
# monitoring/alertmanager/config.yml
global:
  resolve_timeout: 5m
  slack_api_url: ${SLACK_WEBHOOK_URL}
  pagerduty_url: https://events.pagerduty.com/v2/enqueue

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # Critical alerts go to PagerDuty
    - match:
        severity: critical
      receiver: pagerduty
      continue: true

    # All alerts go to Slack
    - match_re:
        severity: ^(warning|critical)$
      receiver: slack

receivers:
  - name: 'default'
    # Default receiver (no-op)

  - name: 'slack'
    slack_configs:
      - channel: '#alerts-data-platform'
        title: 'Data Platform Alert'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}{{ end }}'
        send_resolved: true
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: ${PAGERDUTY_SERVICE_KEY}
        client: 'Airflow Platform'
        client_url: 'https://airflow.example.com'
        description: '{{ .GroupLabels.alertname }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'
          alerts: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
```

## 📈 Grafana Dashboards

### **Airflow Overview Dashboard**

```json
{
  "dashboard": {
    "title": "Airflow Platform Overview",
    "panels": [
      {
        "title": "DAG Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(airflow_dag_success_total[5m]) / (rate(airflow_dag_success_total[5m]) + rate(airflow_dag_failure_total[5m])) * 100",
            "legendFormat": "{{ dag_id }}"
          }
        ]
      },
      {
        "title": "Active DAG Runs",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(airflow_active_dag_runs) by (dag_id)",
            "legendFormat": "{{ dag_id }}"
          }
        ]
      },
      {
        "title": "Task Duration P95",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(airflow_task_duration_seconds_bucket[5m])) by (dag_id, task_id)",
            "legendFormat": "{{ dag_id }}.{{ task_id }}"
          }
        ]
      },
      {
        "title": "Queue Depth",
        "type": "graph",
        "targets": [
          {
            "expr": "airflow_queued_tasks",
            "legendFormat": "Queued Tasks"
          }
        ]
      }
    ]
  }
}
```

### **Data Quality Dashboard**

```json
{
  "dashboard": {
    "title": "Data Quality Monitoring",
    "panels": [
      {
        "title": "Data Freshness",
        "type": "heatmap",
        "targets": [
          {
            "expr": "time() - data_last_updated_timestamp",
            "legendFormat": "{{ table }}"
          }
        ]
      },
      {
        "title": "Quality Check Pass Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(data_quality_check_passed_total[1h])) / (sum(rate(data_quality_check_passed_total[1h])) + sum(rate(data_quality_check_failed_total[1h]))) * 100"
          }
        ]
      },
      {
        "title": "Records Processed",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(records_processed_total[5m])) by (pipeline)",
            "legendFormat": "{{ pipeline }}"
          }
        ]
      },
      {
        "title": "Data Volume Trends",
        "type": "graph",
        "targets": [
          {
            "expr": "table_row_count",
            "legendFormat": "{{ table }}"
          }
        ]
      }
    ]
  }
}
```

## 🛡️ Security Monitoring

### **Audit Logging**

```python
# plugins/security/audit_logger.py
from airflow.models import Log
from airflow.utils.db import provide_session
from datetime import datetime
import json

class AuditLogger:
    """Security audit logging"""

    @provide_session
    def log_dag_access(self, user, dag_id, action, session=None):
        """Log DAG access events"""
        audit_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'user': user,
            'dag_id': dag_id,
            'action': action,
            'ip_address': self.get_client_ip(),
            'user_agent': self.get_user_agent()
        }

        log_entry = Log(
            dttm=datetime.utcnow(),
            dag_id=dag_id,
            task_id=None,
            event='dag_access',
            execution_date=None,
            owner=user,
            extra=json.dumps(audit_log)
        )

        session.add(log_entry)
        session.commit()

    def log_configuration_change(self, user, config_type, old_value, new_value):
        """Log configuration changes"""
        audit_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'user': user,
            'config_type': config_type,
            'old_value': old_value,
            'new_value': new_value,
            'change_type': 'configuration'
        }

        # Send to security SIEM
        self.send_to_siem(audit_log)

    def log_authentication_event(self, user, event_type, success):
        """Log authentication events"""
        audit_log = {
            'timestamp': datetime.utcnow().isoformat(),
            'user': user,
            'event_type': event_type,
            'success': success,
            'ip_address': self.get_client_ip()
        }

        # Track failed login attempts
        if not success:
            self.track_failed_login(user)

    def send_to_siem(self, event):
        """Send security event to SIEM"""
        # Implementation for your SIEM integration
        pass
```

## 📊 SLA Monitoring

```python
# dags/sla_monitoring_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.email.operators.email import EmailOperator
from datetime import datetime, timedelta

def check_sla_compliance(**context):
    """Check SLA compliance for critical pipelines"""
    from airflow.models import DagRun, TaskInstance
    from airflow.utils.db import provide_session

    @provide_session
    def get_sla_metrics(session=None):
        # Define SLAs
        slas = {
            'bronze_to_silver_pipeline': timedelta(hours=2),
            'silver_to_gold_pipeline': timedelta(hours=3),
            'customer_360_pipeline': timedelta(hours=4)
        }

        violations = []

        for dag_id, expected_duration in slas.items():
            # Get latest DAG run
            latest_run = session.query(DagRun).filter(
                DagRun.dag_id == dag_id
            ).order_by(DagRun.execution_date.desc()).first()

            if latest_run and latest_run.end_date:
                actual_duration = latest_run.end_date - latest_run.start_date
                if actual_duration > expected_duration:
                    violations.append({
                        'dag_id': dag_id,
                        'expected_duration': str(expected_duration),
                        'actual_duration': str(actual_duration),
                        'execution_date': str(latest_run.execution_date)
                    })

        return violations

    violations = get_sla_metrics()

    if violations:
        # Send alerts
        context['task_instance'].xcom_push(key='sla_violations', value=violations)
        return 'send_alert'
    else:
        return 'no_violations'

dag = DAG(
    'sla_monitoring',
    default_args={
        'owner': 'platform',
        'depends_on_past': False,
        'email_on_failure': True,
        'retries': 1
    },
    description='Monitor SLA compliance',
    schedule_interval='*/30 * * * *',  # Every 30 minutes
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['monitoring', 'sla']
)

check_sla_task = PythonOperator(
    task_id='check_sla_compliance',
    python_callable=check_sla_compliance,
    dag=dag
)
```

## 💡 Quick Reference

### **Monitoring Commands**

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Query metrics
curl 'http://localhost:9090/api/v1/query?query=up'

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health

# View Jaeger traces
open http://localhost:16686

# Test alert routing
amtool --alertmanager.url=http://localhost:9093 alert add \
  alertname="test" severity="warning" message="test alert"

# Export Grafana dashboard
curl -X GET http://admin:admin@localhost:3000/api/dashboards/uid/abc123 | jq '.dashboard' > dashboard.json

# Import Grafana dashboard
curl -X POST -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://admin:admin@localhost:3000/api/dashboards/db
```

### **Monitoring Checklist**

- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards configured
- [ ] Alert rules defined and tested
- [ ] Log aggregation working
- [ ] Distributed tracing enabled
- [ ] Custom metrics implemented
- [ ] SLA monitoring active
- [ ] Security audit logging enabled
- [ ] Alert routing configured
- [ ] Documentation updated

---

*Continue with [API Reference Documentation](api-reference.md) for comprehensive API documentation.*