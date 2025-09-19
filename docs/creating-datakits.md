# Creating Datakits

A comprehensive guide to building, testing, and deploying datakits - containerized Python packages that extract data from source systems into the Bronze layer of our data warehouse.

## 🎯 What Are Datakits?

Datakits are our standardized approach to data extraction, providing:
- **Consistency**: All extractors follow the same pattern
- **Portability**: Run anywhere Docker runs
- **Testability**: Unit and integration tests included
- **Observability**: Built-in logging and metrics
- **Maintainability**: Version controlled and documented

## 📚 Documentation Structure

This guide is organized into focused sub-guides for different aspects of datakit development:

### Core Guides
- **[Datakit Architecture](datakits/architecture.md)** - Understanding the design and components
- **[Quick Start Tutorial](datakits/quick-start.md)** - Build your first datakit in 15 minutes
- **[Development Workflow](datakits/development-workflow.md)** - Step-by-step development process

### Source-Specific Guides
- **[PostgreSQL Datakits](datakits/sources/postgresql.md)** - Extracting from PostgreSQL databases
- **[SQL Server Datakits](datakits/sources/sqlserver.md)** - SQL Server with Windows Authentication
- **[REST API Datakits](datakits/sources/rest-api.md)** - Consuming REST APIs
- **[File-Based Datakits](datakits/sources/file-based.md)** - Processing CSV, JSON, Parquet files
- **[Salesforce Datakits](datakits/sources/salesforce.md)** - Salesforce SOQL extraction
- **[Kafka Datakits](datakits/sources/kafka.md)** - Streaming data from Kafka

### Advanced Topics
- **[Authentication Patterns](datakits/authentication.md)** - OAuth, Kerberos, API keys
- **[Error Handling](datakits/error-handling.md)** - Retry logic and failure recovery
- **[Performance Optimization](datakits/performance.md)** - Chunking, parallel processing
- **[Testing Strategies](datakits/testing.md)** - Unit, integration, and E2E testing
- **[Monitoring & Metrics](datakits/monitoring.md)** - Instrumentation and observability

## 🚀 Quick Overview

### Basic Datakit Structure

```
my-datakit/
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── datakit/
│   ├── __init__.py
│   ├── extractor.py
│   ├── config.py
│   ├── models.py
│   └── utils.py
├── tests/
│   ├── __init__.py
│   ├── test_extractor.py
│   └── fixtures/
└── README.md
```

### Minimal Example

```python
# datakit/extractor.py
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataExtractor:
    """Extract data from source to Bronze layer."""

    def __init__(self):
        self.source_url = os.getenv('SOURCE_DATABASE_URL')
        self.target_url = os.getenv('WAREHOUSE_DATABASE_URL')

    def extract(self, table_name: str) -> int:
        """Extract a table from source to bronze."""
        logger.info(f"Starting extraction for {table_name}")

        # Connect to source
        source_engine = create_engine(self.source_url)

        # Read data
        df = pd.read_sql_table(table_name, source_engine)

        # Add metadata
        df['_bronze_loaded_at'] = datetime.now()
        df['_bronze_source'] = 'production_db'

        # Write to bronze
        target_engine = create_engine(self.target_url)
        df.to_sql(
            f'br_{table_name}',
            target_engine,
            schema='bronze',
            if_exists='replace',
            index=False
        )

        rows = len(df)
        logger.info(f"Extracted {rows} rows to bronze.br_{table_name}")
        return rows

if __name__ == '__main__':
    import sys
    extractor = DataExtractor()
    table = sys.argv[1] if len(sys.argv) > 1 else 'customers'
    extractor.extract(table)
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY datakit/ ./datakit/

# Set entrypoint
ENTRYPOINT ["python", "-m", "datakit.extractor"]
```

## 🔄 Development Process

### Step 1: Choose Your Template
```bash
# Clone the appropriate template
git clone templates/datakit-postgres my-postgres-datakit
# or
git clone templates/datakit-api my-api-datakit
```

### Step 2: Customize for Your Source
```python
# Modify the extractor for your specific needs
class MySourceExtractor(DataExtractor):
    def extract(self, config):
        # Your extraction logic
        pass
```

### Step 3: Test Locally
```bash
# Run tests
pytest tests/

# Test with Docker
docker build -t my-datakit:test .
docker run --env-file .env.test my-datakit:test
```

### Step 4: Deploy
```bash
# Tag and push
docker tag my-datakit:test registry.localhost/etl/my-datakit:1.0.0
docker push registry.localhost/etl/my-datakit:1.0.0
```

## 📊 Datakit Categories

### **1. Database Extractors**
Extract from relational databases using SQL queries.

