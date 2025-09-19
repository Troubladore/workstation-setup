with src as (select * from {{ source('bronze','br_film') }})
select
  gen_random_uuid() as sl_film_key,
  cast(film_id as int) as film_id,
  cast(title as varchar(255)) as title,
  cast(description as text) as description,
  cast(release_year as int) as release_year,
  cast(language_id as int) as language_id,
  cast(original_language_id as int) as original_language_id,
  cast(rental_duration as smallint) as rental_duration,
  cast(rental_rate as numeric(4,2)) as rental_rate,
  cast(length as smallint) as length,
  cast(replacement_cost as numeric(5,2)) as replacement_cost,
  cast(rating as varchar(10)) as rating,
  now() as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  null::uuid as sl_source_bronze_key,
  true as sl_is_active,
  null::float as sl_data_quality_score,
  0::int as sl_rental_count,
  0::numeric(12,2) as sl_total_revenue,
  null::float as sl_avg_rental_duration
from src
