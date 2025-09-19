with src as (select * from {{ source('bronze','br_language') }})
select
  gen_random_uuid() as sl_language_key,
  cast(language_id as int) as language_id,
  cast(name as char(20)) as name,
  now() as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  null::uuid as sl_source_bronze_key,
  true as sl_is_active,
  null::float as sl_data_quality_score
from src
