with r as (select * from {{ source('silver','sl_rental_enriched') }}),
     f as (select film_id, rental_duration, rental_rate, replacement_cost from {{ source('silver','sl_film') }}),
     d_film as (select * from {{ ref('dim_film') }}),
     d_store as (select * from {{ ref('dim_store') }}),
     d_staff as (select * from {{ ref('dim_staff') }}),
     d_date as (select * from {{ ref('dim_date') }})
select
  md5(cast(r.rental_id as text))::uuid as gl_fact_rental_key,
  r.rental_id,
  d_film.gl_dim_film_key   as film_key,
  d_store.gl_dim_store_key as store_key,
  d_staff.gl_dim_staff_key as staff_key,
  dd1.date_key             as rental_date_key,
  dd2.date_key             as return_date_key,
  r.rental_date::date      as rental_date,
  r.rental_date            as rental_datetime,
  r.return_date::date      as return_date,
  r.return_date            as return_datetime,
  r.rental_duration_actual,
  f.rental_duration        as rental_duration_planned,
  f.rental_rate,
  f.replacement_cost,
  coalesce(r.revenue_amount, f.rental_rate) as revenue_amount,
  (extract(dow from r.rental_date) in (0,6)) as is_weekend_rental,
  false as is_holiday_rental,
  extract(hour from r.rental_date) as rental_hour,
  extract(quarter from r.rental_date)::int as rental_quarter,
  extract(month from r.rental_date)::int as rental_month,
  extract(year from r.rental_date)::int as rental_year,
  now() as gl_created_time,
  now() as gl_updated_time
from r
left join f      on f.film_id = r.film_id
left join d_film on d_film.film_id = r.film_id
left join d_store on d_store.store_id = r.store_id
left join d_staff on d_staff.staff_id = r.staff_id
left join d_date  dd1 on dd1.full_date = r.rental_date::date
left join d_date  dd2 on dd2.full_date = r.return_date::date
