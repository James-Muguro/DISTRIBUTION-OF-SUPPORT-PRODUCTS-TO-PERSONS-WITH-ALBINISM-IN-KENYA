"""A minimal Streamlit prototype for reviewing transfer plans and picklists.
Run: streamlit run streamlit_app.py

The app allows adjusting donor buffer and re-running picklist generation (in-memory call) to preview impacts.
"""
import streamlit as st
from pathlib import Path
import pandas as pd
import generate_picklists

ROOT = Path(__file__).parent
OUT = ROOT / 'outputs'
TRANSFER_CSV = OUT / 'transfer_plan.csv'
PICK_DIR = OUT / 'picklists'

st.title('PWA Support Products — Transfer Review & Approval')
st.markdown('Adjust buffer percent, preview picklists, and approve transfers to export manifests.')

if not TRANSFER_CSV.exists():
    st.error('No transfer_plan.csv found. Run transfer_plan.py first.')
else:
    buffer = st.slider('Donor buffer percent', 0.0, 0.5, 0.1, step=0.01)
    if st.button('Generate picklists (preview)'):
        with st.spinner('Generating picklists...'):
            generate_picklists.main(buffer)
        st.success('Picklists generated in outputs/picklists')

    st.subheader('Planned transfers')
    trans = pd.read_csv(TRANSFER_CSV)
    trans['approved'] = False
    # display and allow per-row approval
    st.write('Select transfers to approve (tick rows)')
    selected = st.multiselect('Approve transfers (County donor -> County recipient)',
                              options=trans.index.to_list(),
                              format_func=lambda i: f"{trans.at[i,'from_county']} -> {trans.at[i,'to_county']} ({trans.at[i,'units']})")

    if st.button('Export approved manifests'):
        if not selected:
            st.warning('No transfers selected for approval.')
        else:
            approved = trans.loc[selected]
            # write approvals to outputs/approvals.csv
            approvals_path = OUT / 'approvals.csv'
            approved.to_csv(approvals_path, index=False)
            st.success(f'Wrote {len(approved)} approved transfers to {approvals_path}')

    st.subheader('Picklist summary (preview)')
    summary_file = OUT / 'picklist_summary.txt'
    if summary_file.exists():
        st.text(summary_file.read_text())
    else:
        st.info('No picklist summary available yet. Generate picklists to create it.')
