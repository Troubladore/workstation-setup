# Silver Layer Models in dbt

A comprehensive guide to building Silver layer models that transform raw Bronze data into clean, standardized business entities.

## 🎯 Purpose of Silver Layer

The Silver layer serves as the foundation for all analytics by providing:
- **Clean, validated data** with business rules applied
- **Standardized schemas** across different source systems
- **Business entities** that map to real-world concepts
- **Historical tracking** through SCD Type 2 patterns
- **Reusable datasets** for multiple downstream consumers

## 📐 Silver Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Bronze Layer (Raw)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ br_users │  │br_orders │  │br_products│  │br_inventory│ │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘  │
└────────┼─────────────┼─────────────┼─────────────┼────────┘
         │             │             │             │
    ┌────▼─────────────▼─────────────▼─────────────▼────┐
    │               Staging Models (Views)                │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
    │  │stg_users │  │stg_orders│  │stg_products│       │
    │  └─────┬────┘  └─────┬────┘  └─────┬────┘        │
    └────────┼─────────────┼─────────────┼──────────────┘
             │             │             │
    ┌────────▼─────────────▼─────────────▼──────────────┐
    │           Silver Models (Tables/Incremental)        │
    │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
    │  │customers │  │  orders  │  │ products │        │
    │  └──────────┘  └──────────┘  └──────────┘        │
    └────────────────────────────────────────────────────┘
```

## 🏗️ Building Silver Models

### **Step 1: Create Staging Models**

Staging models are lightweight views that handle type casting and basic cleaning:

```sql
-- models/staging/stg_customers.sql
{{
    config(
        materialized='view',
        tags=['staging']
    )
}}

WITH source AS (
    -- Reference the Bronze table
    SELECT * FROM {{ source('bronze', 'br_customers') }}
    WHERE _bronze_loaded_at >= '{{ var("start_date") }}'
),

-- Type casting and basic cleaning
typed AS (
    SELECT
        -- IDs - Cast to appropriate types
        CAST(customer_id AS INTEGER) as customer_id,
        CAST(account_id AS STRING) as account_id,
        {{ safe_cast('external_id', 'STRING') }} as external_id,

        -- Names - Trim and standardize
        {{ standardize_name('first_name') }} as first_name,
        {{ standardize_name('last_name') }} as last_name,
        {{ standardize_name('company_name') }} as company_name,

        -- Contact - Clean and validate
        {{ clean_email('email_address') }} as email,
        {{ clean_phone_number('phone') }} as phone,
        {{ clean_phone_number('mobile') }} as mobile,

        -- Address - Parse and standardize
        {{ parse_address('address_line_1') }} as address_line_1,
        {{ parse_address('address_line_2') }} as address_line_2,
        TRIM(UPPER(city)) as city,
        {{ standardize_state_code('state') }} as state_code,
        {{ standardize_country_code('country') }} as country_code,
        {{ validate_postal_code('postal_code', 'country') }} as postal_code,

        -- Dates - Parse various formats
        {{ parse_date('date_of_birth') }} as date_of_birth,
        {{ parse_timestamp('created_date') }} as created_at,
        {{ parse_timestamp('modified_date') }} as updated_at,
        {{ parse_timestamp('last_login_date') }} as last_login_at,

        -- Status fields
        {{ decode_status('status_code') }} as status,
        {{ to_boolean('is_active_flag') }} as is_active,
        {{ to_boolean('is_verified_flag') }} as is_verified,
        {{ to_boolean('has_opted_in_flag') }} as has_opted_in_marketing,

        -- Metadata from Bronze
        _bronze_loaded_at,
        _bronze_source,
        _bronze_batch_id

    FROM source
),

-- Data quality filters
quality_filtered AS (
    SELECT *
    FROM typed
    WHERE
        -- Remove test data
        email NOT LIKE '%@test.%'
        AND email NOT LIKE '%@example.%'

        -- Remove invalid records
        AND customer_id IS NOT NULL
        AND customer_id > 0

        -- Remove duplicates by keeping latest
        AND ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY updated_at DESC, _bronze_loaded_at DESC
        ) = 1
)

SELECT * FROM quality_filtered
```

### **Step 2: Create Silver Business Entity Models**

Silver models apply business logic and create reusable entities:

```sql
-- models/silver/customers.sql
{{
    config(
        materialized='incremental',
        unique_key='customer_id',
        on_schema_change='sync_all_columns',
        tags=['silver', 'customers', 'daily'],

        -- Performance optimizations
        cluster_by=['created_at', 'customer_id'],

        -- Incremental strategy
        incremental_strategy='merge',
        merge_exclude_columns=['created_at'],

        -- Data quality
        persist_docs={"relation": true, "columns": true}
    )
}}

