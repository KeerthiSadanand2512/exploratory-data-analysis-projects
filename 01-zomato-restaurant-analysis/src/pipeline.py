"""Run from the repository root: python -m src.pipeline."""
from pathlib import Path
import hashlib
import json
import re
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NUMERIC = ['restaurant_id', 'country_code', 'longitude', 'latitude',
           'average_cost_for_two', 'price_range', 'aggregate_rating', 'votes']
FLAGS = ['has_table_booking', 'has_online_delivery', 'is_delivering_now', 'switch_to_order_menu']


def normalize_columns(df):
    df = df.copy()
    df.columns = [re.sub(r'\W+', '_', c.strip().lower()) for c in df.columns]
    if df.columns.duplicated().any():
        raise ValueError('Duplicate normalized columns')
    return df


def clean_data(raw, countries):
    """Preserve source values, add explicit analysis fields, reject invalid inputs."""
    df, lookup = normalize_columns(raw), normalize_columns(countries)
    required = set(NUMERIC + FLAGS + ['restaurant_name', 'city', 'cuisines', 'currency', 'rating_text'])
    if missing := required - set(df.columns):
        raise ValueError(f'Missing columns: {sorted(missing)}')
    input_rows = len(df)
    df = df.drop_duplicates().copy()
    for col in df.select_dtypes(include=['object', 'string']):
        df[col] = df[col].astype('string').str.strip().replace('', pd.NA)
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='raise')
        if df[col].isna().any():
            raise ValueError(f'Missing numeric values: {col}')
    for col in ['restaurant_id', 'country_code', 'price_range', 'votes']:
        if (df[col] % 1 != 0).any():
            raise ValueError(f'Non-integer values: {col}')
        df[col] = df[col].astype('int64')
    if df.restaurant_id.duplicated().any():
        raise ValueError('Conflicting duplicate restaurant IDs; review source records')
    for col in FLAGS:
        df[col] = df[col].str.lower().map({'yes': 'Yes', 'no': 'No'})
        if df[col].isna().any():
            raise ValueError(f'Unknown yes/no values: {col}')
    if not df.aggregate_rating.between(0, 5).all():
        raise ValueError('Rating outside 0–5')
    if not df.price_range.between(1, 4).all():
        raise ValueError('Price range outside 1–4')
    if (df.votes < 0).any() or (df.average_cost_for_two < 0).any():
        raise ValueError('Negative votes or costs')
    if not df.latitude.between(-90, 90).all() or not df.longitude.between(-180, 180).all():
        raise ValueError('Invalid coordinates')
    lookup['country'] = lookup.country.str.strip().replace({'Phillipines': 'Philippines'})
    df = df.merge(lookup[['country_code', 'country']], on='country_code', how='left', validate='many_to_one')
    if df.country.isna().any():
        raise ValueError('Unmapped country code')
    df['is_rated'] = df.aggregate_rating.gt(0) & df.rating_text.ne('Not rated')
    df['rating_for_analysis'] = df.aggregate_rating.where(df.is_rated)
    df['cuisines_missing'] = df.cuisines.isna()
    df['valid_coordinates'] = ~(df.latitude.eq(0) & df.longitude.eq(0))
    df = df.sort_values('restaurant_id').reset_index(drop=True)
    bridge = df[['restaurant_id', 'cuisines']].dropna().copy()
    bridge['cuisine'] = bridge.cuisines.str.split(',')
    bridge = bridge.explode('cuisine')[['restaurant_id', 'cuisine']]
    bridge.cuisine = bridge.cuisine.str.strip()
    bridge = bridge[bridge.cuisine.ne('')].drop_duplicates().sort_values(['restaurant_id', 'cuisine']).reset_index(drop=True)
    audit = {'raw_rows': input_rows, 'clean_rows': len(df), 'exact_duplicates_removed': input_rows-len(df),
             'duplicate_restaurant_ids': int(df.restaurant_id.duplicated().sum()),
             'missing_cuisines': int(df.cuisines_missing.sum()), 'unrated_restaurants': int((~df.is_rated).sum()),
             'zero_cost_records': int(df.average_cost_for_two.eq(0).sum()),
             'zero_coordinate_pairs': int((~df.valid_coordinates).sum()),
             'rating_status_disagreements': int((df.aggregate_rating.eq(0) != df.rating_text.eq('Not rated')).sum()),
             'countries': int(df.country.nunique()), 'country_city_pairs': int(df[['country','city']].drop_duplicates().shape[0])}
    return df, bridge, audit


