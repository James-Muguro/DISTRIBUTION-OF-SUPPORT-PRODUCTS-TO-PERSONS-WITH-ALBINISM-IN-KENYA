"""Run generate_picklists with multiple buffer percentages and capture summary stats.
Produces: outputs/sensitivity_summary.csv
"""
from pathlib import Path
import subprocess
import csv

ROOT = Path(__file__).parent
OUT = ROOT / 'outputs'
PICK_DIR = OUT / 'picklists'
SENS_CSV = OUT / 'sensitivity_summary.csv'

buffers = [0.05, 0.1, 0.15]
rows = []
for b in buffers:
    # call generate_picklists.py with given buffer
    cmd = ["python", str(ROOT / 'generate_picklists.py'), "--buffer", str(b)]
    print('Running:', ' '.join(cmd))
    subprocess.check_call(cmd)
    # read picklist_summary to extract top donor total
    summary = OUT / 'picklist_summary.txt'
    top_donor = ''
    donor_units = 0
    if summary.exists():
        text = summary.read_text()
        # crude parsing: look for the Top donors table and pick first numeric
        lines = text.splitlines()
        for i, l in enumerate(lines):
            if l.strip().startswith('from_county'):
                if i+1 < len(lines):
                    parts = lines[i+1].split()
                    if len(parts)>=2:
                        top_donor = parts[0]
                        try:
                            donor_units = int(parts[1])
                        except ValueError:
                            donor_units = 0
                break
    rows.append({'buffer_pct': b, 'top_donor_units': donor_units})

# write CSV
with open(SENS_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['buffer_pct', 'top_donor_units'])
    writer.writeheader()
    writer.writerows(rows)

print('Wrote', SENS_CSV)
