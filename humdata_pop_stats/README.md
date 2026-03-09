# Subnational Population Statistics (HumData COD-PS)

Sex and age disaggregated population estimates for Bangladesh (2022), from OCHA/HumData Common Operational Dataset.

Source: https://data.humdata.org/dataset/cod-ps-bgd

## How to regenerate

```bash
pip install pandas openpyxl
python humdata_pop_stats/extract_pop_stats.py
```

Raw files are in `raw/` (downloaded from HumData).

## Output files

### pop_district.csv (64 districts, 58 columns)

| Column | Description |
|--------|-------------|
| `division` | Division name (ADM1) |
| `division_pcode` | Division P-code |
| `district` | District name (ADM2) |
| `district_pcode` | District P-code |
| `female_total` | Total female population |
| `male_total` | Total male population |
| `total_population` | Total population |
| `female_00_04`..`female_80plus` | Female population by 5-year age group |
| `male_00_04`..`male_80plus` | Male population by 5-year age group |
| `total_00_04`..`total_80plus` | Total population by 5-year age group |

### pop_upazila.csv (544 upazilas, 60 columns)

Same columns as district, plus:

| Column | Description |
|--------|-------------|
| `upazila` | Upazila name (ADM3) |
| `upazila_pcode` | Upazila P-code |

### pop_division.csv (8 divisions, 56 columns)

Same population columns, with division-level admin fields only.

## Notes

- Population totals are consistent across all three levels (165,650,475)
- 17 age groups: 0-4, 5-9, 10-14, ..., 75-79, 80+
- P-codes follow the Bangladesh COD standard (e.g. BD10 = Barisal division)
- Division names use the HumData spelling (e.g. "Barisal" not "Barishal", "Chittagong" not "Chattogram")
