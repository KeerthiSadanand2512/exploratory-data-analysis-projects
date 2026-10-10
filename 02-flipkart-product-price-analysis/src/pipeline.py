"""SQL-first analysis with reproducible data, findings and charts. Run from the project root."""
from pathlib import Path
import argparse
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
import duckdb
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SQL = ROOT / 'sql'
REQUIRED = {'uniq_id','pid','product_name','product_url','crawl_timestamp',
            'retail_price','discounted_price','product_rating','brand','product_category_tree'}

def load_database(csv_path, connection):
    connection.execute("SET TimeZone = 'UTC'")
    raw = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing = REQUIRED - set(raw.columns)
    if missing:
        raise ValueError(f'Missing required columns: {sorted(missing)}')
    if raw.empty:
        raise ValueError('Input CSV has no rows')
    raw['source_row'] = range(1, len(raw) + 1)
    connection.register('input_frame', raw)
    connection.execute('CREATE OR REPLACE TABLE raw_products AS SELECT * FROM input_frame')
    connection.unregister('input_frame')
    connection.execute((SQL / '01_clean.sql').read_text())

def analyze(connection):
    return {p.stem[3:]: connection.execute(p.read_text()).df()
            for p in sorted(SQL.glob('*.sql')) if not p.name.startswith('01_')}

from src.visualize import plots

def report(results, destination, provenance):
    q = results['quality'].iloc[0]
    cats = results['categories']
    eligible = cats[(cats.discount_listings >= 30) & (cats.category != 'Unknown')]
    leader = eligible.nlargest(1, 'mean_discount_pct')
    discount_insight = (f"{leader.iloc[0].category} has the highest mean discount among categories with at least 30 valid discounts: {leader.iloc[0].mean_discount_pct:.1f}%." if len(leader) else 'No category meets the discount comparison threshold.')
    insights = [
        f"{cats.iloc[0].category} accounts for {cats.iloc[0].listings / q.retained_listings * 100:.1f}% of retained listings.",
        discount_insight,
        f"{int(q.rated_listings):,} listings ({q.rating_coverage_pct:.1f}%) have a valid numeric rating. Rating results describe this subset only.",
        f"{len(results['outliers']):,} listings exceed the category IQR fences. These are candidates for manual review, not confirmed pricing errors.",
        f"Brand is missing for {int(q.missing_brands):,} listings ({q.missing_brands/q.retained_listings*100:.1f}%). Brand rankings are incomplete."
    ]
    (destination / 'findings.md').write_text('# Findings\n\n' + '\n'.join('- '+s for s in insights) + '\n\nPrices are INR. Historical crawl: '+str(q.first_crawl)+' to '+str(q.last_crawl)+'.\n\n## Recommended next steps\n\nReview flagged items within narrower product types and check variant, unit, and bundle differences. Compare discount policies only after checking category composition. Collect sales, costs, stock, and time-series data before assessing profitability or proposing price changes.\n\nNo sales volumes, costs, realized transaction prices, or representative sampling weights are available.\n', encoding='utf-8')
    readme = ROOT / 'README.md'
    if readme.exists():
        content = readme.read_text()
        start_marker, end_marker = '<!-- FINDINGS START -->', '<!-- FINDINGS END -->'
        if start_marker in content and end_marker in content:
            before = content.split(start_marker)[0]
            after = content.split(end_marker)[1]
            findings = '\n## Computed findings\n\n' + '\n'.join('- ' + line for line in insights) + '\n\n'
            readme.write_text(before + start_marker + findings + end_marker + after)
    (destination / 'data_quality.json').write_text(results['quality'].to_json(orient='records', date_format='iso', indent=2))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, default=ROOT / 'data/raw/flipkart_com-ecommerce_sample.csv')
    args = parser.parse_args()
    if not args.csv.exists():
        parser.error('CSV missing. Run python -m src.download or use --csv PATH.')
    destination = ROOT / 'reports'
    for sub in ['tables','figures']:
        (destination/sub).mkdir(parents=True, exist_ok=True)
    (ROOT / 'data/processed').mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(ROOT / 'data/processed/flipkart.duckdb')) as connection:
        load_database(args.csv, connection)
        results = analyze(connection)
        connection.execute('SELECT * FROM products ORDER BY listing_id').df().to_csv(
            ROOT / 'data/processed/listings.csv.gz', index=False,
            compression={'method': 'gzip', 'mtime': 0})
    provenance = {'source':'https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products',
                  'sha256':hashlib.sha256(args.csv.read_bytes()).hexdigest(), 'filename':args.csv.name,
                  'duckdb_version':duckdb.__version__, 'raw_rows':int(results['quality'].iloc[0].raw_rows)}
    (destination/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    for name, df in results.items():
        df.to_csv(destination/'tables'/f'{name}.csv', index=False)
    plots(results, destination/'figures')
    report(results, destination, provenance)
    print(results['quality'].to_string(index=False))
    print('Created processed data, SQL tables, charts and findings. Run: python -m streamlit run app.py')

if __name__ == '__main__':
    main()
