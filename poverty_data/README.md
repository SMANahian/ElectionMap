# Poverty Map of Bangladesh 2022

Data extracted from **"Poverty Map of Bangladesh 2022: Small Area Estimation — District and Upazila Results"** (BBS, World Bank, WFP, December 2024).

Source PDF: `ELR 3605.pdf`

## How to regenerate

```bash
pip install pdfplumber pandas
python poverty_data/extract_poverty_data.py
```

## Output files

### poverty_district.csv (64 districts)

| Column | Description |
|--------|-------------|
| `division` | Division name (8 divisions) |
| `name` | District name |
| `population` | General household population (PHC 2022) |
| `quintile_2022` | Poverty quintile group 2022: Very Low (Q1) to Very High (Q5) |
| `poverty_rate_2022` | Poverty headcount rate (%) Upper Poverty Line, 2022 (CensusEB) |
| `se_2022` | Standard error (%) of 2022 estimate |
| `quintile_2010` | Poverty quintile group 2010 |
| `poverty_rate_2010` | Poverty headcount rate (%) Upper Poverty Line, 2010 (CensusEB, re-estimated) |
| `se_2010` | Standard error (%) of 2010 estimate |
| `extreme_poverty_category` | Extreme poverty level (Lower Poverty Line) 2022: Low (<2.15%), Moderate (2.16-5.52%), High (>5.53%) |
| `poverty_change_2010_2022` | Change in poverty rate from 2010 to 2022 (percentage points) |

### poverty_upazila.csv (590 upazilas)

Same columns as district CSV, plus:

| Column | Description |
|--------|-------------|
| `district` | Parent district name |

## Data sources within the PDF

- **Annex 1**: Division, District and Upazila Level Poverty Rates of 2022 and 2010 — population, quintile, HCR (%), standard error
- **Annex 2**: Division, District and Upazila Level Extreme Poverty of 2022 — categorical (Low/Moderate/High)

## Notes

- 2010 figures are re-estimated using CensusEB method and comparable consumption aggregates (differ from original 2010 poverty maps)
- Population figures are from PHC 2022, excluding institutional and floating populations
- Quintile thresholds for 2022: Very Low <9.80%, Low 9.81-14.90%, Moderate 14.91-21.15%, High 21.16-28.20%, Very High >28.20%
