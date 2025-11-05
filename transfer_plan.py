import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent
in_csv = ROOT / 'outputs' / 'county_summary.csv'
out_csv = ROOT / 'outputs' / 'transfer_plan.csv'
out_txt = ROOT / 'outputs' / 'transfer_summary.txt'

if not in_csv.exists():
    raise SystemExit('county_summary.csv not found; run analysis.py first')

TARGET_PER_PERSON = 20

df = pd.read_csv(in_csv)
# compute surplus units as in insights
if 'surplus_units' not in df.columns:
    df['No_PWA_2019'] = df['No_PWA_2019'].fillna(0).astype(int)
    df['target_total'] = df['No_PWA_2019'] * TARGET_PER_PERSON
    df['surplus_units'] = df['Total_Products'] - df['target_total']
else:
    # ensure numeric
    df['surplus_units'] = pd.to_numeric(df['surplus_units'], errors='coerce').fillna(0).astype(int)

# donors and recipients
donors = df[df['surplus_units']>0][['County','surplus_units']].copy()
recips = df[df['surplus_units']<0][['County','surplus_units']].copy()
recips['need'] = -recips['surplus_units']

# sort donors by largest surplus, recipients by largest need
donors = donors.sort_values('surplus_units', ascending=False).reset_index(drop=True)
recips = recips.sort_values('need', ascending=False).reset_index(drop=True)

transfers = []
# Greedy allocation
for r_idx, r in recips.iterrows():
    need = int(r['need'])
    if need <= 0:
        continue
    for d_idx in donors.index:
        donor_qty = int(donors.at[d_idx,'surplus_units'])
        if donor_qty <= 0:
            continue
        give = min(donor_qty, need)
        if give <= 0:
            continue
        transfers.append({'from_county': donors.at[d_idx,'County'], 'to_county': r['County'], 'units': give})
        donors.at[d_idx,'surplus_units'] = donor_qty - give
        need -= give
        if need <= 0:
            break
    if need>0:
        # unmet need remains (not expected here because total surplus >> deficit)
        transfers.append({'from_county': 'UNMET', 'to_county': r['County'], 'units': need})

# Save transfer plan
trans_df = pd.DataFrame(transfers)
trans_df.to_csv(out_csv, index=False)

# Summaries
by_donor = trans_df.groupby('from_county')['units'].sum().reset_index().sort_values('units', ascending=False)
by_recipient = trans_df.groupby('to_county')['units'].sum().reset_index().sort_values('units', ascending=False)

with out_txt.open('w', encoding='utf-8') as f:
    f.write('Transfer plan summary\n')
    f.write('=====================\n')
    f.write(f'Total donors: {len(donors)}\n')
    f.write(f'Total recipients: {len(recips)}\n')
    f.write('\nTop donors (by units donated)\n')
    f.write(by_donor.to_string(index=False))
    f.write('\n\nTop recipients (by units requested)\n')
    f.write(by_recipient.to_string(index=False))

print('Wrote', out_csv)
print('Wrote', out_txt)
print('\nTop 10 transfers:')
print(trans_df.head(10).to_string(index=False))
