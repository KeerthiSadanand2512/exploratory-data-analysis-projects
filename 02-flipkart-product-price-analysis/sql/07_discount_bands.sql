WITH bands AS (
 SELECT CASE WHEN discount_pct = 0 THEN '0%'
 WHEN discount_pct < 25 THEN '>0–<25%'
 WHEN discount_pct < 50 THEN '25–<50%'
 WHEN discount_pct < 75 THEN '50–<75%' ELSE '75–100%' END AS discount_band,
 CASE WHEN discount_pct = 0 THEN 0 WHEN discount_pct < 25 THEN 1
 WHEN discount_pct < 50 THEN 2 WHEN discount_pct < 75 THEN 3 ELSE 4 END AS band_order
 FROM products WHERE valid_discount
)
SELECT discount_band, count(*) AS listings,
 100.0 * count(*) / sum(count(*)) OVER () AS share_pct
FROM bands GROUP BY discount_band, band_order ORDER BY band_order;
