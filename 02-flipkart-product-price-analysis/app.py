"""Run with: python -m streamlit run app.py"""
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Flipkart pricing landscape', page_icon='📊', layout='wide')

@st.cache_data
def load_data(stamp):
    # The modification time invalidates the cache after a pipeline refresh.
    frame = pd.read_csv(ROOT / 'data/processed/listings.csv.gz', keep_default_na=False)
    for column in ['selling_price', 'retail_price', 'rating', 'discount_pct']:
        frame[column] = pd.to_numeric(frame[column], errors='coerce')
    outliers = pd.read_csv(ROOT / 'reports/tables/outliers.csv')
    return frame, outliers

st.title('Flipkart pricing landscape')
st.caption('Interactive SQL EDA · historical 2015–2016 listings · prices in INR')
snapshot = ROOT / 'data/processed/listings.csv.gz'
if not snapshot.exists():
    st.info('Build the analysis data first, then refresh this page.')
    st.code('python -m src.download\npython -m src.pipeline', language='bash')
    st.stop()
outlier_path = ROOT / 'reports/tables/outliers.csv'
if not outlier_path.exists():
    st.error('The outlier results are missing. Run python -m src.pipeline to rebuild the report.')
    st.stop()
data, outliers = load_data((snapshot.stat().st_mtime_ns, outlier_path.stat().st_mtime_ns))

st.sidebar.header('Explore listings')
categories = st.sidebar.multiselect('Categories', sorted(data.category.unique()), key='categories')
category_rows = data[data.category.isin(categories)] if categories else data
brands = st.sidebar.multiselect('Brands', sorted(category_rows.brand.unique()), key='brands')
search = st.sidebar.text_input('Search product name', key='search')
limit_price = st.sidebar.checkbox('Apply selling-price range', key='limit_price')
cap = max(1.0, float(data.loc[data.valid_price, 'selling_price'].max()))
price_range = st.sidebar.slider('Selling price (INR)', 0.0, cap, (0.0, cap), disabled=not limit_price, key='price_range')
st.sidebar.caption('Empty category or brand selection means all. A price range excludes invalid prices.')
filtered = category_rows.copy()
if brands:
    filtered = filtered[filtered.brand.isin(brands)]
if search:
    filtered = filtered[filtered.product_name.str.contains(search, case=False, regex=False, na=False)]
if limit_price:
    filtered = filtered[filtered.valid_price & filtered.selling_price.between(*price_range)]
st.caption(f'Showing {len(filtered):,} of {len(data):,} listings. All metrics and charts below reflect these filters.')
if filtered.empty:
    st.warning('No listings match these filters. Clear a category, brand, search, or price filter to continue.')
    st.stop()

prices = filtered.loc[filtered.valid_price, 'selling_price']
discounts = filtered.discount_pct.dropna()
metrics = st.columns(4)
metrics[0].metric('Listings', f'{len(filtered):,}')
metrics[1].metric('Median selling price', f'₹{prices.median():,.0f}' if len(prices) else 'N/A')
metrics[2].metric('Median discount', f'{discounts.median():.1f}%' if len(discounts) else 'N/A')
metrics[3].metric('Rating coverage', f'{filtered.rating.notna().mean()*100:.1f}%')
st.caption(f'{len(prices):,} valid prices · {len(discounts):,} valid discounts · {filtered.rating.notna().sum():,} rated listings. Ratings describe a sparse, self-selected subset.')

with duckdb.connect() as con:
    con.register('selection', filtered)
    benchmarks = con.execute('''SELECT category, count(*) AS listings,
        count(*) FILTER (WHERE valid_price) AS valid_prices,
        quantile_cont(selling_price, .25) FILTER (WHERE valid_price) AS p25,
        median(selling_price) FILTER (WHERE valid_price) AS median_price,
        quantile_cont(selling_price, .75) FILTER (WHERE valid_price) AS p75,
        quantile_cont(selling_price, .90) FILTER (WHERE valid_price) AS p90,
        count(discount_pct) AS valid_discounts, avg(discount_pct) AS mean_discount_pct
        FROM selection GROUP BY category ORDER BY listings DESC, category''').df()
    brand_counts = con.execute('''SELECT brand, count(*) AS listings,
        100.0*count(*)/sum(count(*)) OVER () AS selection_share_pct
        FROM selection GROUP BY brand ORDER BY listings DESC, brand''').df()

overview, review, listings, notes = st.tabs(['Overview', 'Outlier review', 'Browse listings', 'Methodology'])
with overview:
    left, right = st.columns(2)
    with left:
        st.subheader('Largest categories')
        st.bar_chart(benchmarks.head(10), x='category', y='listings', color='#167d9a')
    with right:
        st.subheader('Average listed discounts')
        eligible = benchmarks[(benchmarks.valid_discounts >= 30) & (benchmarks.category != 'Unknown')]
        if eligible.empty:
            st.info('No selected category has 30 valid discount observations.')
        else:
            st.bar_chart(eligible.nlargest(10, 'mean_discount_pct'), x='category', y='mean_discount_pct', color='#ad633c')
        st.caption('At least 30 valid discounts per displayed category. Each listing receives equal weight.')
    st.subheader('Category price benchmarks')
    st.dataframe(benchmarks, hide_index=True, width='stretch')
    st.subheader('Brand representation')
    st.bar_chart(brand_counts.head(10), x='brand', y='listings', color='#167d9a')
    st.caption('Includes Unknown brands. Shares use all filtered listings, not sales.')
    st.dataframe(brand_counts.head(20), hide_index=True, width='stretch')
with review:
    st.subheader('Listings for manual review')
    st.info('Flags use the full dataset category benchmarks. Filters narrow the queue but do not recalculate its fences. A flag is not proof of a pricing error.')
    queue = outliers[outliers.listing_id.isin(filtered.listing_id)]
    flag = st.selectbox('Outlier direction', ['All', 'High', 'Low'], key='flag')
    if flag != 'All':
        queue = queue[queue.flag == flag]
    st.metric('Review candidates', f'{len(queue):,}')
    columns = ['product_name','category','brand','selling_price','lower_fence','upper_fence','flag','product_url']
    st.dataframe(queue[columns], hide_index=True, width='stretch')
    st.download_button('Download review queue', queue.to_csv(index=False).encode(), 'flipkart_review_queue.csv', 'text/csv')
with listings:
    st.subheader('Filtered listings')
    columns = ['product_name','category','brand','selling_price','retail_price','discount_pct','rating','valid_price']
    st.dataframe(filtered[columns], hide_index=True, width='stretch')
    st.download_button('Download filtered listings', filtered.to_csv(index=False).encode(), 'flipkart_filtered_listings.csv', 'text/csv')
with notes:
    st.markdown('''Prices and discount statistics use valid observations only. Category percentiles are recalculated for the filtered selection. Outlier flags remain anchored to the full dataset: groups need at least 30 positive finite selling prices and a nonzero IQR, with fences at Q1 − 1.5 × IQR and Q3 + 1.5 × IQR.

The sample is historical and its category labels can be noisy. Listings do not measure sales, market share, demand, or profitability. Ratings cover only a small subset. Validate product type, variant, bundle, and units before acting on an outlier.

Source: [PromptCloud / Kaggle](https://www.kaggle.com/datasets/PromptCloudHQ/flipkart-products). Dataset-derived outputs: CC BY-SA 4.0. See DATA_LICENSE.md and reports/data_dictionary.md.''')
st.caption('SQL calculations: DuckDB · Display: Streamlit · Rebuild data with python -m src.pipeline')
