import pandas as pd
from generate_picklists import allocate_from_facilities, PRODUCT_COLS


def make_donors_df():
    # simple synthetic donor facilities in COUNTY X
    data = [
        {'County':'TESTCOUNTY','Facility':'F1','Distibuted_Sunscreen_Lotions':100,'Distributed_Lip_Care_Products':50,'Distributed_After_Sun_Lotions':50,'Distributed_Protective_Clothings_Caps':20,'Distributed_Protective_Clothings_Long_sleeved_T-Shirts':30},
        {'County':'TESTCOUNTY','Facility':'F2','Distibuted_Sunscreen_Lotions':200,'Distributed_Lip_Care_Products':100,'Distributed_After_Sun_Lotions':100,'Distributed_Protective_Clothings_Caps':40,'Distributed_Protective_Clothings_Long_sleeved_T-Shirts':60},
    ]
    return pd.DataFrame(data)


def test_allocate_basic():
    donors = make_donors_df()
    # need 300 units; buffer 10% => releasable = 90% of total stocks
    allocations = allocate_from_facilities(donors, 'TESTCOUNTY', 300, 0.1)
    total_alloc = sum(a['units'] for a in allocations)
    # donors total stock = (100+50+50+20+30)=250 and (200+100+100+40+60)=500 => total 750
    # releasable = 90% * 750 = 675 -> can satisfy 300
    assert total_alloc == 300
    # allocations should reference known facilities
    facilities = set(a['facility'] for a in allocations)
    assert facilities.issubset({'F1','F2'})
