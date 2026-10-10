-- Shares use ALL listings in each category, including unknown brands.
WITH volumes AS (
 SELECT category, brand, count(*) AS listings FROM products GROUP BY category, brand
), shares AS (
 SELECT *, 100.0 * listings / sum(listings) OVER (PARTITION BY category) AS category_share_pct
 FROM volumes
)
SELECT *, dense_rank() OVER (PARTITION BY category ORDER BY listings DESC) AS volume_rank
FROM shares ORDER BY category, volume_rank, brand;
