# Poverty Map of Bangladesh 2022 (District-Level)

This README documents the district-level columns in `poverty_district.csv`.

Source: Poverty Map of Bangladesh 2022: Small Area Estimation - District and Upazila Results.

## Files

- `poverty_district.csv`: District-level dataset.
- `district_columns.py`: Importable column description dict and ordered key list.

## How to regenerate

```bash
pip install pdfplumber pandas
python poverty_data/extract_poverty_data.py
python scripts/generate_district_metadata.py
```

## Columns

| Column | Description |
|--------|-------------|
| `division` | Parent division name. |
| `name` | District name. |
| `population` | General household population used in the poverty map. |
| `quintile_2022` | 2022 poverty quintile group, from Very Low (Q1) to Very High (Q5). |
| `poverty_rate_2022` | 2022 upper poverty line headcount rate in percent. |
| `se_2022` | Standard error of the 2022 poverty estimate, in percentage points. |
| `quintile_2010` | 2010 poverty quintile group. |
| `poverty_rate_2010` | 2010 upper poverty line headcount rate in percent, re-estimated for comparability. |
| `se_2010` | Standard error of the 2010 poverty estimate, in percentage points. |
| `extreme_poverty_category` | 2022 lower poverty line category: Low, Moderate, or High. |
| `poverty_change_2010_2022` | Change in poverty rate between 2010 and 2022, in percentage points. |

## Notes

- This README documents only the district-level file.
- Poverty rates use the upper poverty line; extreme poverty categories use the lower poverty line.
