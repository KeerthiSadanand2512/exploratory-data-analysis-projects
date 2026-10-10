-- PERCENT_RANK gives tied prices the same rank; NTILE may split ties.
SELECT listing_id, product_name, category, brand, selling_price,
 percent_rank() OVER (PARTITION BY category ORDER BY selling_price) AS price_percent_rank,
 ntile(4) OVER (PARTITION BY category ORDER BY selling_price, listing_id) AS price_quartile
FROM products WHERE valid_price
ORDER BY category, selling_price, listing_id;
