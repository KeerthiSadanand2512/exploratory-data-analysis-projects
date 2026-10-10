-- Every category is exported. Compare groups with >= 30 valid prices in charts.
SELECT category, count(*) AS listings,
 count(*) FILTER (WHERE valid_price) AS priced_listings,
 count(discount_pct) AS discount_listings,
 count(rating) AS rated_listings,
 100.0 * count(rating) / count(*) AS rating_coverage_pct,
 min(selling_price) FILTER (WHERE valid_price) AS min_price,
 quantile_cont(selling_price, 0.25) FILTER (WHERE valid_price) AS p25,
 quantile_cont(selling_price, 0.50) FILTER (WHERE valid_price) AS p50,
 quantile_cont(selling_price, 0.75) FILTER (WHERE valid_price) AS p75,
 quantile_cont(selling_price, 0.90) FILTER (WHERE valid_price) AS p90,
 max(selling_price) FILTER (WHERE valid_price) AS max_price,
 avg(discount_pct) AS mean_discount_pct,
 median(discount_pct) AS median_discount_pct
FROM products GROUP BY category ORDER BY listings DESC, category;
