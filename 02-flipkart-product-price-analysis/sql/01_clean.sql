-- Raw strings remain available in raw_products; deduplicate nonblank uniq_id.
-- The latest parseable crawl wins, with source row as a deterministic tie breaker.
CREATE OR REPLACE TABLE products AS
WITH typed AS (
 SELECT *,
   coalesce(nullif(trim(uniq_id), ''), '__missing_' || source_row) AS listing_id,
   coalesce(try_cast(crawl_timestamp AS TIMESTAMPTZ),
     try_strptime(crawl_timestamp, '%Y-%m-%d %H:%M:%S %z')) AS crawled_at,
   try_cast(retail_price AS DOUBLE) AS retail,
   try_cast(discounted_price AS DOUBLE) AS selling,
   try_cast(product_rating AS DOUBLE) AS rating_value,
   coalesce(nullif(trim(brand), ''), 'Unknown') AS brand_name,
   coalesce(nullif(trim(split_part(json_extract_string(try_cast(product_category_tree AS JSON), '$[0]'), ' >> ', 1)), ''), 'Unknown') AS category
 FROM raw_products
), dedup AS (
 SELECT *, row_number() OVER (
   PARTITION BY listing_id ORDER BY crawled_at DESC NULLS LAST, source_row
 ) AS duplicate_rank FROM typed
)
SELECT listing_id, pid, product_name, product_url, crawled_at,
       category, brand_name AS brand, retail AS retail_price,
       selling AS selling_price,
       CASE WHEN rating_value BETWEEN 1 AND 5 THEN rating_value END AS rating,
       coalesce(isfinite(selling) AND selling > 0, false) AS valid_price,
       coalesce(isfinite(retail) AND isfinite(selling)
         AND retail > 0 AND selling > 0 AND selling <= retail, false) AS valid_discount,
       CASE WHEN isfinite(retail) AND isfinite(selling)
         AND retail > 0 AND selling > 0 AND selling <= retail
         THEN 100.0 * (retail - selling) / retail END AS discount_pct
FROM dedup WHERE duplicate_rank = 1;
