# dbt Development Guide

A comprehensive guide to developing, testing, and deploying dbt (data build tool) transformations for the Silver and Gold layers of our data warehouse.

## 🎯 Why dbt?

dbt brings software engineering practices to SQL transformations:
- **Version Control**: All transformations in Git
- **Testing**: Data quality tests and schema validation
- **Documentation**: Self-documenting data models
- **Modularity**: Reusable macros and packages
- **Dependency Management**: Automatic DAG generation
- **Environment Management**: Dev/staging/prod configurations

## 📚 Documentation Structure

This guide is organized into comprehensive sub-guides for different aspects of dbt development:

### Core Guides
- **[dbt Architecture](dbt/architecture.md)** - Understanding dbt's design and our implementation
- **[Quick Start Tutorial](dbt/quick-start.md)** - Build your first dbt model in 15 minutes
- **[Development Workflow](dbt/development-workflow.md)** - Day-to-day dbt development process

### Model Development
- **[Silver Layer Models](dbt/models/silver-layer.md)** - Building business entity models
- **[Gold Layer Models](dbt/models/gold-layer.md)** - Creating facts and dimensions
- **[Incremental Models](dbt/models/incremental.md)** - Efficient incremental processing
- **[Snapshots (SCD Type 2)](dbt/models/snapshots.md)** - Slowly changing dimensions

### Advanced Topics
- **[Macros and Packages](dbt/macros-packages.md)** - Creating reusable components
- **[Testing Strategies](dbt/testing.md)** - Data quality and unit testing
- **[Documentation](dbt/documentation.md)** - Creating comprehensive model docs
- **[Performance Optimization](dbt/performance.md)** - Query optimization and materialization
- **[CI/CD Integration](dbt/cicd.md)** - Automated testing and deployment

## 🚀 Quick Overview

### Project Structure

```
layer2-dbt-projects/
├── silver-core/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── silver/
│   │   │   ├── customers.sql
│   │   │   ├── orders.sql
│   │   │   └── schema.yml
│   │   └── staging/
│   │       ├── stg_customers.sql
│   │       └── stg_orders.sql
│   ├── macros/
│   │   └── generate_alias.sql
│   ├── tests/
│   │   └── assert_positive_values.sql
│   └── snapshots/
│       └── customers_snapshot.sql
├── gold-dimensions/
│   ├── models/
│   │   └── dimensions/
│   │       ├── dim_customer.sql
│   │       ├── dim_product.sql
│   │       └── dim_date.sql
└── gold-facts/
    ├── models/
    │   └── facts/
    │       ├── fact_orders.sql
    │       └── fact_customer_lifetime.sql
    └── analyses/
        └── revenue_analysis.sql
```

### Basic dbt Model

```sql
-- models/silver/customers.sql
{{
    config(
        materialized='table',
        tags=['silver', 'customers', 'daily']
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('stg_customers') }}
),

cleaned AS (
    SELECT
        -- IDs
        customer_id,
        customer_uuid,

        -- PII
        {{ mask_pii('first_name') }} as first_name,
        {{ mask_pii('last_name') }} as last_name,
        {{ mask_pii('email') }} as email,

        -- Demographics
        date_of_birth,
        {{ calculate_age('date_of_birth') }} as age,
        gender,

        -- Location
        city,
        state,
        country,
        postal_code,

        -- Status
        status,
        is_active,

        -- Timestamps
        created_at,
        updated_at,

        -- Metadata
        CURRENT_TIMESTAMP as dbt_processed_at,
        '{{ invocation_id }}' as dbt_invocation_id

    FROM source
    WHERE customer_id IS NOT NULL
)

SELECT * FROM cleaned
```

## 🏗️ dbt Layers in Our Architecture

