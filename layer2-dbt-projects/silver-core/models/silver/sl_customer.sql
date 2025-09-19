with src as (select * from {{ source('bronze','br_customer') }})
select
  gen_random_uuid() as sl_customer_key,
  cast(customer_id as int) as customer_id,
  cast(store_id as int) as store_id,
  cast(first_name as varchar(45)) as first_name,
  cast(last_name as varchar(45)) as last_name,
  (cast(first_name as varchar(45)) || ' ' || cast(last_name as varchar(45))) as full_name,
  cast(email as varchar(50)) as email,
  cast(address_id as int) as address_id,
  cast(active as boolean) as is_active,
  cast(create_date as timestamp) as create_date,
  cast(last_update as timestamp) as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  true as sl_is_active,
  null::float as sl_data_quality_score
from src
