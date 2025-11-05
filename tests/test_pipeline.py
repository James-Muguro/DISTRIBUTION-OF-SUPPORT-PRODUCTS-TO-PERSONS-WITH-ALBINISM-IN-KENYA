import os
from pathlib import Path
from data_processing import prepare_products, prepare_population

ROOT = Path(__file__).parent.parent
prod = ROOT / 'distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv'
pop = ROOT / 'distribution-of-persons-with-albinism-by-sex1-area-of-residence-county-and-sub-county-2019-censu (1).csv'


def test_prepare_runs():
    p = prepare_products(prod)
    q = prepare_population(pop)
    assert not p.empty
    assert not q.empty
    # run analysis module to ensure no runtime errors
    from analysis import compute_and_report
    compute_and_report(p, q)
    assert (ROOT / 'outputs' / 'county_summary.csv').exists()
