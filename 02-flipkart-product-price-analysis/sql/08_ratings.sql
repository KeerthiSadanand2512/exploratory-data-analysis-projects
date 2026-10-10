-- Sparse, self-selected rated subset: this correlation cannot imply causation.
SELECT category, count(*) AS listings, count(rating) AS rated_listings,
 100.0 * count(rating)/count(*) AS rating_coverage_pct,
 avg(rating) AS mean_rating,
 count(*) FILTER (WHERE rating IS NOT NULL AND valid_price) AS price_rating_pairs,
 CASE WHEN count(*) FILTER (WHERE rating IS NOT NULL AND valid_price) >= 30
 THEN corr(selling_price, rating) FILTER (WHERE valid_price) END AS price_rating_correlation
FROM products GROUP BY category ORDER BY rated_listings DESC, category;
