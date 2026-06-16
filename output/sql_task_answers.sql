-- Loblaw Strategy & Analytics Case - SQL task answers
-- Assumptions:
-- 1. discount_sales_by_region has the columns:
--    discount_market, period, sales_2020, sales_2019,
--    promo_sales_2020, promo_sales_2019, e_commerce_sales_2020,
--    e_commerce_sales_2019.
-- 2. industry_sales_by_region has analogous industry_market columns.
-- 3. Date parsing syntax varies by SQL version; functions below show logic.

-- (1) Average weekly sales for Maxi in 2020
SELECT
  AVG(sales_2020) AS avg_weekly_sales_2020
FROM discount_sales_by_region
WHERE discount_market = 'MAXI BANNER QUEBEC';

-- Numeric result from workbook: $61.5M.

-- (2) Promo penetration by Industry Market in 2020
SELECT
  industry_market,
  SUM(promo_sales_2020) / NULLIF(SUM(sales_2020), 0) AS promo_penetration_2020
FROM industry_sales_by_region
GROUP BY industry_market;

-- Numeric results:
-- TOTAL ATLANTIC MARKET: 35.5%
-- TOTAL NATIONAL MARKET: 35.2%
-- TOTAL ONTARIO MARKET: 33.5%
-- TOTAL QUEBEC MARKET: 33.1%
-- TOTAL WEST MARKET: 35.5%

-- (3) By Discount Market, identify the week with the highest E-Com sales in 2020
WITH ranked AS (
  SELECT
    discount_market,
    period,
    e_commerce_sales_2020,
    ROW_NUMBER() OVER (
      PARTITION BY discount_market
      ORDER BY e_commerce_sales_2020 DESC
    ) AS rn
  FROM discount_sales_by_region
)
SELECT
  discount_market,
  period,
  e_commerce_sales_2020
FROM ranked
WHERE rn = 1;

-- (4) For No Frills Ontario, pull the third week of each month and 2019 sales
WITH prepared AS (
  SELECT
    discount_market,
    period,
    sales_2019,
    CAST('20' || SUBSTRING(period FROM 11 FOR 2) || '-' ||
      CASE SUBSTRING(period FROM 4 FOR 3)
        WHEN 'Jan' THEN '01'
        WHEN 'Feb' THEN '02'
        WHEN 'Mar' THEN '03'
        WHEN 'Apr' THEN '04'
        WHEN 'May' THEN '05'
        WHEN 'Jun' THEN '06'
        WHEN 'Jul' THEN '07'
        WHEN 'Aug' THEN '08'
        WHEN 'Sep' THEN '09'
        WHEN 'Oct' THEN '10'
        WHEN 'Nov' THEN '11'
        WHEN 'Dec' THEN '12'
      END || '-' || SUBSTRING(period FROM 8 FOR 2) AS DATE) AS week_end_date
  FROM discount_sales_by_region
  WHERE discount_market = 'NO FRILLS ONTARIO'
),
month_ranked AS (
  SELECT
    discount_market,
    period,
    sales_2019,
    EXTRACT(MONTH FROM week_end_date) AS month_number,
    ROW_NUMBER() OVER (
      PARTITION BY EXTRACT(MONTH FROM week_end_date)
      ORDER BY week_end_date
    ) AS week_in_month
  FROM prepared
  WHERE week_end_date >= DATE '2020-01-01'
    AND week_end_date < DATE '2021-01-01'
)
SELECT
  month_number,
  period,
  sales_2019
FROM month_ranked
WHERE week_in_month = 3;

-- The workbook result matches the prompt example: Apr -> WE Apr 18 20, $118.8M.

-- (5) Using a Join, calculate No Frills Ontario market share on WE Jun 27 20
SELECT
  d.period,
  d.sales_2020 AS no_frills_ontario_sales_2020,
  i.sales_2020 AS total_ontario_market_sales_2020,
  d.sales_2020 / NULLIF(i.sales_2020, 0) AS market_share_2020
FROM discount_sales_by_region d
JOIN industry_sales_by_region i
  ON d.period = i.period
WHERE d.discount_market = 'NO FRILLS ONTARIO'
  AND i.industry_market = 'TOTAL ONTARIO MARKET'
  AND d.period = 'WE Jun 27 20';

-- Numeric result from workbook: 9.6% ($115.6M / $1.21B).