WITH staged AS (
    SELECT * FROM {{ ref('stg_customers') }}
    {% if is_incremental() %}
        -- Only process new or updated records
        WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
        OR _bronze_loaded_at > (SELECT MAX(_bronze_loaded_at) FROM {{ this }})
    {% endif %}
),

-- Enrich with derived fields
enriched AS (
    SELECT
        -- Primary identifiers
        customer_id,
        account_id,
        external_id,

        -- Personal information
        first_name,
        last_name,
        CONCAT(first_name, ' ', last_name) as full_name,
        company_name,

        -- Contact information
        email,
        phone,
        mobile,
        COALESCE(mobile, phone) as primary_phone,

        -- Address
        address_line_1,
        address_line_2,
        city,
        state_code,
        country_code,
        postal_code,
        {{ build_full_address(
            'address_line_1',
            'address_line_2',
            'city',
            'state_code',
            'postal_code',
            'country_code'
        ) }} as full_address,

        -- Demographics
        date_of_birth,
        {{ calculate_age('date_of_birth') }} as age,
        {{ assign_age_group('date_of_birth') }} as age_group,
        {{ calculate_lifetime_days('created_at') }} as customer_lifetime_days,

        -- Status and flags
        status,
        is_active,
        is_verified,
        has_opted_in_marketing,

        -- Derived status
        CASE
            WHEN status = 'Active' AND is_verified THEN 'Verified Active'
            WHEN status = 'Active' AND NOT is_verified THEN 'Unverified Active'
            WHEN status = 'Suspended' THEN 'Suspended'
            WHEN status = 'Closed' THEN 'Closed'
            ELSE 'Unknown'
        END as customer_status_detailed,

        -- Segmentation
        {{ assign_customer_segment(
            'created_at',
            'last_login_at',
            'is_verified'
        ) }} as customer_segment,

        -- Activity tracking
        created_at,
        updated_at,
        last_login_at,
        {{ calculate_days_since('last_login_at') }} as days_since_last_login,

        -- Data quality scores
        {{ calculate_completeness_score([
            'first_name',
            'last_name',
            'email',
            'phone',
            'address_line_1',
            'city',
            'state_code',
            'postal_code'
        ]) }} as data_completeness_score,

        -- Processing metadata
        CURRENT_TIMESTAMP() as silver_processed_at,
        '{{ invocation_id }}' as dbt_invocation_id,
        _bronze_loaded_at as bronze_loaded_at,
        _bronze_source as source_system

    FROM staged
),

-- Apply business rules
business_rules_applied AS (
    SELECT
        *,

        -- Customer lifecycle stage
        CASE
            WHEN days_since_last_login IS NULL THEN 'Never Active'
            WHEN days_since_last_login <= 30 THEN 'Active'
            WHEN days_since_last_login <= 90 THEN 'At Risk'
            WHEN days_since_last_login <= 365 THEN 'Dormant'
            ELSE 'Churned'
        END as lifecycle_stage,

        -- Risk indicators
        CASE
            WHEN NOT is_verified AND customer_lifetime_days > 30 THEN TRUE
            WHEN data_completeness_score < 0.5 THEN TRUE
            ELSE FALSE
        END as is_high_risk,

        -- Marketing eligibility
        CASE
            WHEN has_opted_in_marketing
                AND is_verified
                AND email IS NOT NULL
                AND status = 'Active'
            THEN TRUE
            ELSE FALSE
        END as is_marketing_eligible

    FROM enriched
),

-- Add data quality indicators
final AS (
    SELECT
        *,

        -- Data quality flags
        CASE
            WHEN email IS NULL THEN FALSE
            WHEN {{ is_valid_email('email') }} THEN TRUE
            ELSE FALSE
        END as has_valid_email,

        CASE
            WHEN primary_phone IS NULL THEN FALSE
            WHEN {{ is_valid_phone('primary_phone') }} THEN TRUE
            ELSE FALSE
        END as has_valid_phone,

        CASE
            WHEN postal_code IS NULL THEN FALSE
            WHEN {{ is_valid_postal_code('postal_code', 'country_code') }} THEN TRUE
            ELSE FALSE
        END as has_valid_address

    FROM business_rules_applied
)

