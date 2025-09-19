with src as (select * from {{ source('bronze','br_store') }})
select
  gen_random_uuid() as sl_store_key,
  cast(store_id as int) as store_id,
  cast(manager_staff_id as int) as manager_staff_id,
  cast(address_id as int) as address_id,
  now() as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  null::uuid as sl_source_bronze_key,
  true as sl_is_active,
  null::float as sl_data_quality_score,
  0::float as sl_total_revenue,
  0::int as sl_total_customers,
  0::int as sl_total_rentals,
  null::float as sl_avg_rental_rate
from src
