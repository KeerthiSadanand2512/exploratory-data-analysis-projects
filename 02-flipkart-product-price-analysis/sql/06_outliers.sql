-- Screening, not proof of error. Broad categories can mix different product types.
WITH bounds AS (
 SELECT category, count(*) AS category_n,
 quantile_cont(selling_price, 0.25) AS q1,
 quantile_cont(selling_price, 0.75) AS q3
 FROM products WHERE valid_price AND category <> 'Unknown' GROUP BY category
), scored AS (
 SELECT p.*, b.category_n, b.q1, b.q3,
 greatest(0, b.q1 - 1.5 * (b.q3-b.q1)) AS lower_fence,
 b.q3 + 1.5 * (b.q3-b.q1) AS upper_fence,
 (p.selling_price-b.q3)/(b.q3-b.q1) AS iqr_distance_above_q3
 FROM products p JOIN bounds b USING(category)
 WHERE p.valid_price AND b.category_n >= 30 AND b.q3 > b.q1
)
SELECT *, CASE WHEN selling_price > upper_fence THEN 'High' ELSE 'Low' END AS flag
FROM scored WHERE selling_price > upper_fence OR selling_price < lower_fence
ORDER BY iqr_distance_above_q3 DESC, listing_id;