### **Staging Layer** (Bronze → Silver preparation)
```sql
-- models/staging/stg_customers.sql
WITH source AS (
    SELECT * FROM {{ source('bronze', 'br_customers') }}
),

typed AS (
    SELECT
        CAST(customer_id AS INTEGER) as customer_id,
        CAST(customer_uuid AS STRING) as customer_uuid,
        TRIM(first_name) as first_name,
        TRIM(last_name) as last_name,
        LOWER(TRIM(email)) as email,
        TO_DATE(date_of_birth, 'YYYY-MM-DD') as date_of_birth,
        UPPER(gender) as gender,
        CAST(is_active AS BOOLEAN) as is_active,
        TO_TIMESTAMP(created_at) as created_at,
        TO_TIMESTAMP(updated_at) as updated_at
    FROM source
)

SELECT * FROM typed
```

### **Silver Layer** (Business Entities)
```sql
-- models/silver/orders.sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        on_schema_change='sync_all_columns'
    )
}}

WITH staged AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
    WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
),

enriched AS (
    SELECT
        o.*,
        c.customer_segment,
        c.lifetime_value,
        p.product_category,
        p.product_subcategory
    FROM staged o
    LEFT JOIN {{ ref('customers') }} c
        ON o.customer_id = c.customer_id
    LEFT JOIN {{ ref('products') }} p
        ON o.product_id = p.product_id
)

SELECT * FROM enriched
```

### **Gold Dimensions** (Conformed Dimensions)
```sql
-- models/gold/dimensions/dim_customer.sql
{{
    config(
        materialized='table',
        tags=['gold', 'dimension', 'customer']
    )
}}

WITH customers AS (
    SELECT * FROM {{ ref('customers') }}
),

orders AS (
    SELECT
        customer_id,
        COUNT(*) as total_orders,
        SUM(order_amount) as lifetime_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        AVG(order_amount) as avg_order_value
    FROM {{ ref('orders') }}
    GROUP BY customer_id
),

final AS (
    SELECT
        -- Surrogate key
        {{ dbt_utils.surrogate_key(['c.customer_id']) }} as customer_key,

        -- Natural key
        c.customer_id,

        -- Attributes
        c.first_name,
        c.last_name,
        c.email,
        c.date_of_birth,
        c.age,
        c.gender,

        -- Location
        c.city,
        c.state,
        c.country,
        c.postal_code,

        -- Derived attributes
        COALESCE(o.total_orders, 0) as total_orders,
        COALESCE(o.lifetime_value, 0) as lifetime_value,
        o.first_order_date,
        o.last_order_date,
        o.avg_order_value,

        -- Segments
        CASE
            WHEN o.lifetime_value > 10000 THEN 'Diamond'
            WHEN o.lifetime_value > 5000 THEN 'Gold'
            WHEN o.lifetime_value > 1000 THEN 'Silver'
            ELSE 'Bronze'
        END as value_segment,

        -- Metadata
        c.is_active,
        c.created_at,
        c.updated_at,
        CURRENT_TIMESTAMP as dim_created_at,
        CURRENT_TIMESTAMP as dim_updated_at

    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
)

SELECT * FROM final
```

### **Gold Facts** (Fact Tables)
```sql
-- models/gold/facts/fact_orders.sql
{{
    config(
        materialized='incremental',
        unique_key='order_key',
        partition_by={'field': 'order_date', 'data_type': 'date'},
        cluster_by=['customer_key', 'product_key']
    )
}}

WITH orders AS (
    SELECT * FROM {{ ref('orders') }}
    {% if is_incremental() %}
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
    {% endif %}
),

final AS (
    SELECT
        -- Surrogate keys
        {{ dbt_utils.surrogate_key(['order_id']) }} as order_key,
        {{ dbt_utils.surrogate_key(['customer_id']) }} as customer_key,
        {{ dbt_utils.surrogate_key(['product_id']) }} as product_key,
        {{ dbt_utils.surrogate_key(['order_date']) }} as date_key,

        -- Degenerate dimensions
        order_id,
        order_status,
        payment_method,
        shipping_method,

        -- Measures
        quantity,
        unit_price,
        discount_amount,
        tax_amount,
        shipping_amount,
        quantity * unit_price as gross_amount,
        (quantity * unit_price) - discount_amount as net_amount,
        (quantity * unit_price) - discount_amount + tax_amount + shipping_amount as total_amount,

        -- Calculated measures
        CASE
            WHEN discount_amount > 0 THEN 1
            ELSE 0
        END as is_discounted,

        discount_amount / NULLIF(quantity * unit_price, 0) as discount_percentage,

        -- Date/time
        order_date,
        ship_date,
        deliver_date,
        DATE_DIFF(ship_date, order_date, DAY) as days_to_ship,
        DATE_DIFF(deliver_date, ship_date, DAY) as days_in_transit,

        -- Metadata
        created_at,
        updated_at,
        CURRENT_TIMESTAMP as fact_created_at

    FROM orders
)

SELECT * FROM final
```

