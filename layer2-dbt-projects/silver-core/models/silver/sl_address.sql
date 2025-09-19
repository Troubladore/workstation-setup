with src as (select * from {{ source('bronze','br_address') }})
select
  gen_random_uuid() as sl_address_key,
  cast(address_id as int) as address_id,
  cast(address as varchar(50)) as address,
  cast(address2 as varchar(50)) as address2,
  cast(district as varchar(20)) as district,
  cast(city_id as int) as city_id,
  cast(postal_code as varchar(10)) as postal_code,
  cast(phone as varchar(20)) as phone,
  now() as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  null::uuid as sl_source_bronze_key,
  true as sl_is_active,
  null::float as sl_data_quality_score,
  0::int as sl_customer_count,
  0::int as sl_store_count
from src
