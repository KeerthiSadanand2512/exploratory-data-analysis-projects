from pathlib import Path
import json
import duckdb
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.pipeline import ROOT, clean_data, queries


@pytest.fixture(scope='module')
def data():
    return pd.read_csv(ROOT/'data/processed/zomato_cleaned.csv')


def test_raw_reconciliation(data):
    raw = pd.read_csv(ROOT/'data/raw/zomato.csv',encoding='latin1')
    assert len(data) == len(raw.drop_duplicates()) == 9551
    assert data.restaurant_id.is_unique
    assert set(data.restaurant_id) == set(raw['Restaurant ID'])
    assert data.rating_for_analysis.count() == raw['Aggregate rating'].gt(0).sum()
    assert data.loc[~data.is_rated,'rating_for_analysis'].isna().all()


def test_sql_independent_metrics(data):
    with duckdb.connect(str(ROOT/'data/processed/zomato.duckdb'),read_only=True) as con:
        results = {k:con.execute(v).df() for k,v in queries().items()}
    o = results['overview'].iloc[0]
    raw = pd.read_csv(ROOT/'data/raw/zomato.csv',encoding='latin1')
    assert o.restaurants == len(raw)
    assert o.mean_rating == pytest.approx(raw.loc[raw['Aggregate rating'].gt(0),'Aggregate rating'].mean())
    assert o.online_delivery_pct == pytest.approx(raw['Has Online delivery'].eq('Yes').mean()*100)
    high = raw[raw['Aggregate rating'].ge(4)]
    assert len(high)==1380
    assert results['high_rating_booking'].iloc[0].with_booking == high['Has Table booking'].eq('Yes').sum() ==287
    assert results['country_summary'].restaurants.sum() == len(raw)
    assert results['city_summary'].restaurants.sum() == len(raw)
    assert results['high_rating_booking'].iloc[0].booking_pct == pytest.approx(287/1380*100)
    expected = data.dropna(subset=['cuisines']).assign(cuisine=lambda d:d.cuisines.str.split(',')).explode('cuisine')
    expected.cuisine = expected.cuisine.str.strip()
    expected = expected.drop_duplicates(['restaurant_id','cuisine']).groupby('cuisine').size()
    got=results['cuisine_summary'].set_index('cuisine').restaurants
    pd.testing.assert_series_equal(got.sort_index(),expected[expected.ge(20)].sort_index(),check_names=False)


def test_cleaning_edges():
    raw = pd.read_csv(ROOT/'data/raw/zomato.csv',encoding='latin1').head(2)
    lookup = pd.read_excel(ROOT/'data/raw/Country-Code.xlsx')
    raw.loc[0,'Cuisines']=None
    raw.loc[0,'Aggregate rating']=0
    raw.loc[0,'Rating text']='Not rated'
    raw.loc[0,'Has Table booking']=' yes '
    clean, bridge, audit = clean_data(pd.concat([raw,raw.iloc[[0]]]),lookup)
    assert audit['exact_duplicates_removed']==1
    assert audit['missing_cuisines']==1
    assert clean.rating_for_analysis.isna().sum()==1
    assert bridge.restaurant_id.nunique()==1
    assert set(clean.country)=={'Philippines'}
    bad=raw.copy(); bad.loc[1,'Restaurant ID']=bad.loc[0,'Restaurant ID']
    with pytest.raises(ValueError,match='duplicate restaurant IDs'):
        clean_data(bad,lookup)
    bad=raw.copy(); bad.loc[0,'Has Online delivery']='Maybe'
    with pytest.raises(ValueError,match='Unknown yes/no'):
        clean_data(bad,lookup)
    bad=raw.copy(); bad.loc[0,'Aggregate rating']=9
    with pytest.raises(ValueError,match='Rating outside'):
        clean_data(bad,lookup)


def test_dashboard_default_and_filters(data):
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=40).run()
    assert not app.exception
    assert app.metric[0].value=='9,551'
    app.sidebar.selectbox[0].select('India').run()
    assert not app.exception
    assert app.metric[0].value==f'{data.country.eq("India").sum():,}'
    app.sidebar.checkbox[0].check().run()
    assert not app.exception
    assert app.metric[0].value==f'{(data.country.eq("India") & data.is_rated).sum():,}'
    app.sidebar.multiselect[0].select('New Delhi').run()
    app.sidebar.selectbox[1].select('Yes').run()
    expected = data[data.country.eq('India') & data.is_rated & data.city.eq('New Delhi') & data.has_online_delivery.eq('Yes')]
    assert app.metric[0].value==f'{len(expected):,}'
    app.sidebar.number_input[0].set_value(10000000).run()
    assert not app.exception
    assert any('No restaurants match' in x.value for x in app.info)


def test_quality_and_generated_assets():
    audit=json.loads((ROOT/'reports/data_quality.json').read_text())
    assert audit['missing_cuisines']==9
    assert audit['rating_status_disagreements']==0
    expected_figures = {'country_coverage', 'city_coverage', 'rating_distribution',
                        'cuisine_supply', 'service_ratings', 'india_price_ratings'}
    assert expected_figures <= {p.stem for p in (ROOT/'reports/figures').glob('*.png')}
    assert len(list((ROOT/'reports/tables').glob('*.csv')))==len(queries())
