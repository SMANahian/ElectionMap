# Population and Housing Census 2022 (District-Level)

This README documents the district-level columns in `census_district.csv`.

Source: Bangladesh Bureau of Statistics PHC Preliminary Report 2022.

## Files

- `census_district.csv`: District-level dataset.
- `district_columns.py`: Importable column description dict and ordered key list.

## How to regenerate

```bash
pip install pandas
# Requires pdftotext (poppler-utils)
python census_from_sid/extract_census_data.py
python scripts/generate_district_metadata.py
```

## Columns

| Column | Description |
|--------|-------------|
| `division` | Parent division name. |
| `district` | District name. |
| `total_population` | Total district population in the 2022 Population and Housing Census. |
| `male_population` | Male population in the district. |
| `female_population` | Female population in the district. |
| `hijra_population` | Hijra population in the district. |
| `sex_ratio` | Males per 100 females. |
| `rural_male` | Rural male population. |
| `rural_female` | Rural female population. |
| `rural_hijra` | Rural hijra population. |
| `rural_total` | Total rural population. |
| `urban_male` | Urban male population. |
| `urban_female` | Urban female population. |
| `urban_hijra` | Urban hijra population. |
| `urban_total` | Total urban population. |
| `ethnic_minority_total` | Total ethnic minority population. |
| `ethnic_minority_male` | Male ethnic minority population. |
| `ethnic_minority_female` | Female ethnic minority population. |
| `ethnic_minority_pct` | Ethnic minority population as a share of the district population. |
| `pct_muslim` | Muslim share of the district population. |
| `pct_hindu` | Hindu share of the district population. |
| `pct_buddhist` | Buddhist share of the district population. |
| `pct_christian` | Christian share of the district population. |
| `pct_other_religion` | Share of the population in all other religions combined. |
| `literacy_rate_total` | Literacy rate for people age 7 and above. |
| `literacy_rate_male` | Male literacy rate for people age 7 and above. |
| `literacy_rate_female` | Female literacy rate for people age 7 and above. |
| `literacy_rate_hijra` | Hijra literacy rate for people age 7 and above. |
| `total_households` | Total number of households. |
| `slum_households` | Households classified as slum households. |
| `slum_population` | Population living in slum households. |
| `floating_households` | Households classified as floating households. |
| `floating_population` | Population in floating households. |
| `regular_households` | Households excluding slum and floating households. |
| `regular_population` | Population excluding slum and floating households. |
| `household_size` | Average household size. |
| `population_2011` | District population from the 2011 census. |
| `households_2011` | District households from the 2011 census. |
| `hh_size_2011` | Average household size in 2011. |
| `density_2011` | Population density per square kilometer in 2011. |
| `population_2022` | District population from the 2022 census. |
| `households_2022` | District households from the 2022 census. |
| `hh_size_2022` | Average household size in 2022. |
| `density_2022` | Population density per square kilometer in 2022. |
| `dwelling_units_rural` | Number of rural dwelling units. |
| `dwelling_units_urban` | Number of urban dwelling units. |
| `dwelling_units_total` | Total number of dwelling units. |

## Notes

- This README documents only the district-level file.
- Column meanings follow the district output produced by extract_census_data.py.