## 🔧 Configuration

### **dbt_project.yml**
```yaml
name: 'silver_core'
version: '1.0.0'
config-version: 2

profile: 'silver_core'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["data"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

models:
  silver_core:
    staging:
      +materialized: view
      +tags: ['staging']
    silver:
      +materialized: table
      +tags: ['silver']
      +on_schema_change: sync_all_columns
      customers:
        +indexes:
          - columns: ['customer_id']
            unique: true
          - columns: ['email']
          - columns: ['created_at']

vars:
  start_date: '2020-01-01'
  environment: '{{ env_var("DBT_ENVIRONMENT", "dev") }}'
  enable_masking: '{{ env_var("ENABLE_PII_MASKING", "false") }}'

on-run-start:
  - "{{ log_dbt_run_started() }}"

on-run-end:
  - "{{ log_dbt_run_completed() }}"
```

### **profiles.yml**
```yaml
silver_core:
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5432
      user: "{{ env_var('DBT_USER', 'developer') }}"
      password: "{{ env_var('DBT_PASSWORD') }}"
      database: warehouse_dev
      schema: silver_dev
      threads: 4
      keepalives_idle: 0
      search_path: [silver_dev, bronze, public]

    staging:
      type: postgres
      host: warehouse-staging.internal
      port: 5432
      user: "{{ env_var('DBT_USER') }}"
      password: "{{ env_var('DBT_PASSWORD') }}"
      database: warehouse_staging
      schema: silver_staging
      threads: 8

    prod:
      type: postgres
      host: warehouse-prod.internal
      port: 5432
      user: "{{ env_var('DBT_USER') }}"
      password: "{{ env_var('DBT_PASSWORD') }}"
      database: warehouse_prod
      schema: silver
      threads: 16

  target: dev
```

## 🧪 Testing

### **Schema Tests**
```yaml
# models/silver/schema.yml
version: 2

models:
  - name: customers
    description: Clean customer data from source systems
    columns:
      - name: customer_id
        description: Unique customer identifier
        tests:
          - unique
          - not_null

      - name: email
        description: Customer email address
        tests:
          - unique
          - not_null
          - email_format

      - name: age
        tests:
          - not_null
          - accepted_values:
              values: [18, 19, 20] # Example range
              quote: false
          - range_check:
              min_value: 0
              max_value: 120

      - name: created_at
        tests:
          - not_null
          - date_is_past

    tests:
      - row_count_range:
          min_count: 1000
          max_count: 1000000
```

### **Custom Tests**
```sql
-- tests/generic/test_email_format.sql
{% test email_format(model, column_name) %}

WITH validation AS (
    SELECT
        {{ column_name }} as email
    FROM {{ model }}
    WHERE {{ column_name }} IS NOT NULL
        AND {{ column_name }} NOT LIKE '%@%.%'
)

SELECT COUNT(*) FROM validation

{% endtest %}
```

## 🚀 Development Workflow

