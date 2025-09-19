with src as (select * from {{ source('bronze','br_inventory') }})
select
  gen_random_uuid() as sl_inventory_key,
  cast(inventory_id as int) as inventory_id,
  cast(film_id as int) as film_id,
  cast(store_id as int) as store_id,
  cast(last_update as timestamp) as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  true as sl_is_active,
  null::float as sl_data_quality_score
from src
