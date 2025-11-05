from pathlib import Path
from data_processing import prepare_products, prepare_population

ROOT = Path(__file__).parent.parent


def test_prepare_products_and_population():
    prod_file = ROOT / 'distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv'
    pop_file = ROOT / 'distribution-of-persons-with-albinism-by-sex1-area-of-residence-county-and-sub-county-2019-censu (1).csv'
    assert prod_file.exists(), 'products CSV missing'
    assert pop_file.exists(), 'population CSV missing'

    p = prepare_products(prod_file)
    q = prepare_population(pop_file)

    # Basic sanity checks
    assert not p.empty
    assert not q.empty
    assert 'County' in p.columns
    assert 'County' in q.columns
