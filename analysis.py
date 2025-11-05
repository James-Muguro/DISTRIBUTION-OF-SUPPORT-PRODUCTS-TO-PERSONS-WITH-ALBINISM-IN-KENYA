"""analysis.py
Produces high-level metrics and a concise HTML summary for decision makers.
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from data_processing import prepare_products, prepare_population

ROOT = Path(__file__).parent
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)


def compute_and_report(products_df: pd.DataFrame, pop_df: pd.DataFrame):
    # Ensure County column exists
    if 'County' in products_df.columns:
        products_df['County'] = products_df['County'].str.upper().str.strip()
    # Aggregate products to county
    numeric_cols = [c for c in products_df.columns if c != 'County' and products_df[c].dtype in ['int64', 'int32', 'float64']]
    county_products = products_df.groupby('County')[numeric_cols].sum().reset_index()

    # Merge with population PWA counts
    pop_sub = pop_df[['County', 'No_PWA_2019']].drop_duplicates('County')
    merged = county_products.merge(pop_sub, on='County', how='left')
    merged['No_PWA_2019'] = merged['No_PWA_2019'].fillna(0).astype(int)

    # Total products per county
    merged['Total_Products'] = merged[numeric_cols].sum(axis=1)
    # Products per PWA (avoid division by zero)
    merged['Products_per_PWA'] = merged.apply(lambda r: r['Total_Products'] / r['No_PWA_2019'] if r['No_PWA_2019']>0 else None, axis=1)

    # Key summaries
    total_products = merged['Total_Products'].sum()
    total_pwa_2018 = products_df['Number_Of_Registered_Persons_With_Albinism'].astype(float).sum() if 'Number_Of_Registered_Persons_With_Albinism' in products_df.columns else None
    total_pwa_2019 = merged['No_PWA_2019'].sum()

    top5_by_pwa = merged.sort_values('No_PWA_2019', ascending=False).head(5)[['County','No_PWA_2019']]
    top5_by_products = merged.sort_values('Total_Products', ascending=False).head(5)[['County','Total_Products']]

    # Save merged table
    merged.to_csv(OUT / 'county_summary.csv', index=False)

    # Simple bar chart: top 10 counties by Total_Products
    top10 = merged.sort_values('Total_Products', ascending=False).head(10)
    ax = top10.plot.bar(x='County', y='Total_Products', legend=False, figsize=(10,5), rot=45)
    ax.set_ylabel('Total Products')
    plt.tight_layout()
    plt.savefig(OUT / 'top10_total_products.png', dpi=200)
    plt.close()

    # Render a compact HTML summary
    html = []
    html.append(f"<h1>Distribution Summary</h1>")
    html.append(f"<p>Total products distributed (sum): <b>{int(total_products)}</b></p>")
    if total_pwa_2019 is not None:
        html.append(f"<p>Total persons with albinism (2019 dataset): <b>{int(total_pwa_2019)}</b></p>")
    if total_pwa_2018 is not None:
        html.append(f"<p>Total persons registered (2018): <b>{int(total_pwa_2018)}</b></p>")
    html.append('<h2>Top 5 counties by PWA (2019)</h2>')
    html.append(top5_by_pwa.to_html(index=False))
    html.append('<h2>Top 5 counties by total products</h2>')
    html.append(top5_by_products.to_html(index=False))
    html.append('<h2>Top 10 by products (chart)</h2>')
    html.append('<img src="top10_total_products.png" alt="top10"/>')

    (OUT / 'summary.html').write_text('\n'.join(html), encoding='utf-8')
    print('Report saved to outputs/summary.html')


if __name__ == '__main__':
    # Default filenames (assume files live in repo root)
    p = prepare_products('distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv')
    q = prepare_population('distribution-of-persons-with-albinism-by-sex1-area-of-residence-county-and-sub-county-2019-censu (1).csv')
    compute_and_report(p, q)