SELECT * FROM final
```

### **Step 3: Create Complex Silver Models with Joins**

```sql
-- models/silver/customer_profiles.sql
{{
    config(
        materialized='table',
        tags=['silver', 'customer_profiles', 'daily']
    )
}}

WITH customers AS (
    SELECT * FROM {{ ref('customers') }}
),

orders AS (
    SELECT
        customer_id,
        COUNT(*) as total_orders,
        SUM(order_amount) as total_spent,
        AVG(order_amount) as avg_order_value,
        MAX(order_amount) as max_order_value,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date,
        COUNT(DISTINCT product_category) as categories_purchased,
        COUNT(DISTINCT DATE_TRUNC('month', order_date)) as active_months
    FROM {{ ref('orders') }}
    WHERE order_status = 'Completed'
    GROUP BY customer_id
),

support_tickets AS (
    SELECT
        customer_id,
        COUNT(*) as total_tickets,
        COUNT(CASE WHEN priority = 'High' THEN 1 END) as high_priority_tickets,
        AVG(resolution_time_hours) as avg_resolution_time,
        MAX(created_date) as last_ticket_date
    FROM {{ ref('support_tickets') }}
    GROUP BY customer_id
),

final AS (
    SELECT
        -- Customer base information
        c.customer_id,
        c.full_name,
        c.email,
        c.customer_segment,
        c.lifecycle_stage,
        c.customer_lifetime_days,

        -- Order metrics
        COALESCE(o.total_orders, 0) as total_orders,
        COALESCE(o.total_spent, 0) as total_spent,
        COALESCE(o.avg_order_value, 0) as avg_order_value,
        COALESCE(o.max_order_value, 0) as max_order_value,
        o.first_order_date,
        o.last_order_date,
        COALESCE(o.categories_purchased, 0) as categories_purchased,
        COALESCE(o.active_months, 0) as active_months,

        -- Calculate derived metrics
        CASE
            WHEN o.total_orders > 0 THEN
                o.total_spent / NULLIF(c.customer_lifetime_days, 0)
            ELSE 0
        END as daily_average_value,

        CASE
            WHEN o.active_months > 0 THEN
                o.total_orders::FLOAT / o.active_months
            ELSE 0
        END as orders_per_active_month,

        -- Support metrics
        COALESCE(s.total_tickets, 0) as total_support_tickets,
        COALESCE(s.high_priority_tickets, 0) as high_priority_tickets,
        s.avg_resolution_time,
        s.last_ticket_date,

        -- Customer scores
        {{ calculate_clv_score(
            'o.total_spent',
            'o.total_orders',
            'o.last_order_date',
            'c.customer_lifetime_days'
        ) }} as clv_score,

        {{ calculate_engagement_score(
            'o.active_months',
            'c.days_since_last_login',
            'o.categories_purchased'
        ) }} as engagement_score,

        -- Classification
        CASE
            WHEN o.total_spent > 10000 THEN 'VIP'
            WHEN o.total_spent > 5000 THEN 'High Value'
            WHEN o.total_spent > 1000 THEN 'Regular'
            WHEN o.total_orders > 0 THEN 'Low Value'
            ELSE 'Prospect'
        END as customer_tier,

        -- Metadata
        CURRENT_TIMESTAMP() as profile_updated_at

    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    LEFT JOIN support_tickets s ON c.customer_id = s.customer_id
)

SELECT * FROM final
```

## 🔄 Incremental Processing Strategies

### **Strategy 1: Timestamp-Based Incremental**

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns'
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('stg_orders') }}

    {% if is_incremental() %}
        -- Look back 2 days for late-arriving data
        WHERE updated_at >= (
            SELECT DATE_SUB(MAX(updated_at), INTERVAL 2 DAY)
            FROM {{ this }}
        )
    {% endif %}
),

-- Processing logic here
...
```

### **Strategy 2: Batch ID-Based Incremental**

```sql
{{
    config(
        materialized='incremental',
        unique_key='record_id'
    )
}}

WITH source AS (
    SELECT * FROM {{ source('bronze', 'br_transactions') }}

    {% if is_incremental() %}
        WHERE _bronze_batch_id > (
            SELECT MAX(_bronze_batch_id)
            FROM {{ this }}
        )
    {% endif %}
),

-- Processing logic here
...
```

### **Strategy 3: Delete + Insert for Partitions**

