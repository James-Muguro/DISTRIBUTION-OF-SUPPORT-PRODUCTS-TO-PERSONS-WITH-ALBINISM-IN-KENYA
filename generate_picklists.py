"""generate_picklists.py
Map county-level transfers to donor facilities and produce per-donor picklists.
Outputs:
 - outputs/picklists/<donor_county>_picklist.csv
 - outputs/picklist_summary.txt

Default behavior:
 - Uses `outputs/transfer_plan.csv` produced by `transfer_plan.py`.
 - Uses original products CSV to get facility-level stock counts per product type.
 - Honors a donor buffer percent (default 10%): donors keep buffer% of their stock and only release the rest.
 - Allocates proportionally from donor facilities to satisfy transfer quantities.

Usage:
    python generate_picklists.py --buffer 0.1

"""
from pathlib import Path
import pandas as pd
import argparse

ROOT = Path(__file__).parent
OUT = ROOT / 'outputs'
OUT.mkdir(exist_ok=True)
PICK_DIR = OUT / 'picklists'
PICK_DIR.mkdir(exist_ok=True)

# Defaults
PRODUCTS_CSV = ROOT / 'distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv'
TRANSFER_CSV = OUT / 'transfer_plan.csv'

# Product columns we expect in the products CSV (guessed from file headers)
PRODUCT_COLS = [
    'Distibuted_Sunscreen_Lotions',
    'Distributed_Lip_Care_Products',
    'Distributed_After_Sun_Lotions',
    'Distributed_Protective_Clothings_Caps',
    'Distributed_Protective_Clothings_Long_sleeved_T-Shirts'
]

# possible inventory metadata columns (batch/lot/expiry)
META_KEYS = ['batch', 'lot', 'expiry', 'manufacture', 'mfg_date', 'exp_date']