**Examples**: PostgreSQL, MySQL, SQL Server, Oracle

**Key Features**:
- Connection pooling
- Incremental extraction
- Schema discovery
- Type mapping

[Learn more →](datakits/sources/postgresql.md)

### **2. API Extractors**
Consume data from REST and GraphQL APIs.

**Examples**: REST APIs, GraphQL, SOAP

**Key Features**:
- Pagination handling
- Rate limiting
- Authentication management
- Response parsing

[Learn more →](datakits/sources/rest-api.md)

### **3. File Processors**
Process files from various sources.

**Examples**: S3, SFTP, Local filesystem

**Key Features**:
- Format detection
- Compression handling
- Schema inference
- Chunked processing

[Learn more →](datakits/sources/file-based.md)

### **4. Stream Consumers**
Consume from streaming platforms.

**Examples**: Kafka, Kinesis, Pub/Sub

**Key Features**:
- Offset management
- Batch accumulation
- Schema registry integration
- Exactly-once semantics

[Learn more →](datakits/sources/kafka.md)

### **5. SaaS Connectors**
Extract from SaaS platforms.

**Examples**: Salesforce, HubSpot, Stripe

**Key Features**:
- OAuth authentication
- Bulk API usage
- Field mapping
- Incremental sync

[Learn more →](datakits/sources/salesforce.md)

## 🏗️ Standard Patterns

### Configuration Management
```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class ExtractorConfig:
    """Configuration for data extraction."""
    source_host: str = os.getenv('SOURCE_HOST', 'localhost')
    source_port: int = int(os.getenv('SOURCE_PORT', '5432'))
    source_database: str = os.getenv('SOURCE_DATABASE', 'production')
    batch_size: int = int(os.getenv('BATCH_SIZE', '10000'))
    max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
```

### Error Handling
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientExtractor:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    def extract_with_retry(self, table: str):
        """Extract with automatic retry."""
        return self.extract(table)
```

### Logging and Metrics
```python
import structlog
from prometheus_client import Counter, Histogram

logger = structlog.get_logger()

extraction_counter = Counter(
    'datakit_extractions_total',
    'Total number of extractions',
    ['source', 'table', 'status']
)

extraction_duration = Histogram(
    'datakit_extraction_duration_seconds',
    'Duration of extractions',
    ['source', 'table']
)
```

## 🧪 Testing Requirements

Every datakit must include:

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test with real connections
3. **Contract Tests**: Verify output schema
4. **Performance Tests**: Validate resource usage

See [Testing Strategies](datakits/testing.md) for detailed examples.

## 📦 Packaging and Distribution

### Version Management
```bash
# Semantic versioning
git tag -a v1.0.0 -m "Initial release"
git tag -a v1.1.0 -m "Add incremental extraction"
git tag -a v2.0.0 -m "Breaking: Change schema format"
```

### Registry Organization
```
registry.localhost/
├── etl/
│   ├── postgres-extractor:1.0.0
│   ├── postgres-extractor:1.1.0
│   ├── postgres-extractor:latest
│   ├── sqlserver-extractor:1.0.0
│   └── api-extractor:2.0.0
```

## 🎯 Best Practices

### DO's
✅ Keep datakits focused on a single source
✅ Use environment variables for configuration
✅ Include comprehensive logging
✅ Handle errors gracefully
✅ Write tests for edge cases
✅ Document expected schemas
✅ Version your containers

### DON'Ts
❌ Hard-code credentials
❌ Transform data (that's Silver layer's job)
❌ Skip error handling
❌ Ignore memory constraints
❌ Forget about timezones
❌ Mix multiple sources in one datakit

## 🔍 Troubleshooting Common Issues

| Issue | Solution |
|-------|----------|
| Connection timeouts | Increase timeout, check network |
| Memory errors | Use chunking, increase container memory |
| Schema changes | Implement schema evolution strategy |
| Authentication failures | Check credentials, verify network policies |
| Slow extraction | Add indexes, use parallel processing |

For detailed troubleshooting, see [Datakit Troubleshooting](datakits/troubleshooting.md).

## 📚 Further Reading

- **[Datakit Architecture](datakits/architecture.md)** - Deep dive into design decisions
- **[Performance Optimization](datakits/performance.md)** - Make your datakits faster
- **[Security Considerations](datakits/security.md)** - Secure credential handling
- **[Migration Guide](datakits/migration.md)** - Converting existing scripts

## 💡 Quick Links

- [Template Repository](https://github.com/yourorg/datakit-templates)
- [Example Datakits](../layer2-datakits/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Packaging Guide](https://packaging.python.org/)

---

*Ready to build your first datakit? Start with the [Quick Start Tutorial](datakits/quick-start.md).*