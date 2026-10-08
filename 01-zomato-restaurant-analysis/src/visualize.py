"""Static figures regenerated from the cleaned records."""
from pathlib import Path
import os
import tempfile
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir())/'zomato-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def make_figures(df, bridge):
    out = ROOT/'reports/figures'
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False, 'axes.titleweight':'bold', 'figure.facecolor':'white'})
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(out/f'{name}.png', dpi=160, bbox_inches='tight')
        plt.close(fig)
    def barh(series, title, xlabel, name):
        fig, ax = plt.subplots(figsize=(10,6))
        series.sort_values().plot.barh(ax=ax, color='#DF4D55')
        ax.set(title=title, xlabel=xlabel, ylabel='')
        ax.grid(axis='x', alpha=.15)
        save(fig,name)
    barh(df.country.value_counts().head(10), 'Dataset coverage is concentrated in India', 'Restaurant records', 'country_coverage')
    barh(df.groupby(['country','city']).size().sort_values(ascending=False).head(10).rename(index=lambda x:x),
         'Ten most represented country–city pairs', 'Restaurant records', 'city_coverage')
    fig, ax = plt.subplots(figsize=(10,5))
    ax.hist(df.rating_for_analysis.dropna(), bins=np.arange(0,5.21,.2), color='#248B8B', edgecolor='white')
    ax.set(title='Rating distribution among rated restaurants', xlabel='Aggregate rating / 5', ylabel='Restaurant records', xlim=(0,5))
    ax.text(.02,.95,f'Unrated records excluded: {(~df.is_rated).sum():,}',transform=ax.transAxes,va='top')
    save(fig,'rating_distribution')
    barh(bridge.cuisine.value_counts().head(12), 'Most frequently listed cuisines', 'Restaurants listing cuisine (multiple cuisines per restaurant)', 'cuisine_supply')
    fig, axes = plt.subplots(1,2,figsize=(12,5),sharey=True)
    for ax, col, title in zip(axes,['has_table_booking','has_online_delivery'],['Table booking','Online delivery']):
        groups = df.groupby(col).rating_for_analysis.agg(['mean','count']).reindex(['No','Yes'])
        ax.bar(groups.index,groups['mean'],color=['#97A8B5','#DF4D55'])
        for i, row in enumerate(groups.itertuples()):
            ax.text(i,row.mean+.12,f'{row.mean:.2f}\nn={row.count:,}',ha='center',fontsize=10)
        ax.set(title=title,ylim=(0,5),ylabel='Mean rating among rated records')
    fig.suptitle('Service availability and ratings: association, not causation',fontsize=14)
    save(fig,'service_ratings')
    india = df[df.country.eq('India') & df.is_rated]
    fig, ax = plt.subplots(figsize=(10,5))
    ax.boxplot([india.loc[india.price_range.eq(p),'rating_for_analysis'] for p in range(1,5)],tick_labels=['1','2','3','4'],patch_artist=True,
               boxprops={'facecolor':'#99D3CF'},medianprops={'color':'#142B3A'})
    ax.set(title='India: rating distribution by source price tier',xlabel='Price range (ordinal tiers)',ylabel='Aggregate rating / 5',ylim=(0,5))
    save(fig,'india_price_ratings')
