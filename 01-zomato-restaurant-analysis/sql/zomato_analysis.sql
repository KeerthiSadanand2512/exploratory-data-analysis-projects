-- Tables are built by python -m src.pipeline in data/processed/zomato.duckdb.
-- All averages use non-null rating_for_analysis (unrated rows excluded).
-- name: overview
SELECT COUNT(*) AS restaurants, COUNT(rating_for_analysis) AS rated_restaurants,
       AVG(rating_for_analysis) AS mean_rating,
       COUNT(*) FILTER (WHERE rating_for_analysis >= 4) AS highly_rated,
       100.0 * COUNT(*) FILTER (WHERE has_online_delivery = 'Yes') / NULLIF(COUNT(*),0) AS online_delivery_pct,
       100.0 * COUNT(*) FILTER (WHERE has_table_booking = 'Yes') / NULLIF(COUNT(*),0) AS table_booking_pct
FROM restaurants;

-- name: high_rating_booking
SELECT COUNT(*) AS highly_rated,
       COUNT(CASE WHEN has_table_booking = 'Yes' THEN 1 END) AS with_booking,
       100.0 * COUNT(CASE WHEN has_table_booking = 'Yes' THEN 1 END) / NULLIF(COUNT(*),0) AS booking_pct
FROM restaurants WHERE rating_for_analysis >= 4.0;

-- name: country_summary
SELECT country, COUNT(*) AS restaurants,
       100.0*COUNT(*)/SUM(COUNT(*)) OVER () AS share_pct,
       COUNT(rating_for_analysis) AS rated_restaurants, AVG(rating_for_analysis) AS mean_rating
FROM restaurants GROUP BY country ORDER BY restaurants DESC, country;

-- name: city_summary
SELECT country, city, COUNT(*) AS restaurants, COUNT(rating_for_analysis) AS rated_restaurants,
       AVG(rating_for_analysis) AS mean_rating,
       100.0*COUNT(*) FILTER (WHERE has_online_delivery='Yes')/COUNT(*) AS delivery_pct
FROM restaurants GROUP BY country, city ORDER BY restaurants DESC, country, city;

-- name: service_comparison
SELECT 'Table booking' AS service, has_table_booking AS available, COUNT(*) AS restaurants,
       COUNT(rating_for_analysis) AS rated_restaurants, AVG(rating_for_analysis) AS mean_rating
FROM restaurants GROUP BY has_table_booking
UNION ALL
SELECT 'Online delivery', has_online_delivery, COUNT(*), COUNT(rating_for_analysis), AVG(rating_for_analysis)
FROM restaurants GROUP BY has_online_delivery ORDER BY service, available;

-- name: price_range_summary
SELECT country, price_range, COUNT(*) AS restaurants, COUNT(rating_for_analysis) AS rated_restaurants,
       AVG(rating_for_analysis) AS mean_rating
FROM restaurants GROUP BY country, price_range ORDER BY country, price_range;

-- name: cuisine_summary
-- Each restaurant can contribute to several cuisines, once per cuisine.
SELECT c.cuisine, COUNT(*) AS restaurants, COUNT(r.rating_for_analysis) AS rated_restaurants,
       AVG(r.rating_for_analysis) AS mean_rating
FROM restaurant_cuisines c JOIN restaurants r USING (restaurant_id)
GROUP BY c.cuisine HAVING COUNT(*) >= 20 ORDER BY restaurants DESC, cuisine;

-- name: cost_summary
-- No cross-currency sums or averages. Zero costs are not treated as free meals.
SELECT country, currency, COUNT(*) AS records_with_positive_cost,
       MEDIAN(average_cost_for_two) AS median_cost_for_two,
       QUANTILE_CONT(average_cost_for_two,0.25) AS p25_cost,
       QUANTILE_CONT(average_cost_for_two,0.75) AS p75_cost
FROM restaurants WHERE average_cost_for_two > 0
GROUP BY country, currency ORDER BY country, currency;

-- name: service_by_city_price
-- Descriptive strata only; still not a causal estimate. Require 10 rated restaurants per group.
SELECT country, city, price_range, has_table_booking, COUNT(*) AS restaurants,
       COUNT(rating_for_analysis) AS rated_restaurants, AVG(rating_for_analysis) AS mean_rating
FROM restaurants GROUP BY country, city, price_range, has_table_booking
HAVING COUNT(rating_for_analysis) >= 10 ORDER BY country, city, price_range, has_table_booking;

-- name: most_voted_per_country
-- Votes are engagement counts, not sales. Rank within countries with deterministic ties.
WITH ranked AS (
 SELECT country, city, restaurant_name, restaurant_id, votes, rating_for_analysis,
        ROW_NUMBER() OVER (PARTITION BY country ORDER BY votes DESC, restaurant_id) AS vote_rank
 FROM restaurants WHERE is_rated
)
SELECT * FROM ranked WHERE vote_rank <= 5 ORDER BY country, vote_rank;
