# Bronze → Silver → Gold Data Architecture

A comprehensive guide to our three-layer data architecture pattern, explaining how raw data transforms into business-ready analytics through progressive refinement.

## 🎯 Why This Pattern?

The Bronze → Silver → Gold pattern solves fundamental data engineering challenges:

1. **Source System Decoupling**: Bronze isolates source system changes
2. **Business Logic Centralization**: Silver contains reusable business rules
3. **Performance Optimization**: Gold provides query-optimized structures
4. **Audit Trail**: Complete lineage from source to analytics
5. **Parallel Development**: Teams can work on different layers simultaneously

## 📊 Layer Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                          DATA JOURNEY                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Source Systems          Bronze              Silver           Gold │
│  ┌──────────┐           ┌──────────┐       ┌──────────┐    ┌──────────┐
│  │PostgreSQL│ ─extract─▶│  br_     │──────▶│ Cleaned  │───▶│  Facts   │
│  │SQL Server│           │  tables  │transform Business │    │   &      │
│  │   APIs   │           │  (raw)   │       │ Entities │    │Dimensions│
│  │  Files   │           └──────────┘       └──────────┘    └──────────┘
│  └──────────┘                                                      │
│                                                                    │
│     Variety              Uniformity         Consistency    Analytics│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## 🥉 Bronze Layer: Raw Data Ingestion

### **Purpose**
Faithful representation of source system data with minimal transformation.

### **Characteristics**
- **Schema**: Matches source system exactly
- **Naming**: Prefixed with `br_` (e.g., `br_customers`, `br_orders`)
- **Updates**: Append-only or full refresh
- **Processing**: Type casting and timestamp standardization only
- **Storage**: Typically in `bronze` schema

### **Implementation Pattern**

```python
# Bronze Datakit Example (datakit_bronze/extract.py)
class BronzeExtractor:
    """Extract raw data from source systems."""

    def extract_table(self, table_name: str):
        # 1. Connect to source
        source_conn = self.get_source_connection()

        # 2. Read raw data
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, source_conn)

        # 3. Add metadata
        df['_bronze_loaded_at'] = datetime.now()
        df['_bronze_source'] = self.source_name

        # 4. Write to bronze
        df.to_sql(
            name=f"br_{table_name}",
            con=self.warehouse_conn,
            schema="bronze",
            if_exists="append",
            index=False
        )
```

### **Bronze Best Practices**

1. **No Business Logic**: Just extract and load
2. **Preserve Everything**: Including "bad" data for debugging
3. **Add Metadata**: Capture load time, source, batch ID
4. **Handle Schema Changes**: Use schema evolution strategies
5. **Partition Large Tables**: By date or other logical boundaries

### **Example Bronze Tables**

```sql
-- bronze.br_customers (raw from source)
CREATE TABLE bronze.br_customers (
    customer_id VARCHAR(50),      -- Keep source types
    cust_name VARCHAR(255),        -- Don't rename fields
    created_date VARCHAR(50),      -- Don't parse dates
    status_cd VARCHAR(10),         -- Keep cryptic codes
    _bronze_loaded_at TIMESTAMP,   -- Add metadata
    _bronze_source VARCHAR(50),
    _bronze_batch_id VARCHAR(50)
);

-- bronze.br_orders (preserves source structure)
CREATE TABLE bronze.br_orders (
    ord_id VARCHAR(50),
    cust_id VARCHAR(50),           -- Inconsistent naming preserved
    order_dt VARCHAR(50),
    amt DECIMAL(10,2),
    _bronze_loaded_at TIMESTAMP,
    _bronze_source VARCHAR(50)
);
```

## 🥈 Silver Layer: Business Entities

### **Purpose**
Clean, standardized business entities with consistent naming and types.

### **Characteristics**
- **Schema**: Normalized business model
- **Naming**: Business-friendly names
- **Updates**: Incremental with SCD handling
- **Processing**: Cleaning, validation, standardization
- **Storage**: Schema named after business domain

