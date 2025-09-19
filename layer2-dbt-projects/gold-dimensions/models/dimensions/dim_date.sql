{{ config(materialized='table') }}
-- Replace this with a proper date spine in real deployments.
select
  20250101::int as date_key,
  '2025-01-01'::date as full_date,
  1 as day_of_month, 1 as day_of_year, 3 as day_of_week,
  'Wednesday' as day_name, 'Wed' as day_name_short,
  1 as week_of_year, 1 as week_of_month, 'Weekday' as weekday_indicator,
  1 as month_number, 'January' as month_name, 'Jan' as month_name_short, '2025-01' as month_year,
  1 as quarter_number, 'Q1' as quarter_name, '2025-Q1' as quarter_year,
  2025 as year_number,
  false as is_weekend, true as is_weekday, false as is_holiday, true as is_business_day,
  null::text as holiday_name, null::text as holiday_type,
  2025 as fiscal_year, 1 as fiscal_quarter, 1 as fiscal_month,
  false as is_current_day, false as is_current_week, false as is_current_month, false as is_current_quarter, false as is_current_year,
  null::int as days_from_today,
  false as is_month_end, false as is_quarter_end, false as is_year_end, false as is_leap_year,
  'Winter' as season
