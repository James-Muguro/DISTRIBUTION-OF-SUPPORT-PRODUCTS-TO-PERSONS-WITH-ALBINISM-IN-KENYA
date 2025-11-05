# Run the full pipeline (PowerShell helper)
python data_processing.py --products "distribution_of_sunscreen_and_support_products_to_persons_with_albinism_pwas (1).csv" --population "distribution-of-persons-with-albinism-by-sex1-area-of-residence-county-and-sub-county-2019-censu (1).csv"
python analysis.py
python insights.py
python transfer_plan.py
python generate_picklists.py --buffer 0.1
python sensitivity.py
Write-Host "Pipeline finished. See outputs/ for reports and picklists."
