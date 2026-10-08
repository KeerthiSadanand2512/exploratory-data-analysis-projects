# Data dictionary

Grain: one restaurant listing per `restaurant_id`. Cleaned output retains all raw fields with normalized names. CSV nulls are empty fields; DuckDB preserves numeric and boolean types.

| Field | Type | Meaning / treatment |
|---|---|---|
| restaurant_id | integer | Source unique identifier; conflicting duplicates fail validation |
| restaurant_name | text | Name as supplied, surrounding whitespace trimmed |
| country_code | integer | Join key into the supplied country workbook |
| city | text | Source city; use together with country |
| address | text | Source street/address text |
| locality | text | Locality label |
| locality_verbose | text | Expanded locality label |
| longitude | decimal | Degrees, validated between −180 and 180 |
| latitude | decimal | Degrees, validated between −90 and 90 |
| cuisines | text, nullable | Comma-separated cuisine labels; nine absent in this snapshot |
| average_cost_for_two | numeric | Cost estimate in recorded currency; zeros retained but excluded from cost summaries |
| currency | text | Unverified source label; known apparent inconsistencies |
| has_table_booking | text | Standardized Yes/No |
| has_online_delivery | text | Standardized Yes/No |
| is_delivering_now | text | Snapshot Yes/No status; not a current availability statement |
| switch_to_order_menu | text | Original Yes/No flag, retained even though constant in this snapshot |
| price_range | integer | Source ordinal tier, 1–4; not currency-normalized |
| aggregate_rating | decimal | Original 0–5 value; zero can represent unrated |
| rating_color | text | Source rating colour category |
| rating_text | text | Source rating description including Not rated |
| votes | integer | Nonnegative source engagement/review count, not sales |
| country | text | Lookup name; Phillipines corrected to Philippines |
| is_rated | boolean | Rating >0 and rating text is not Not rated |
| rating_for_analysis | nullable decimal | Original rating for rated rows, null otherwise |
| cuisines_missing | boolean | Cuisine field is absent after whitespace cleanup |
| valid_coordinates | boolean | Range validation passed and coordinate pair is not (0,0); does not prove actual location |

`restaurant_cuisines` has two columns: `restaurant_id` (foreign key) and `cuisine` (trimmed individual label). The composite key is unique. Missing cuisines do not generate bridge records.

## Output tables

| Table | Grain and denominator |
|---|---|
| overview | Entire dataset; service shares use all listings, rating mean uses rated listings |
| high_rating_booking | Rating ≥4 subset; booking percentage denominator is that subset |
| country_summary | One country; share of all restaurants |
| city_summary | One country–city pair |
| service_comparison | Service × Yes/No; mean uses rated records, both total and rated counts shown |
| price_range_summary | Country × price tier |
| cuisine_summary | Cuisine with at least 20 total listings; multiple cuisines can include same restaurant |
| cost_summary | Country × recorded currency, positive costs only; median and interquartile bounds |
| service_by_city_price | Country × city × price tier × booking; at least 10 rated records per group |
| most_voted_per_country | Top five rated records by votes in each country; ties resolved by ID |
