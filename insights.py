import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
csv = ROOT / 'outputs' / 'county_summary.csv'
if not csv.exists():
    raise SystemExit('county_summary.csv not found; run analysis.py first')

df = pd.read_csv(csv)
# Keep counties with >0 PWA
df = df[df['No_PWA_2019']>0].copy()
# Products_per_PWA may be missing; compute if not present
if 'Products_per_PWA' not in df.columns or df['Products_per_PWA'].isnull().any():
    df['Products_per_PWA'] = df['Total_Products'] / df['No_PWA_2019']

mean_pp = df['Products_per_PWA'].mean()
median_pp = df['Products_per_PWA'].median()

# Identify top deficits (lowest products per PWA) and surpluses (highest)
low = df.sort_values('Products_per_PWA').head(10)[['County','No_PWA_2019','Total_Products','Products_per_PWA']]
high = df.sort_values('Products_per_PWA', ascending=False).head(10)[['County','No_PWA_2019','Total_Products','Products_per_PWA']]

# Choose a conservative target per person (policy choice) — change as needed
TARGET_PER_PERSON = 20

# Compute deficits/surplus relative to target
df['target_total'] = df['No_PWA_2019'] * TARGET_PER_PERSON
df['surplus_units'] = df['Total_Products'] - df['target_total']

# Surplus positive means excess supply; negative means deficit
surplus_total = df[df['surplus_units']>0]['surplus_units'].sum()
deficit_total = -df[df['surplus_units']<0]['surplus_units'].sum()

reallocatable = df[df['surplus_units']>0].sort_values('surplus_units', ascending=False)[['County','surplus_units']]
needs = df[df['surplus_units']<0].sort_values('surplus_units')[['County','surplus_units']]

out = ROOT / 'outputs' / 'insights.txt'
with out.open('w', encoding='utf-8') as f:
    f.write('National products-per-PWA mean: {:.2f}\n'.format(mean_pp))
    f.write('National products-per-PWA median: {:.2f}\n'.format(median_pp))
    f.write('\nTop 10 deficit counties (lowest products per PWA):\n')
    f.write(low.to_string(index=False))
    f.write('\n\nTop 10 surplus counties (highest products per PWA):\n')
    f.write(high.to_string(index=False))
    f.write('\n\nAssumed target per PWA: {} units\n'.format(TARGET_PER_PERSON))
    f.write('Total surplus units available: {}\n'.format(int(surplus_total)))
    f.write('Total deficit units needed: {}\n'.format(int(deficit_total)))
    f.write('\nCounts that can donate (surplus):\n')
    f.write(reallocatable.to_string(index=False))
    f.write('\n\nCounts with deficits (need units):\n')
    f.write(needs.to_string(index=False))

print('Insights written to', out)
print('Mean products-per-PWA:', mean_pp)
print('Median products-per-PWA:', median_pp)
print('Total surplus units:', int(surplus_total))
print('Total deficit units:', int(deficit_total))
