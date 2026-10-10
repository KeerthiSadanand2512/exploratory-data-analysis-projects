# Methodology and data dictionary

## Source and grain

The source is the PromptCloud Flipkart product listing sample on Kaggle. One input row is a scraped listing observation, not an order, sale, customer, or SKU inventory count. The source contains 20,000 rows and 15 fields. Crawls span December 2015 to June 2016. This is a historical sample, with no evidence that it represents all Flipkart listings.

## Field mapping

| Source field | Treatment |
|---|---|
| uniq_id | Deduplication key; blank values get distinct source-row keys |
| crawl_timestamp | UTC timestamp; latest observation per key retained |
| product_url | Preserved for manual investigation |
| product_name | Preserved |
| product_category_tree | First JSON array path, split at ` >> `; use top-level category |
| pid | Preserved, not used to infer sales or deduplicate variants |
| retail_price | Numeric reference/list price in INR |
| discounted_price | Numeric listed selling price in INR |
| image | Retained in raw table; unused |
| is_FK_Advantage_product | Retained in raw table; unused |
| description | Retained in raw table; unused |
| product_rating | Numeric values 1–5 retained; all other values become NULL |
| overall_rating | Retained in raw table; not mixed with product_rating |
| brand | Trim outer whitespace; blank → Unknown; no speculative name merging |
| product_specifications | Retained in raw table; unused |

## Denominators and formulas

Price population: retained rows where selling price is finite and strictly positive. An invalid retail price does not exclude an otherwise valid selling price from price statistics.

Discount population: retained rows with finite positive retail and selling prices, and selling ≤ retail. Invalid pairs remain in the clean table but receive NULL discount. Discount percent = `(retail_price - selling_price) / retail_price * 100`. The category mean is the arithmetic average of listing percentages, not a ratio of aggregate prices or a revenue-weighted measure. Zero discounts remain in the denominator. Invalid pairs are counted separately.

Brand shares: brand listing count divided by all retained listings in the same category, including Unknown brands. `DENSE_RANK` assigns equal ranks for equal volumes. Global brand chart excludes Unknown but does not renormalize shares.

Ratings: valid numeric product ratings divided by all retained listings in each category. Correlation uses only rows with both valid price and rating and is suppressed below 30 pairs. A constant price/rating series can also yield undefined correlation. Missing ratings are never set to zero or imputed. Correlations are exploratory and do not establish causal price effects or represent unrated listings.

Percentiles: DuckDB `quantile_cont` uses linear interpolation; P50 is the median. Price percentile ranks use `(rank - 1)/(n - 1)`, with the single-row case handled as zero by DuckDB. Tied prices receive the same percentile rank. `NTILE(4)` divides row counts approximately evenly and may split ties; listing_id breaks quartile ordering ties deterministically.

Outliers: IQR = Q3 − Q1. Lower fence = max(0, Q1 − 1.5 × IQR); upper fence = Q3 + 1.5 × IQR. Strictly outside values are flagged. Groups with fewer than 30 valid prices, Unknown category, or zero IQR are excluded from screening. Their absence from the review queue does not establish that their prices are normal. Ranking the queue by `(selling_price − Q3)/IQR` prioritizes upper extremes; both lower and upper flags are exported. Outliers remain in all other analyses.

## Cleaning and quality checks

`raw_products` preserves the source fields as text plus source_row. `products` converts types and retains the chosen observation per uniq_id. Timestamp ties prefer the first source row. Malformed category JSON becomes Unknown. Missing numeric fields and nonnumeric price text become NULL. Nonfinite or nonpositive prices are excluded through explicit flags.

The observed dataset has no duplicate uniq_id rows, 78 unusable price pairs, 5,861 missing brands, and 1,849 valid ratings. The source has 265 extracted category labels, many with too few listings for stable comparisons. No broad automatic category merging is attempted. Charts compare sufficiently populated groups, and full category tables retain every label.

## Reproducibility and validation

Run the pipeline before capturing screenshots. Committed reports describe the source fingerprint in reports/provenance.json; rerunning with a different source changes results. The pipeline updates the computed findings section in the README. Screenshots require explicit regeneration.

Offline tests verify cleaning, timestamp parsing, deduplication, blank IDs, percentile interpolation, tied ranks, outlier detection, zero-IQR exclusions, and share reconciliation. The completed run was also checked against independent pandas summaries of the source data. No simulated data is used for reported business findings.

## Interpretation

Use the results to prioritize data review and generate pricing hypotheses. Narrow categories to comparable types, sizes, quantities, and variants before setting prices. Deep listed discounts do not prove customer savings against historical prices. Add costs, transactions, stock availability, and longitudinal observations to study margins, demand, elasticity, or realized promotion effectiveness.