```sql
{{
    config(
        materialized='incremental',
        partition_by={
            'field': 'transaction_date',
            'data_type': 'date'
        },
        incremental_strategy='insert_overwrite'
    )
}}

WITH source AS (
    SELECT * FROM {{ ref('stg_transactions') }}

    {% if is_incremental() %}
        -- Reprocess last 3 days of partitions
        WHERE transaction_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
    {% endif %}
),

-- Processing logic here
...
```

## 🧪 Testing Silver Models

### **Data Quality Tests**

```yaml
# models/silver/schema.yml
version: 2

models:
  - name: customers
    description: Clean, standardized customer data

    # Table-level tests
    tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1000
          max_value: 10000000

      - dbt_expectations.expect_table_column_count_to_equal:
          value: 25

      - freshness_check:
          date_column: silver_processed_at
          threshold_hours: 6

    columns:
      - name: customer_id
        description: Unique customer identifier
        tests:
          - unique
          - not_null
          - dbt_expectations.expect_column_values_to_be_of_type:
              column_type: integer

      - name: email
        description: Customer email address
        tests:
          - not_null
          - unique:
              where: "is_active = true"
          - email_format
          - no_test_emails

      - name: age
        description: Customer age in years
        tests:
          - not_null:
              where: "date_of_birth is not null"
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0
              max_value: 120
              row_condition: "date_of_birth is not null"

      - name: customer_segment
        tests:
          - accepted_values:
              values: ['New', 'Active', 'VIP', 'At Risk', 'Churned']
          - not_null

      - name: data_completeness_score
        tests:
          - dbt_expectations.expect_column_values_to_be_between:
              min_value: 0.0
              max_value: 1.0
```

### **Custom Silver Layer Tests**

```sql
-- tests/silver/test_no_orphaned_orders.sql
-- Ensure all orders have valid customers

SELECT
    o.order_id,
    o.customer_id
FROM {{ ref('orders') }} o
LEFT JOIN {{ ref('customers') }} c
    ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL
```

```sql
-- tests/silver/test_customer_lifecycle_consistency.sql
-- Ensure lifecycle stages are consistent with activity

WITH validation AS (
    SELECT
        customer_id,
        lifecycle_stage,
        days_since_last_login,
        CASE
            WHEN lifecycle_stage = 'Active'
                AND days_since_last_login > 30
            THEN 'Inconsistent: marked Active but inactive > 30 days'

            WHEN lifecycle_stage = 'Churned'
                AND days_since_last_login < 365
            THEN 'Inconsistent: marked Churned but active < 365 days'

            ELSE 'Consistent'
        END as consistency_check
    FROM {{ ref('customers') }}
)

SELECT *
FROM validation
WHERE consistency_check != 'Consistent'
```

## 📊 Silver Layer Macros

### **Data Standardization Macros**

```sql
-- macros/standardize_name.sql
{% macro standardize_name(column_name) %}
    CASE
        WHEN {{ column_name }} IS NULL THEN NULL
        WHEN TRIM({{ column_name }}) = '' THEN NULL
        ELSE INITCAP(
            LOWER(
                REGEXP_REPLACE(
                    TRIM({{ column_name }}),
                    '[^a-zA-Z\s\-\']',
                    '',
                    'g'
                )
            )
        )
    END
{% endmacro %}
```

```sql
-- macros/clean_email.sql
{% macro clean_email(column_name) %}
    CASE
        WHEN {{ column_name }} IS NULL THEN NULL
        WHEN {{ column_name }} NOT LIKE '%@%' THEN NULL
        ELSE LOWER(TRIM({{ column_name }}))
    END
{% endmacro %}
```

```sql
-- macros/calculate_completeness_score.sql
{% macro calculate_completeness_score(columns) %}
    (
        {% for column in columns %}
            CASE WHEN {{ column }} IS NOT NULL THEN 1.0 ELSE 0.0 END
            {%- if not loop.last %} + {% endif %}
        {% endfor %}
    ) / {{ columns | length }}
{% endmacro %}
```

### **Business Logic Macros**