### **Implementation Pattern**

```sql
-- Silver dbt Model (models/silver/customers.sql)
WITH source AS (
    SELECT * FROM {{ ref('br_customers') }}
),

cleaned AS (
    SELECT
        -- Standardize IDs
        CAST(customer_id AS INTEGER) as customer_id,

        -- Clean names
        INITCAP(TRIM(cust_name)) as customer_name,

        -- Parse dates
        TO_DATE(created_date, 'YYYY-MM-DD') as created_date,

        -- Decode statuses
        CASE status_cd
            WHEN 'A' THEN 'Active'
            WHEN 'I' THEN 'Inactive'
            WHEN 'S' THEN 'Suspended'
            ELSE 'Unknown'
        END as status,

        -- Add business fields
        CASE
            WHEN created_date < '2020-01-01' THEN 'Legacy'
            ELSE 'Modern'
        END as customer_cohort,

        -- Metadata
        _bronze_loaded_at as bronze_loaded_at,
        CURRENT_TIMESTAMP as silver_processed_at

    FROM source
    WHERE customer_id IS NOT NULL  -- Remove bad records
)

SELECT * FROM cleaned
```

### **Silver Best Practices**

1. **Consistent Naming**: Use business terminology
2. **Data Quality**: Validate and clean data
3. **Handle Changes**: Implement SCD Type 2 where needed
4. **Business Logic**: Apply reusable business rules
5. **Documentation**: Document all transformations

### **Example Silver Tables**

```sql
-- pagila_silver.customers (cleaned and standardized)
CREATE TABLE pagila_silver.customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    address_line_1 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    postal_code VARCHAR(20),
    country VARCHAR(100),
    created_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    customer_cohort VARCHAR(20),
    is_active BOOLEAN,
    silver_processed_at TIMESTAMP
);

-- pagila_silver.orders (business-ready)
CREATE TABLE pagila_silver.orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    order_amount DECIMAL(10,2) NOT NULL,
    order_status VARCHAR(20),
    payment_method VARCHAR(50),
    shipping_address_id INTEGER,
    is_completed BOOLEAN,
    days_to_fulfill INTEGER,
    silver_processed_at TIMESTAMP
);
```

## 🥇 Gold Layer: Analytics-Ready

### **Purpose**
Optimized dimensional models for reporting and analytics.

### **Characteristics**
- **Schema**: Star/snowflake schemas
- **Naming**: Fact and dimension prefixes
- **Updates**: Typically full refresh
- **Processing**: Aggregations, calculations, joins
- **Storage**: Separate schemas per domain

### **Implementation Pattern**

```sql
-- Gold dbt Model - Dimension (models/gold/dim_customer.sql)
WITH customer_base AS (
    SELECT * FROM {{ ref('customers') }}  -- Silver layer
),

customer_metrics AS (
    SELECT
        customer_id,
        COUNT(*) as total_orders,
        SUM(order_amount) as lifetime_value,
        MAX(order_date) as last_order_date
    FROM {{ ref('orders') }}
    GROUP BY customer_id
),

final AS (
    SELECT
        -- Dimension key
        {{ dbt_utils.surrogate_key(['c.customer_id']) }} as customer_key,

        -- Natural key
        c.customer_id,

        -- Attributes
        c.customer_name,
        c.email,
        c.city,
        c.state,
        c.country,
        c.status,
        c.customer_cohort,

        -- Derived attributes
        COALESCE(m.total_orders, 0) as total_orders,
        COALESCE(m.lifetime_value, 0) as lifetime_value,
        m.last_order_date,

        -- Segmentation
        CASE
            WHEN m.lifetime_value > 10000 THEN 'High Value'
            WHEN m.lifetime_value > 1000 THEN 'Medium Value'
            ELSE 'Low Value'
        END as value_segment,

        -- Metadata
        CURRENT_TIMESTAMP as gold_processed_at

    FROM customer_base c
    LEFT JOIN customer_metrics m ON c.customer_id = m.customer_id
)

SELECT * FROM final
```

