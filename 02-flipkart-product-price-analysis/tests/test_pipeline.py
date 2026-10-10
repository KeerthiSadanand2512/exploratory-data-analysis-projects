"""Behavioral tests run offline using small, explicitly synthetic fixtures."""
import tempfile
from pathlib import Path
import unittest
import duckdb
import pandas as pd
from src.pipeline import load_database, analyze

def row(identifier, price='100', **overrides):
    value = dict(uniq_id=identifier, pid=identifier, product_name='Fixture',
                 product_url='', crawl_timestamp='2016-03-25 22:59:23 +0000',
                 retail_price='200', discounted_price=price,
                 product_rating='No rating available', brand='',
                 product_category_tree='["Test >> Items"]')
    value.update(overrides)
    return value

class PipelineTests(unittest.TestCase):
    def run_fixture(self, rows):
        con = duckdb.connect()
        self.addCleanup(con.close)
        with tempfile.TemporaryDirectory() as folder:
            csv = Path(folder) / 'fixture.csv'
            pd.DataFrame(rows).to_csv(csv, index=False)
            load_database(csv, con)
        return con, analyze(con)

    def test_cleaning_and_denominators(self):
        con, result = self.run_fixture([
            row('a', '100', product_rating='4'), row('b', '0'),
            row('c', '300'), row('d', 'bad'), row('e', 'inf'),
            row('f', '50', product_rating='6', product_category_tree='malformed')])
        q = result['quality'].iloc[0]
        self.assertEqual(q.valid_prices, 3)
        self.assertEqual(q.valid_discounts, 2)
        self.assertEqual(q.rated_listings, 1)
        self.assertEqual(q.unknown_categories, 1)
        self.assertEqual(q.above_retail, 2)  # Includes infinity, also flagged invalid.
        self.assertEqual(con.execute('SELECT count(crawled_at) FROM products').fetchone()[0], 6)
        self.assertAlmostEqual(q.rating_coverage_pct, 100/6)

    def test_latest_duplicate_and_blank_ids(self):
        con, result = self.run_fixture([row('a','10'),
            row('a','20',crawl_timestamp='2016-04-01 00:00:00 +0000'),row(''),row('')])
        self.assertEqual(result['quality'].iloc[0].duplicates_removed, 1)
        self.assertEqual(con.execute("SELECT selling_price FROM products WHERE listing_id='a'").fetchone()[0],20)
        self.assertEqual(result['quality'].iloc[0].retained_listings,3)

    def test_percentiles_and_tied_rank(self):
        _, result = self.run_fixture([row(str(i),str(v)) for i,v in enumerate([10,20,20,40])])
        category = result['categories'].iloc[0]
        self.assertEqual(category.p25,17.5)
        self.assertEqual(category.p50,20)
        self.assertEqual(category.p75,25)
        ranks = result['price_positions'].query('selling_price == 20').price_percent_rank
        self.assertTrue((ranks == 1/3).all())
        self.assertEqual(len(result['outliers']),0)

    def test_outlier_and_zero_iqr_guard(self):
        rows = [row(str(i),str(i+1)) for i in range(39)] + [row('high','1000')]
        rows += [row('flat'+str(i),'1',product_category_tree='["Flat"]') for i in range(40)]
        _, result = self.run_fixture(rows)
        self.assertEqual(result['outliers'].listing_id.tolist(),['high'])
        self.assertEqual(result['outliers'].iloc[0].flag,'High')

    def test_brand_shares_and_discount_bands_reconcile(self):
        _, result = self.run_fixture([row('a',brand='A'),row('b',brand='B'),row('c')])
        self.assertAlmostEqual(result['brands'].category_share_pct.sum(),100)
        self.assertEqual(result['discount_bands'].listings.sum(),3)
        self.assertTrue((result['brands'].volume_rank == 1).all())

if __name__ == '__main__':
    unittest.main()
