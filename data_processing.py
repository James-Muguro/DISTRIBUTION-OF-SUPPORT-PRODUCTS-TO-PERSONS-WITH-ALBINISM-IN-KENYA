"""data_processing.py
Utilities to load, clean and save the CSV datasets used in the project.
Produces cleaned CSVs in a `data/clean` folder.
"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)


def load_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    # read with engine and low_memory to be robust to irregular csvs
    return pd.read_csv(path, dtype=str, encoding='utf-8', low_memory=False)


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    # Rename columns to canonical names
    cols = {c: c.strip() for c in df.columns}
    df = df.rename(columns=cols)

    # Standardize county name
    if 'County' in df.columns:
        df['County'] = df['County'].str.upper().str.strip()

    # Numeric columns: coerce to numeric, fill NaN with 0
    numeric_cols = [c for c in df.columns if any(k in c.lower() for k in ['number', 'no_', 'distributed', 'distributed_', 'sunsreen', 'sunscreen', 'objectid']) or df[c].dtype == object and df[c].str.replace(',', '', regex=False).str.isnumeric().any()]
    for col in numeric_cols:
        # remove commas and coerce
        df[col] = pd.to_numeric(df[col].str.replace(',', '', regex=False), errors='coerce').fillna(0).astype(int)

    # Drop obvious metadata columns if present
    for drop_col in ['Financial_Year_Ending', 'Centroid_x', 'Centoid_Y', 'OBJECTID']:
        if drop_col in df.columns:
            df = df.drop(columns=[drop_col])

    return df


def clean_population(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # Attempt to find county and PWA columns
    # Strip column names
    df.columns = [c.strip() for c in df.columns]
    # Normalize the main county column
    possible_county_cols = [c for c in df.columns if 'county' in c.lower() or 'sub county' in c.lower() or 'county/sub' in c.lower()]
    county_col = possible_county_cols[0] if possible_county_cols else df.columns[0]
    df = df.rename(columns={county_col: 'County'})
    df['County'] = df['County'].astype(str).str.upper().str.strip()

    # Attempt to locate PWA column (persons with albinism)
    pwa_cols = [c for c in df.columns if 'albin' in c.lower() or 'pwa' in c.lower() or 'persons with' in c.lower()]
    if pwa_cols:
        pwa_col = pwa_cols[0]
        # Clean numbers and convert
        df[pwa_col] = df[pwa_col].astype(str).str.replace(',', '', regex=False).replace({'-': '0', '': '0'}).fillna('0')
        df[pwa_col] = pd.to_numeric(df[pwa_col], errors='coerce').fillna(0).astype(int)
        df = df.rename(columns={pwa_col: 'No_PWA_2019'})
    else:
        # fallback: add a zero column
        df['No_PWA_2019'] = 0

    return df


def save_clean(df: pd.DataFrame, name: str) -> Path:
    out = CLEAN_DIR / name
    df.to_csv(out, index=False)
    return out


def prepare_products(path) -> pd.DataFrame:
    raw = load_csv(path)
    cleaned = clean_products(raw)
    save_clean(cleaned, 'clean_products.csv')
    return cleaned


def prepare_population(path) -> pd.DataFrame:
    raw = load_csv(path)
    cleaned = clean_population(raw)
    save_clean(cleaned, 'clean_population.csv')
    return cleaned


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Prepare and clean CSV datasets')
    parser.add_argument('--products', default='distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv')
    parser.add_argument('--population', default='distribution-of-persons-with-albinism-by-sex1-area-of-residence-county-and-sub-county-2019-censu (1).csv')
    args = parser.parse_args()

    print('Preparing products...')
    p = prepare_products(Path(args.products))
    print('Products cleaned rows:', len(p))

    print('Preparing population...')
    q = prepare_population(Path(args.population))
    print('Population cleaned rows:', len(q))
