with s as (select * from {{ source('silver','sl_store') }}),
     a as (select * from {{ source('silver','sl_address') }})
select
  md5(cast(s.store_id as text))::uuid as gl_dim_store_key,
  s.store_id, s.manager_staff_id,
  ''::varchar(45) as manager_first_name, ''::varchar(45) as manager_last_name, ''::varchar(91) as manager_full_name, null::varchar(50) as manager_email,
  a.address as address_line1, a.address2 as address_line2, a.district, ''::varchar(50) as city, a.postal_code, a.phone, ''::varchar(50) as country,
  s.last_update, s.sl_total_customers as total_customers, s.sl_total_rentals as total_rentals, s.sl_total_revenue as total_revenue, s.sl_avg_rental_rate as avg_rental_rate,
  0 as total_inventory_items, 0 as active_customers,
  null::numeric(8,2) as revenue_per_customer, null::float as inventory_turnover_rate, null::float as customer_retention_rate, null::float as avg_rentals_per_day,
  null::varchar(20) as store_tier, false as is_flagship_store, null::varchar(25) as primary_customer_segment
from s left join a on a.address_id = s.address_id
