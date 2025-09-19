with f as (select * from {{ source('silver','sl_film') }}),
     l as (select language_id, name as language_name from {{ source('silver','sl_language') }})
select
  md5(cast(f.film_id as text))::uuid as gl_dim_film_key,
  f.film_id, f.title, f.description, f.release_year, f.rating,
  coalesce(l.language_name,'Unknown') as language_name,
  null::varchar(20) as original_language_name,
  null::varchar(200) as category_names, null::varchar(25) as primary_category,
  null::varchar(1000) as actor_names, null::varchar(90) as lead_actor,
  f.length as length_minutes, f.rental_duration as rental_duration_days, f.rental_rate, f.replacement_cost,
  false as has_trailers, false as has_commentaries, false as has_deleted_scenes, false as has_behind_scenes, 0 as special_features_count,
  0 as total_inventory_copies, coalesce(f.sl_rental_count,0) as total_rentals, coalesce(f.sl_total_revenue,0.00) as total_revenue,
  f.sl_avg_rental_duration as avg_rental_duration, null::float as rental_frequency,
  null::varchar(20) as length_category, null::varchar(20) as price_tier, null::float as popularity_score, false as is_classic,
  true as is_currently_available, null::timestamptz as last_rental_date, null::int as days_since_last_rental
from f left join l on l.language_id = f.language_id