### **1. Local Development**
```bash
# Set up environment
cd layer2-dbt-projects/silver-core
python -m venv venv
source venv/bin/activate
pip install dbt-postgres==1.7.0

# Install dependencies
dbt deps

# Test connection
dbt debug

# Run models
dbt run --select customers+  # Run customers and downstream
dbt run --models tag:daily    # Run daily models
dbt run --exclude tag:heavy   # Run all except heavy models

# Test models
dbt test --select customers
dbt test --select source:bronze

# Generate documentation
dbt docs generate
dbt docs serve --port 8080
```

### **2. Development in Docker**
```bash
# Build dbt runner image
docker build -t registry.localhost/analytics/dbt-runner:1.0.0 .

# Run dbt commands
docker run --rm \
  -v $(pwd):/dbt \
  -v ~/.dbt:/root/.dbt \
  -e DBT_PROFILES_DIR=/root/.dbt \
  registry.localhost/analytics/dbt-runner:1.0.0 \
  run --select customers
```

## 📊 Best Practices

### **DO's**
✅ Use ref() and source() functions for dependencies
✅ Write comprehensive tests for critical models
✅ Document all models and columns
✅ Use incremental models for large tables
✅ Version control everything
✅ Use consistent naming conventions
✅ Leverage macros for repeated logic

### **DON'Ts**
❌ Hard-code database or schema names
❌ Use SELECT * in production models
❌ Skip testing
❌ Ignore query performance
❌ Mix business logic across layers
❌ Create circular dependencies

## 🔍 Common Patterns

### **Incremental Pattern**
```sql
{{
    config(
        materialized='incremental',
        unique_key='id',
        on_schema_change='fail'
    )
}}

SELECT *
FROM source_table
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

### **SCD Type 2 Pattern**
```sql
-- snapshots/customers_snapshot.sql
{% snapshot customers_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='timestamp',
      updated_at='updated_at',
      invalidate_hard_deletes=True
    )
}}

SELECT * FROM {{ source('bronze', 'br_customers') }}

{% endsnapshot %}
```

### **Macro Pattern**
```sql
-- macros/calculate_age.sql
{% macro calculate_age(date_column) %}
    DATE_DIFF(CURRENT_DATE(), {{ date_column }}, YEAR)
{% endmacro %}
```

## 📚 Further Reading

### Child Pages
- **[dbt Architecture](dbt/architecture.md)** - Deep dive into dbt design
- **[Silver Layer Models](dbt/models/silver-layer.md)** - Business entity modeling
- **[Gold Layer Models](dbt/models/gold-layer.md)** - Dimensional modeling
- **[Testing Strategies](dbt/testing.md)** - Comprehensive testing guide
- **[Performance Optimization](dbt/performance.md)** - Query optimization

### External Resources
- [dbt Documentation](https://docs.getdbt.com/)
- [dbt Best Practices](https://docs.getdbt.com/guides/best-practices)
- [The Data Warehouse Toolkit](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/books/)

## 💡 Quick Commands

```bash
# Development
dbt run                          # Run all models
dbt test                         # Run all tests
dbt build                        # Run and test all models
dbt compile                      # Compile SQL without executing

# Selective execution
dbt run --select model_name      # Run specific model
dbt run --select +model_name     # Run model and upstream
dbt run --select model_name+     # Run model and downstream
dbt run --select @model_name     # Run model, upstream, and downstream

# Testing
dbt test --select model_name     # Test specific model
dbt test --select test_type:generic  # Run generic tests
dbt test --select test_type:singular # Run singular tests

# Documentation
dbt docs generate                # Generate documentation
dbt docs serve                   # Serve documentation locally

# Snapshots
dbt snapshot                     # Run all snapshots
dbt snapshot --select snapshot_name # Run specific snapshot

# Seeds
dbt seed                         # Load all seed files
dbt seed --select seed_name     # Load specific seed
```

---

*Ready to start building dbt models? Begin with the [Quick Start Tutorial](dbt/quick-start.md).*