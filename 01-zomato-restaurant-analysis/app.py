"""Interactive dashboard: streamlit run app.py."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='Zomato | Restaurant Explorer', page_icon='🍽️', layout='wide')
st.title('Zomato Restaurant Explorer')
st.caption('Historical restaurant listings • Coverage, ratings and service availability')


@st.cache_data
def load_data(file_path, modified):
    return pd.read_csv(file_path)


path = ROOT/'data/processed/zomato_cleaned.csv'
if not path.exists():
    st.error('Run python -m src.pipeline from the project folder first.')
    st.stop()
df = load_data(str(path), path.stat().st_mtime_ns)
with st.sidebar:
    st.header('Explore the dataset')
    country = st.selectbox('Country', ['All countries']+sorted(df.country.unique()))
    scope = df if country == 'All countries' else df[df.country.eq(country)]
    cities = st.multiselect('Cities (empty = all)',sorted(scope.city.unique()))
    tiers = st.multiselect('Price tiers (empty = all)', [1,2,3,4])
    service = st.selectbox('Online delivery', ['Any','Yes','No'])
    booking = st.selectbox('Table booking', ['Any','Yes','No'])
    rated_only = st.checkbox('Rated restaurants only')
    min_votes = st.number_input('Minimum votes', min_value=0,value=0,step=10)
    st.caption('Filters apply to all metrics, charts and downloaded rows.')
filtered = scope.copy()
if cities:
    filtered = filtered[filtered.city.isin(cities)]
if tiers:
    filtered = filtered[filtered.price_range.isin(tiers)]
if service != 'Any':
    filtered = filtered[filtered.has_online_delivery.eq(service)]
if booking != 'Any':
    filtered = filtered[filtered.has_table_booking.eq(booking)]
if rated_only:
    filtered = filtered[filtered.is_rated]
filtered = filtered[filtered.votes.ge(min_votes)]
if filtered.empty:
    st.info('No restaurants match these filters. Broaden your selection.')
    st.stop()

cols = st.columns(4)
cols[0].metric('Restaurants',f'{len(filtered):,}')
mean = filtered.rating_for_analysis.mean()
cols[1].metric('Mean rating · rated only', '—' if pd.isna(mean) else f'{mean:.2f} / 5')
cols[2].metric('Online delivery', f'{filtered.has_online_delivery.eq("Yes").mean()*100:.1f}%')
cols[3].metric('Table booking', f'{filtered.has_table_booking.eq("Yes").mean()*100:.1f}%')
st.caption(f'{filtered.is_rated.sum():,} rated records; {(~filtered.is_rated).sum():,} unrated records. Service percentages use all filtered restaurants.')
overview, ratings, records, method = st.tabs(['Coverage & cuisines','Ratings & costs','Restaurant data','Methodology'])
with overview:
    left,right = st.columns(2)
    counts = filtered.groupby(['country','city']).size().reset_index(name='Restaurants').nlargest(12,'Restaurants')
    counts['Location'] = counts.city+', '+counts.country
    left.plotly_chart(px.bar(counts.sort_values('Restaurants'),x='Restaurants',y='Location',orientation='h',
                            title='Most represented locations',color_discrete_sequence=['#DF4D55']),use_container_width=True)
    cuisine = filtered.cuisines.dropna().str.split(',').explode().str.strip().value_counts().head(12).rename_axis('Cuisine').reset_index(name='Restaurants')
    right.plotly_chart(px.bar(cuisine.sort_values('Restaurants'),x='Restaurants',y='Cuisine',orientation='h',
                             title='Listed cuisine supply',color_discrete_sequence=['#248B8B']),use_container_width=True)
    st.caption('A restaurant can list several cuisines. Counts are not measures of demand or sales.')
with ratings:
    left,right = st.columns(2)
    rated = filtered[filtered.is_rated]
    if rated.empty:
        st.info('The selection contains no rated restaurants.')
    else:
        left.plotly_chart(px.histogram(rated,x='rating_for_analysis',nbins=25,range_x=[0,5],title='Ratings among rated restaurants',
                                      labels={'rating_for_analysis':'Rating / 5'},color_discrete_sequence=['#248B8B']),use_container_width=True)
        comparison = filtered.groupby('has_table_booking').rating_for_analysis.agg(['mean','count']).reset_index()
        right.plotly_chart(px.bar(comparison,x='has_table_booking',y='mean',text='count',range_y=[0,5],
                                  title='Table booking and mean rating',labels={'has_table_booking':'Table booking','mean':'Mean rating','count':'Rated records'},
                                  color_discrete_sequence=['#DF4D55']),use_container_width=True)
        st.caption('Bar labels show rated sample sizes. Service comparisons are descriptive and confounded by location, price tier and other factors.')
    if country == 'All countries':
        st.info('Select a country to view costs in its recorded currency. Currency labels may contain source errors.')
    else:
        positive = filtered[filtered.average_cost_for_two.gt(0)]
        costs = positive.groupby('currency').average_cost_for_two.agg(['count','median','min','max'])
        st.subheader('Cost for two by recorded currency')
        st.dataframe(costs,use_container_width=True)
        st.caption('Zero costs excluded. No currency conversion; source currency labels are unverified.')
with records:
    fields = ['restaurant_name','country','city','cuisines','rating_for_analysis','votes','price_range','average_cost_for_two','currency','has_online_delivery','has_table_booking']
    st.dataframe(filtered[fields].sort_values('votes',ascending=False),hide_index=True,use_container_width=True)
    st.download_button('Download filtered records',filtered.to_csv(index=False).encode('utf-8'),file_name='zomato_filtered.csv',mime='text/csv')
with method:
    st.markdown('''**Unit:** one restaurant listing, identified by restaurant ID.

**Ratings:** source zero ratings or “Not rated” entries are excluded from averages. Each rated restaurant has equal weight; votes are not sales.

**Coverage:** this is a historical convenience sample dominated by India, not a current or representative census. No collection date was supplied.

**Costs:** kept in their original recorded currencies. Suspicious currency labels and text encoding artefacts are preserved and documented. No cross-currency averages are calculated.

**Interpretation:** associations do not establish causality. Cuisine counts overlap across categories. Missing cuisines are omitted from cuisine charts only.

See README.md, reports/data_quality.json and sql/zomato_analysis.sql for reproducible definitions and outputs.''')