```sql
-- Gold dbt Model - Fact (models/gold/fact_orders.sql)
WITH orders AS (
    SELECT * FROM {{ ref('orders') }}  -- Silver layer
),

final AS (
    SELECT
        -- Fact key
        {{ dbt_utils.surrogate_key(['order_id']) }} as order_key,

        -- Dimension keys
        {{ dbt_utils.surrogate_key(['customer_id']) }} as customer_key,
        {{ dbt_utils.surrogate_key(['order_date']) }} as date_key,
        {{ dbt_utils.surrogate_key(['product_id']) }} as product_key,

        -- Degenerate dimensions
        order_id,
        order_status,
        payment_method,

        -- Measures
        order_amount,
        order_quantity,
        discount_amount,
        tax_amount,
        shipping_amount,
        order_amount - discount_amount + tax_amount + shipping_amount as total_amount,

        -- Calculated measures
        days_to_fulfill,
        CASE
            WHEN days_to_fulfill <= 2 THEN 1
            ELSE 0
        END as is_fast_delivery,

        -- Metadata
        CURRENT_TIMESTAMP as gold_processed_at

    FROM orders
)

SELECT * FROM final
```

### **Gold Best Practices**

1. **Dimensional Modeling**: Follow Kimball methodology
2. **Conformed Dimensions**: Share across fact tables
3. **Pre-Calculate**: Complex metrics and KPIs
4. **Optimize for Queries**: Add indexes and partitions
5. **Business Names**: Use terms business users understand

### **Example Gold Tables**

```sql
-- gold_mart.dim_customer (dimension table)
CREATE TABLE gold_mart.dim_customer (
    customer_key VARCHAR(32) PRIMARY KEY,  -- Surrogate key
    customer_id INTEGER NOT NULL,          -- Natural key
    customer_name VARCHAR(255),
    email VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(100),
    value_segment VARCHAR(20),
    total_orders INTEGER,
    lifetime_value DECIMAL(12,2),
    first_order_date DATE,
    last_order_date DATE,
    is_active BOOLEAN,
    gold_processed_at TIMESTAMP
);

-- gold_rental.fact_rental (fact table)
CREATE TABLE gold_rental.fact_rental (
    rental_key VARCHAR(32) PRIMARY KEY,
    customer_key VARCHAR(32),
    film_key VARCHAR(32),
    staff_key VARCHAR(32),
    date_key VARCHAR(32),
    rental_id INTEGER,
    rental_duration_days INTEGER,
    rental_amount DECIMAL(10,2),
    late_fee_amount DECIMAL(10,2),
    total_amount DECIMAL(10,2),
    is_returned BOOLEAN,
    is_late_return BOOLEAN,
    gold_processed_at TIMESTAMP
);
```

## 🔄 Data Flow Examples

### **Example 1: Customer Data Journey**

```
1. Bronze: Raw Extract
   br_customers:
   - cust_id: "00123"
   - nm: "john doe"
   - stat: "A"
   - crtd: "2023-01-15 08:30:00"

2. Silver: Cleaned Entity
   customers:
   - customer_id: 123
   - customer_name: "John Doe"
   - status: "Active"
   - created_date: 2023-01-15

3. Gold: Dimension
   dim_customer:
   - customer_key: "abc123..."
   - customer_name: "John Doe"
   - value_segment: "High Value"
   - lifetime_value: 15000.00
```

### **Example 2: Order Processing Pipeline**

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Source  │────▶│  Bronze  │────▶│  Silver  │────▶│   Gold   │
│          │     │          │     │          │     │          │
│ OrderSys │     │ br_orders│     │  orders  │     │fact_order│
│          │     │ br_items │     │order_items│    │ +metrics │
│          │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
   OLTP            Staging         Cleaned          Analytics