def load_products(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # normalize columns safe
    df.columns = [c.strip() for c in df.columns]
    # Ensure County and Health centre exist
    if 'County' not in df.columns:
        raise SystemExit('products CSV missing County column')
    if 'Distribution_Centres_Hospitals/Health_Centres' in df.columns:
        df = df.rename(columns={'Distribution_Centres_Hospitals/Health_Centres': 'Facility'})
    if 'Facility' not in df.columns:
        # fallback to second column
        df.insert(1, 'Facility', df.iloc[:,1].astype(str))

    # Fill numeric product columns if present; else create zeros
    for pc in PRODUCT_COLS:
        if pc in df.columns:
            df[pc] = pd.to_numeric(df[pc].astype(str).str.replace(',', '', regex=False), errors='coerce').fillna(0).astype(int)
        else:
            df[pc] = 0

    df['County'] = df['County'].astype(str).str.upper().str.strip()
    df['Facility'] = df['Facility'].astype(str).str.strip()
    # detect metadata columns (case-insensitive)
    meta_cols = [c for c in df.columns if any(k in c.lower() for k in META_KEYS)]
    # keep meta columns if present; else none
    df['_meta_cols'] = ','.join(meta_cols) if meta_cols else ''
    return df


def allocate_from_facilities(donors_df: pd.DataFrame, donor_county: str, need_units: int, buffer_pct: float):
    """Allocate up to need_units from donor facilities in donor_county respecting buffer_pct.
    Allocation is proportional across product columns aggregated to units.
    Returns list of allocations: [{'facility':..., 'product':..., 'units':...}, ...]
    """
    df = donors_df[donors_df['County'] == donor_county].copy()
    if df.empty:
        return []
    # compute total available per facility (sum product cols)
    df['total_stock'] = df[PRODUCT_COLS].sum(axis=1)
    # apply buffer
    df['releasable'] = (df['total_stock'] * (1.0 - buffer_pct)).astype(int)
    total_releasable = df['releasable'].sum()
    to_give = min(total_releasable, need_units)
    if to_give <= 0:
        return []

    allocations = []
    # allocate proportional to each facility's releasable share
    df = df[df['releasable']>0].copy()
    df['share'] = df['releasable'] / df['releasable'].sum()
    df['allocate_total'] = (df['share'] * to_give).round().astype(int)

    # For each facility, allocate across product columns proportionally to their stock
    for _, row in df.iterrows():
        facility = row['Facility']
        alloc_total = int(row['allocate_total'])
        if alloc_total <= 0:
            continue
        prod_stocks = {pc: int(row[pc]) for pc in PRODUCT_COLS}
        prod_sum = sum(prod_stocks.values())
        if prod_sum == 0:
            # nothing to allocate (odd), skip
            continue
        # allocate per product proportionally but cap by releasable per-product
        for pc in PRODUCT_COLS:
            share = prod_stocks[pc] / prod_sum if prod_sum>0 else 0
            units = int(round(share * alloc_total))
            # ensure not exceeding stock and not giving below buffer at product level
            units = min(units, prod_stocks[pc])
            if units>0:
                # include metadata if available for the facility and product
                meta = {}
                if isinstance(row.get('_meta_cols', ''), str) and row.get('_meta_cols'):
                    for c in row['_meta_cols'].split(','):
                        if c:
                            meta[c] = row.get(c, '')
                allocations.append({'facility': facility, 'product': pc, 'units': units, 'meta': meta})
    # If rounding left unmet units, try to fill from largest remaining stocks
    allocated = sum(a['units'] for a in allocations)
    remaining = to_give - allocated
    if remaining>0:
        # sort facilities by remaining releasable stock and fill
        rem_list = []
        for _, row in df.iterrows():
            facility = row['Facility']
            for pc in PRODUCT_COLS:
                rem_stock = int(row[pc])
                if rem_stock>0:
                    rem_list.append((facility, pc, rem_stock))
        rem_list = sorted(rem_list, key=lambda x: x[2], reverse=True)
        idx = 0
        while remaining>0 and idx < len(rem_list):
            facility, pc, qty = rem_list[idx]
            give = min(qty, remaining)
            # try to include metadata if available
            meta = {}
            row = df[df['Facility']==facility]
            if not row.empty and row.iloc[0].get('_meta_cols'):
                for c in row.iloc[0]['_meta_cols'].split(','):
                    if c:
                        meta[c] = row.iloc[0].get(c, '')
            allocations.append({'facility': facility, 'product': pc, 'units': give, 'meta': meta})
            remaining -= give
            idx += 1
    return allocations


def main(buffer_pct: float):
    products = load_products(PRODUCTS_CSV)
    if not TRANSFER_CSV.exists():
        raise SystemExit('transfer_plan.csv not found; run transfer_plan.py first')
    transfers = pd.read_csv(TRANSFER_CSV)

    # prepare donors facilities dataframe
    donors_df = products.copy()
    # normalize county names
    donors_df['County'] = donors_df['County'].str.upper().str.strip()

    final_rows = []
    for _, t in transfers.iterrows():
        donor = t['from_county']
        recipient = t['to_county']
        units = int(t['units'])
        if donor == 'UNMET':
            final_rows.append({'from_county': donor, 'to_county': recipient, 'facility': '', 'product': '', 'units': units})
            continue
        allocations = allocate_from_facilities(donors_df, donor, units, buffer_pct)
        if not allocations:
            final_rows.append({'from_county': donor, 'to_county': recipient, 'facility': '', 'product': '', 'units': 0})
            continue
        for a in allocations:
            meta_fields = a.get('meta', {})
            # flatten meta into a string for CSV
            meta_str = '; '.join([f"{k}={v}" for k, v in meta_fields.items()]) if meta_fields else ''
            final_rows.append({'from_county': donor, 'to_county': recipient, 'facility': a['facility'], 'product': a['product'], 'units': a['units'], 'meta': meta_str})

    pick_df = pd.DataFrame(final_rows)
    pick_df.to_csv(PICK_DIR / 'transfer_picklists_combined.csv', index=False)

    # produce simple printable HTML picklists per donor with totals and readable product names
    for donor, sub in pick_df[pick_df['from_county']!='UNMET'].groupby('from_county'):
        html = []
        html.append(f"<h1>Picklist: {donor}</h1>")
        html.append(f"<p>Buffer percent applied: {buffer_pct*100:.1f}%</p>")
        html.append(sub.to_html(index=False))
        (PICK_DIR / f"{donor}_picklist.html").write_text('\n'.join(html), encoding='utf-8')

    # also write per-donor picklists
    for donor, sub in pick_df[pick_df['from_county']!='UNMET'].groupby('from_county'):
        sub.to_csv(PICK_DIR / f"{donor}_picklist.csv", index=False)

    # write summary
    by_donor = pick_df.groupby('from_county')['units'].sum().reset_index().sort_values('units', ascending=False)
    by_recipient = pick_df.groupby('to_county')['units'].sum().reset_index().sort_values('units', ascending=False)
    out_txt = OUT / 'picklist_summary.txt'
    with out_txt.open('w', encoding='utf-8') as f:
        f.write('Picklist summary\n')
        f.write('=================\n')
        f.write(f'Buffer percent applied to donors: {buffer_pct*100:.1f}%\n')
        f.write('\nTop donors (units allocated)\n')
        f.write(by_donor.to_string(index=False))
        f.write('\n\nTop recipients (units allocated)\n')
        f.write(by_recipient.to_string(index=False))

    print('Wrote combined picklists to', PICK_DIR / 'transfer_picklists_combined.csv')
    print('Wrote per-donor picklists to', PICK_DIR)
    print('Wrote picklist summary to', out_txt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--buffer', type=float, default=0.1, help='Donor buffer percent (0-1) to keep in donor stock')
    args = parser.parse_args()
    main(args.buffer)
