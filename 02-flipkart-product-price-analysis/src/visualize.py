"""Reproducible EDA charts from SQL query outputs."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def plots(results, folder):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.spines.left': False, 'figure.facecolor': '#ffffff',
                         'axes.labelcolor': '#334155', 'text.color': '#14283e'})
    cats = results['categories']
    comparable = cats[(cats.priced_listings >= 30) & (cats.category != 'Unknown')]
    def bars(df, x, y, title, xlabel, name, color='#167d9a'):
        fig, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
        ax.barh(df[y], df[x], color=color, height=.65)
        ax.set(title=title, xlabel=xlabel)
        ax.grid(axis='x', alpha=.15)
        ax.set_axisbelow(True)
        fig.savefig(folder / name, dpi=160)
        plt.close(fig)
    bars(cats.head(10).iloc[::-1], 'listings', 'category', 'Where the listings are', 'Number of listings', 'category_volume.png')
    d = comparable[comparable.discount_listings >= 30].nlargest(10, 'mean_discount_pct').iloc[::-1]
    bars(d, 'mean_discount_pct', 'category', 'Deepest average discounts', 'Mean discount (%) · at least 30 valid discounts per category', 'discounts.png', '#ad633c')
    d = comparable.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
    ax.hlines(d.category, d.p25, d.p75, color='#9bccd6', linewidth=9, label='25th–75th percentile')
    ax.scatter(d.p50, d.category, color='#126d88', s=45, zorder=3, label='Median')
    ax.set(xlabel='Selling price (INR)', title='Typical price ranges · 10 largest eligible categories')
    ax.legend(loc='lower right', frameon=False)
    ax.grid(axis='x', alpha=.15)
    fig.savefig(folder / 'price_ranges.png', dpi=160)
    plt.close(fig)
    b = results['brands'].query("brand != 'Unknown'").groupby('brand', as_index=False).listings.sum().nlargest(10,'listings').iloc[::-1]
    bars(b, 'listings', 'brand', 'Most represented known brands', 'Number of listings · unknown brands excluded', 'brands.png')