```

## 🛠️ Implementation Technologies

### **Bronze Layer Tools**
- **Datakits**: Python-based extractors
- **Apache Spark**: Large-scale data ingestion
- **Airbyte/Fivetran**: SaaS connectors
- **Custom Scripts**: Legacy system integration

### **Silver Layer Tools**
- **dbt**: SQL-based transformations
- **Apache Spark**: Complex processing
- **Python**: Advanced cleaning logic
- **Great Expectations**: Data quality

### **Gold Layer Tools**
- **dbt**: Dimensional modeling
- **Apache Spark**: Large aggregations
- **Materialized Views**: Performance optimization
- **BI Tools**: Direct connectivity

## 📋 Layer Comparison

| Aspect | Bronze | Silver | Gold |
|--------|--------|--------|------|
| **Purpose** | Staging | Business Logic | Analytics |
| **Schema** | Matches Source | Normalized | Dimensional |
| **Updates** | Append/Replace | Incremental | Full Refresh |
| **Data Quality** | As-is | Validated | Guaranteed |
| **Naming** | Source Names | Business Terms | Analytics Terms |
| **Performance** | Not Optimized | Balanced | Query Optimized |
| **Users** | Data Engineers | Data Engineers | Analysts |

## 🎯 Benefits of This Architecture

### **For Data Engineers**
- Clear separation of responsibilities
- Easier debugging with preserved raw data
- Parallel development across layers
- Reusable transformation logic

### **For Data Analysts**
- Consistent, clean data in Gold layer
- Pre-calculated metrics
- Optimized query performance
- Business-friendly naming

### **For the Organization**
- Audit trail from source to reports
- Reduced time to insights
- Lower maintenance costs
- Scalable architecture

## 🚨 Common Pitfalls and Solutions

### **Pitfall 1: Business Logic in Bronze**
**Problem**: Adding transformations in Bronze layer
**Solution**: Keep Bronze as raw as possible; move logic to Silver

### **Pitfall 2: Skipping Silver**
**Problem**: Going directly from Bronze to Gold
**Solution**: Silver provides crucial reusable business logic

### **Pitfall 3: Over-Aggregating Gold**
**Problem**: Too much pre-aggregation limits flexibility
**Solution**: Balance between performance and flexibility

### **Pitfall 4: Inconsistent Naming**
**Problem**: Mixed conventions across layers
**Solution**: Establish and enforce naming standards

## 📊 Monitoring and Quality

### **Key Metrics by Layer**

**Bronze Monitoring**
- Row counts match source
- Load completion times
- Schema drift detection
- Failed extracts

**Silver Monitoring**
- Data quality scores
- Transformation success rates
- Business rule violations
- Processing times

**Gold Monitoring**
- Query performance
- Refresh frequencies
- User adoption metrics
- Report accuracy

## 🔗 Related Documentation

- **[Creating Datakits](creating-datakits.md)** - Build Bronze layer extractors
- **[dbt Development](dbt-development.md)** - Silver and Gold transformations
- **[Architecture Overview](architecture-overview.md)** - System architecture
- **[Testing Strategies](testing-strategies.md)** - Layer-specific testing

## 💡 Quick Reference

### **Bronze SQL Pattern**
```sql
CREATE TABLE bronze.br_{source_table} AS
SELECT
    *,
    CURRENT_TIMESTAMP as _bronze_loaded_at,
    'source_system' as _bronze_source
FROM source.{source_table};
```

### **Silver dbt Pattern**
```sql
-- models/silver/{entity}.sql
WITH source AS (
    SELECT * FROM {{ ref('br_' ~ entity) }}
),
cleaned AS (
    -- Apply business rules
    -- Standardize fields
    -- Add calculations
)
SELECT * FROM cleaned
```

### **Gold dbt Pattern**
```sql
-- models/gold/fact_{process}.sql
WITH base AS (
    SELECT * FROM {{ ref('silver_entity') }}
),
metrics AS (
    -- Calculate measures
    -- Add dimension keys
)
SELECT * FROM metrics
```

---

*Next: Learn about [Developer Workflows](developer-workflows.md) for building pipelines using this pattern.*