"""UI behavior checks use the committed real-data snapshot, with no network."""
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / 'app.py'

class DashboardTests(unittest.TestCase):
    def test_filters_update_metrics_and_empty_state(self):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.metric[0].value, '20,000')
        at.multiselect(key='categories').set_value(['Clothing']).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.metric[0].value, '6,198')
        at.text_input(key='search').set_value('nonexistent-product-xyz987654').run()
        self.assertEqual(len(at.exception), 0)
        self.assertIn('No listings match', at.warning[0].value)

    def test_price_filter_and_review_direction(self):
        at = AppTest.from_file(str(APP), default_timeout=30).run()
        at.checkbox(key='limit_price').check().run()
        at.slider(key='price_range').set_range(0.0, 500.0).run()
        self.assertEqual(len(at.exception), 0)
        value = float(at.metric[1].value.replace('₹','').replace(',',''))
        self.assertLessEqual(value, 500)
        self.assertLess(int(at.metric[0].value.replace(',','')), 20000)
        at.selectbox(key='flag').select('Low').run()
        self.assertEqual(len(at.exception), 0)

if __name__ == '__main__':
    unittest.main()
