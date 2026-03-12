# HumData Population Statistics (District-Level)

This README documents the district-level columns in `pop_district.csv`.

Source: OCHA HumData COD-PS Bangladesh 2022.

## Files

- `pop_district.csv`: District-level dataset.
- `district_columns.py`: Importable column description dict and ordered key list.

## How to regenerate

```bash
pip install pandas openpyxl
python humdata_pop_stats/extract_pop_stats.py
python scripts/generate_district_metadata.py
```

## Columns

| Column | Description |
|--------|-------------|
| `division` | Division name from the HumData COD admin hierarchy. |
| `division_pcode` | Division P-code from the HumData COD admin hierarchy. |
| `district` | District name from the HumData COD admin hierarchy. |
| `district_pcode` | District P-code from the HumData COD admin hierarchy. |
| `female_total` | Total female population estimate. |
| `male_total` | Total male population estimate. |
| `total_population` | Total population estimate. |
| `female_00_04` | Female population estimate ages 0-4. |
| `female_05_09` | Female population estimate ages 5-9. |
| `female_10_14` | Female population estimate ages 10-14. |
| `female_15_19` | Female population estimate ages 15-19. |
| `female_20_24` | Female population estimate ages 20-24. |
| `female_25_29` | Female population estimate ages 25-29. |
| `female_30_34` | Female population estimate ages 30-34. |
| `female_35_39` | Female population estimate ages 35-39. |
| `female_40_44` | Female population estimate ages 40-44. |
| `female_45_49` | Female population estimate ages 45-49. |
| `female_50_54` | Female population estimate ages 50-54. |
| `female_55_59` | Female population estimate ages 55-59. |
| `female_60_64` | Female population estimate ages 60-64. |
| `female_65_69` | Female population estimate ages 65-69. |
| `female_70_74` | Female population estimate ages 70-74. |
| `female_75_79` | Female population estimate ages 75-79. |
| `female_80plus` | Female population estimate ages 80 and above. |
| `male_00_04` | Male population estimate ages 0-4. |
| `male_05_09` | Male population estimate ages 5-9. |
| `male_10_14` | Male population estimate ages 10-14. |
| `male_15_19` | Male population estimate ages 15-19. |
| `male_20_24` | Male population estimate ages 20-24. |
| `male_25_29` | Male population estimate ages 25-29. |
| `male_30_34` | Male population estimate ages 30-34. |
| `male_35_39` | Male population estimate ages 35-39. |
| `male_40_44` | Male population estimate ages 40-44. |
| `male_45_49` | Male population estimate ages 45-49. |
| `male_50_54` | Male population estimate ages 50-54. |
| `male_55_59` | Male population estimate ages 55-59. |
| `male_60_64` | Male population estimate ages 60-64. |
| `male_65_69` | Male population estimate ages 65-69. |
| `male_70_74` | Male population estimate ages 70-74. |
| `male_75_79` | Male population estimate ages 75-79. |
| `male_80plus` | Male population estimate ages 80 and above. |
| `total_00_04` | Total population estimate ages 0-4. |
| `total_05_09` | Total population estimate ages 5-9. |
| `total_10_14` | Total population estimate ages 10-14. |
| `total_15_19` | Total population estimate ages 15-19. |
| `total_20_24` | Total population estimate ages 20-24. |
| `total_25_29` | Total population estimate ages 25-29. |
| `total_30_34` | Total population estimate ages 30-34. |
| `total_35_39` | Total population estimate ages 35-39. |
| `total_40_44` | Total population estimate ages 40-44. |
| `total_45_49` | Total population estimate ages 45-49. |
| `total_50_54` | Total population estimate ages 50-54. |
| `total_55_59` | Total population estimate ages 55-59. |
| `total_60_64` | Total population estimate ages 60-64. |
| `total_65_69` | Total population estimate ages 65-69. |
| `total_70_74` | Total population estimate ages 70-74. |
| `total_75_79` | Total population estimate ages 75-79. |
| `total_80plus` | Total population estimate ages 80 and above. |

## Notes

- This README documents only the district-level file.
- Age groups are five-year bands except 80plus, which means age 80 and above.