def queries():
    """Named SQL blocks are also executable as one ordinary DuckDB SQL script."""
    text = (ROOT/'sql/zomato_analysis.sql').read_text()
    blocks = re.split(r'^-- name: (\w+)\s*$', text, flags=re.M)
    return dict(zip(blocks[1::2], blocks[2::2]))


def run_pipeline():
    processed, results = ROOT/'data/processed', ROOT/'reports/tables'
    processed.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    raw_path = ROOT/'data/raw/zomato.csv'
    country_path = ROOT/'data/raw/Country-Code.xlsx'
    df, bridge, audit = clean_data(pd.read_csv(raw_path, encoding='latin1'), pd.read_excel(country_path))
    audit['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [raw_path, country_path]}
    df.to_csv(processed/'zomato_cleaned.csv', index=False)
    bridge.to_csv(processed/'restaurant_cuisines.csv', index=False)
    with duckdb.connect(str(processed/'zomato.duckdb')) as con:
        con.register('clean_frame', df)
        con.register('bridge_frame', bridge)
        con.execute('CREATE OR REPLACE TABLE restaurants AS SELECT * FROM clean_frame')
        con.execute('CREATE OR REPLACE TABLE restaurant_cuisines AS SELECT * FROM bridge_frame')
        outputs = {name: con.execute(sql).df() for name, sql in queries().items()}
        for name, result in outputs.items():
            result.to_csv(results/f'{name}.csv', index=False)
    (ROOT/'reports/data_quality.json').write_text(json.dumps(audit, indent=2)+'\n')
    from src.visualize import make_figures
    make_figures(df, bridge)
    write_findings(outputs, audit)
    print(json.dumps(audit, indent=2))
    return df, outputs


def write_findings(outputs, audit):
    row = outputs['overview'].iloc[0]
    booking = outputs['high_rating_booking'].iloc[0]
    country = outputs['country_summary'].iloc[0]
    content = f'''<!-- Generated by python -m src.pipeline; do not hand-edit metrics. -->
## Computed findings

- **{int(row.restaurants):,} restaurants** across **{audit['countries']} countries** and **{audit['country_city_pairs']} country–city pairs**.
- **{country.country} accounts for {int(country.restaurants):,} restaurants ({country.share_pct:.2f}%)**. This dataset is geographically concentrated.
- **{int(row.rated_restaurants):,} rated restaurants**; the restaurant-level mean among rated records is **{row.mean_rating:.2f}/5**. **{audit['unrated_restaurants']:,} unrated records** are excluded from all mean ratings.
- **{int(row.highly_rated):,} restaurants** have a rating ≥4.0. Of these, **{int(booking.with_booking):,} ({booking.booking_pct:.2f}%)** offer table booking.
- **{row.online_delivery_pct:.2f}%** of all restaurants offer online delivery; **{row.table_booking_pct:.2f}%** offer table booking.
- **{audit['missing_cuisines']} missing cuisine records**, **{audit['zero_cost_records']} zero-cost records**, and **{audit['zero_coordinate_pairs']} zero-coordinate pairs** are flagged rather than invented or silently replaced.

### Interpretation and proposed next steps

Prioritize country and city comparisons over a single global league table because coverage differs sharply. Test booking and delivery hypotheses within the same city and price tier; observed associations cannot establish a service's effect on ratings. Cuisine counts measure listed supply, not customer demand. Validate demand, economics and recent operating status before recommending expansion.

Costs are reported only within country and recorded currency, excluding zero costs. The source has suspicious currency labels (for example Philippine records labelled Botswana Pula); no exchange-rate conversion or undocumented correction is applied. Price range is an ordinal source category, not a common monetary scale.
'''
    (ROOT/'reports/findings.md').write_text(content)
    readme = ROOT/'README.md'
    if readme.exists():
        text = readme.read_text()
        start, end = '<!-- FINDINGS START -->', '<!-- FINDINGS END -->'
        if start in text and end in text:
            text = text.split(start)[0] + start + '\n' + content + '\n' + end + text.split(end)[1]
            readme.write_text(text)


if __name__ == '__main__':
    run_pipeline()