```sql
-- macros/assign_customer_segment.sql
{% macro assign_customer_segment(created_date, last_activity_date, is_verified) %}
    CASE
        WHEN DATE_DIFF(CURRENT_DATE(), {{ created_date }}, DAY) <= 30
            THEN 'New'

        WHEN {{ last_activity_date }} IS NULL
            THEN 'Never Active'

        WHEN DATE_DIFF(CURRENT_DATE(), {{ last_activity_date }}, DAY) <= 30
            AND {{ is_verified }} = true
            THEN 'Active'

        WHEN DATE_DIFF(CURRENT_DATE(), {{ last_activity_date }}, DAY) <= 90
            THEN 'At Risk'

        WHEN DATE_DIFF(CURRENT_DATE(), {{ last_activity_date }}, DAY) <= 365
            THEN 'Dormant'

        ELSE 'Churned'
    END
{% endmacro %}
```

## 🎯 Best Practices for Silver Models

### **1. Consistent Naming Conventions**

```sql
-- Good: Clear, consistent naming
customers              -- Entity name, plural
customer_profiles      -- Entity + descriptor
customer_order_summary -- Entity + entity + descriptor

-- Bad: Inconsistent naming
cust                  -- Abbreviated
CustomerData          -- Mixed case
customer_info_v2      -- Versioning in name
```

### **2. Modular Design**

```sql
-- Build reusable intermediate models
models/
├── staging/
│   ├── stg_customers.sql       -- Type casting
│   └── stg_orders.sql
├── intermediate/
│   ├── int_customer_orders.sql  -- Join logic
│   └── int_customer_metrics.sql -- Calculations
└── silver/
    ├── customers.sql            -- Final entity
    └── customer_profiles.sql   -- Enriched entity
```

### **3. Documentation**

```yaml
# Always document models comprehensively
models:
  - name: customers
    description: |
      This model contains cleaned and standardized customer data from all source systems.
      It serves as the single source of truth for customer information across the organization.

      **Update Frequency**: Daily at 2 AM UTC
      **Source Systems**: Salesforce, Legacy CRM, E-commerce Platform
      **Business Owner**: Customer Success Team

    columns:
      - name: customer_id
        description: |
          Unique identifier for each customer. This is the primary key and should be used
          for all joins to customer data.
        meta:
          data_type: integer
          business_key: true
          pii: false
```

### **4. Performance Optimization**

```sql
{{
    config(
        -- Choose appropriate materialization
        materialized='incremental' if target.name == 'prod' else 'table',

        -- Add clustering for common query patterns
        cluster_by=['created_date', 'customer_id'],

        -- Partition large tables
        partition_by={
            'field': 'created_date',
            'data_type': 'date',
            'granularity': 'month'
        } if target.name == 'prod' else none,

        -- Set appropriate distribution
        dist='customer_id',

        -- Add indexes for join keys
        indexes=[
            {'columns': ['customer_id'], 'unique': true},
            {'columns': ['email'], 'unique': true},
            {'columns': ['created_date'], 'type': 'btree'}
        ]
    )
}}
```

## 🔍 Monitoring Silver Layer Health

### **Key Metrics to Track**

```sql
-- models/metrics/silver_layer_health.sql
WITH model_metrics AS (
    SELECT
        'customers' as model_name,
        COUNT(*) as row_count,
        COUNT(DISTINCT customer_id) as unique_count,
        MAX(silver_processed_at) as last_updated,
        AVG(data_completeness_score) as avg_completeness
    FROM {{ ref('customers') }}

    UNION ALL

    SELECT
        'orders' as model_name,
        COUNT(*) as row_count,
        COUNT(DISTINCT order_id) as unique_count,
        MAX(silver_processed_at) as last_updated,
        NULL as avg_completeness
    FROM {{ ref('orders') }}
)

SELECT
    model_name,
    row_count,
    unique_count,
    last_updated,
    DATE_DIFF(CURRENT_TIMESTAMP(), last_updated, HOUR) as hours_since_update,
    avg_completeness,
    CASE
        WHEN DATE_DIFF(CURRENT_TIMESTAMP(), last_updated, HOUR) > 24
            THEN 'STALE'
        ELSE 'FRESH'
    END as freshness_status
FROM model_metrics
ORDER BY model_name
```

## 🔗 Related Documentation

- [dbt Development Guide](../../dbt-development.md) - Parent documentation
- [Gold Layer Models](gold-layer.md) - Next transformation layer
- [Incremental Models](incremental.md) - Deep dive into incremental strategies
- [Testing Strategies](../testing.md) - Comprehensive testing guide
- [Performance Optimization](../performance.md) - Query optimization techniques

---

*[← Back to dbt Development](../../dbt-development.md) | [Next: Gold Layer Models →](gold-layer.md)*