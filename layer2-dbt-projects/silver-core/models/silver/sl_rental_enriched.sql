with r as (
  select * from {{ source('bronze','br_rental') }}
),
inv as (
  select inventory_id, film_id, store_id from {{ source('bronze','br_inventory') }}
),
p as (
  select rental_id, sum(amount)::numeric(12,2) as revenue_amount
  from {{ source('bronze','br_payment') }}
  group by rental_id
)
select
  gen_random_uuid() as sl_rental_key,
  cast(r.rental_id as int) as rental_id,
  cast(r.rental_date as timestamp) as rental_date,
  cast(r.return_date as timestamp) as return_date,
  cast(r.customer_id as int) as customer_id,
  cast(r.staff_id as int) as staff_id,
  cast(inv.film_id as int) as film_id,
  cast(inv.store_id as int) as store_id,
  extract(epoch from (r.return_date - r.rental_date))/3600.0 as rental_duration_actual,
  -- simple planned duration proxy from film.rental_duration if desired (join sl_film if needed)
  null::float as rental_duration_planned,
  null::numeric(4,2) as rental_rate,
  null::numeric(5,2) as replacement_cost,
  p.revenue_amount,
  cast(r.last_update as timestamp) as last_update,
  now() as sl_created_time,
  now() as sl_updated_time,
  true as sl_is_active,
  null::float as sl_data_quality_score
from r
left join inv on inv.inventory_id = r.inventory_id
left join p   on p.rental_id = r.rental_id
