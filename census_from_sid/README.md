# Population and Housing Census 2022 (Preliminary Report)

Data extracted from **PHC_Preliminary_Report_August_2022.pdf** (Bangladesh Bureau of Statistics).

## How to regenerate

```bash
pip install pandas
# Requires pdftotext (poppler-utils)
python census_from_sid/extract_census_data.py
```

## Output files

### census_district.csv (64 districts, 47 columns)

| Column | Source | Description |
|--------|--------|-------------|
| `division` | — | Parent division name |
| `district` | — | District name |
| `total_population` | A-1.1 | Total population (PHC 2022) |
| `male_population` | A-1.1 | Male population |
| `female_population` | A-1.1 | Female population |
| `hijra_population` | A-1.1 | Hijra population |
| `sex_ratio` | A-1.1 | Males per 100 females |
| `rural_male` | A-1.2 | Rural male population |
| `rural_female` | A-1.2 | Rural female population |
| `rural_hijra` | A-1.2 | Rural hijra population |
| `rural_total` | A-1.2 | Total rural population |
| `urban_male` | A-1.2 | Urban male population |
| `urban_female` | A-1.2 | Urban female population |
| `urban_hijra` | A-1.2 | Urban hijra population |
| `urban_total` | A-1.2 | Total urban population |
| `ethnic_minority_total` | A-1.3 | Ethnic minority population |
| `ethnic_minority_male` | A-1.3 | Ethnic minority male |
| `ethnic_minority_female` | A-1.3 | Ethnic minority female |
| `ethnic_minority_pct` | A-1.3 | % ethnic minority |
| `pct_muslim` | A-1.6 | % Muslim |
| `pct_hindu` | A-1.6 | % Hindu |
| `pct_buddhist` | A-1.6 | % Buddhist |
| `pct_christian` | A-1.6 | % Christian |
| `pct_other_religion` | A-1.6 | % other religion |
| `literacy_rate_total` | A-1.7 | Literacy rate (%) total |
| `literacy_rate_male` | A-1.7 | Literacy rate (%) male |
| `literacy_rate_female` | A-1.7 | Literacy rate (%) female |
| `literacy_rate_hijra` | A-1.7 | Literacy rate (%) hijra |
| `total_households` | A-1.11 | Total households |
| `slum_households` | A-1.11 | Slum households |
| `slum_population` | A-1.11 | Slum population |
| `floating_households` | A-1.11 | Floating households |
| `floating_population` | A-1.11 | Floating population |
| `regular_households` | A-1.11 | Regular households |
| `regular_population` | A-1.11 | Regular population |
| `household_size` | A-1.11 | Average household size |
| `population_2011` | A-1.12 | Population (Census 2011) |
| `households_2011` | A-1.12 | Households (Census 2011) |
| `hh_size_2011` | A-1.12 | HH size (2011) |
| `density_2011` | A-1.12 | Pop. density per sq.km (2011) |
| `population_2022` | A-1.12 | Population (Census 2022) |
| `households_2022` | A-1.12 | Households (Census 2022) |
| `hh_size_2022` | A-1.12 | HH size (2022) |
| `density_2022` | A-1.12 | Pop. density per sq.km (2022) |
| `dwelling_units_rural` | A-1.13 | Rural dwelling units |
| `dwelling_units_urban` | A-1.13 | Urban dwelling units |
| `dwelling_units_total` | A-1.13 | Total dwelling units |

### census_division.csv (8 divisions, 163 columns)

All district-level columns above (aggregated at division level), plus:

| Column | Source | Description |
|--------|--------|-------------|
| `male_unmarried_pct` | A-1.5 | % males unmarried |
| `male_married_pct` | A-1.5 | % males married |
| `male_widowed_pct` | A-1.5 | % males widowed |
| `male_divorced_pct` | A-1.5 | % males divorced |
| `male_separated_pct` | A-1.5 | % males separated |
| `female_unmarried_pct` | A-1.5 | % females unmarried |
| `female_married_pct` | A-1.5 | % females married |
| `female_widowed_pct` | A-1.5 | % females widowed |
| `female_divorced_pct` | A-1.5 | % females divorced |
| `female_separated_pct` | A-1.5 | % females separated |
| `dependency_ratio_total` | A-1.8 | Dependency ratio (total) |
| `dependency_ratio_rural` | A-1.8 | Dependency ratio (rural) |
| `dependency_ratio_urban` | A-1.8 | Dependency ratio (urban) |
| `mobile_5plus_total_pct` | A-1.9 | % mobile phone users 5+ (total) |
| `mobile_5plus_male_pct` | A-1.9 | % mobile phone users 5+ (male) |
| `mobile_5plus_female_pct` | A-1.9 | % mobile phone users 5+ (female) |
| `mobile_5plus_rural_*_pct` | A-1.9 | Rural mobile users 5+ (total/male/female) |
| `mobile_5plus_urban_*_pct` | A-1.9 | Urban mobile users 5+ (total/male/female) |
| `mobile_18plus_*_pct` | A-1.9 | Mobile phone users 18+ (same breakdown as 5+) |
| `internet_5plus_total_pct` | A-1.10 | % internet users 5+ (total) |
| `internet_5plus_male_pct` | A-1.10 | % internet users 5+ (male) |
| `internet_5plus_female_pct` | A-1.10 | % internet users 5+ (female) |
| `internet_5plus_rural_*_pct` | A-1.10 | Rural internet users 5+ (total/male/female) |
| `internet_5plus_urban_*_pct` | A-1.10 | Urban internet users 5+ (total/male/female) |
| `internet_18plus_*_pct` | A-1.10 | Internet users 18+ (same breakdown as 5+) |
| `marital_never_married_pct` | 2.15 | % never married (combined sex) |
| `marital_currently_married_pct` | 2.15 | % currently married |
| `marital_widowed_pct` | 2.15 | % widow/widower |
| `marital_divorced_pct` | 2.15 | % divorced |
| `marital_separated_pct` | 2.15 | % separated |
| `literacy_rural_total` | 2.17 | Literacy rate rural (total) |
| `literacy_rural_male` | 2.17 | Literacy rate rural (male) |
| `literacy_rural_female` | 2.17 | Literacy rate rural (female) |
| `literacy_urban_total` | 2.17 | Literacy rate urban (total) |
| `literacy_urban_male` | 2.17 | Literacy rate urban (male) |
| `literacy_urban_female` | 2.17 | Literacy rate urban (female) |
| `growth_rate_2022` | 2.4 | Annual avg. population growth rate |
| `sex_ratio_1974..2022` | 2.5 | Historical sex ratio (1974-2022) |
| `dwelling_total_pop` | 2.9 | Total pop. by dwelling type |
| `dwelling_slum_pop` | 2.9 | Slum population |
| `dwelling_floating_pop` | 2.9 | Floating population |
| `dwelling_others_pop` | 2.9 | Other dwelling population |
| `floating_pop_total` | 2.10 | Floating population (total) |
| `floating_pop_male` | 2.10 | Floating population (male) |
| `density_1974..2022_body` | 2.11 | Historical pop. density (1974-2022) |
| `child_woman_ratio_total` | 2.13 | Children 0-4 per 1000 women 15-49 |
| `child_woman_ratio_rural` | 2.13 | Child-woman ratio (rural) |
| `child_woman_ratio_urban` | 2.13 | Child-woman ratio (urban) |
| `disability_total` | 2.18 | Persons with disabilities |
| `disability_rate_total` | 2.18 | Disability rate (%) |
| `disability_male` | 2.18 | Males with disabilities |
| `disability_rate_male` | 2.18 | Male disability rate (%) |
| `disability_female` | 2.18 | Females with disabilities |
| `disability_rate_female` | 2.18 | Female disability rate (%) |
| `hh_rural` | 3.3 | Rural households |
| `hh_urban` | 3.3 | Urban households |
| `hh_size_rural` | 3.3 | Household size (rural) |
| `hh_size_urban` | 3.3 | Household size (urban) |
| `hh_slum` | 3.4 | Slum households |
| `hh_floating` | 3.4 | Floating households |
| `hh_others` | 3.4 | Other households |
| `dwelling_units_total_body` | 3.5 | Total dwelling units |
| `dwelling_units_rural_body` | 3.5 | Rural dwelling units |
| `dwelling_units_urban_body` | 3.5 | Urban dwelling units |
| `water_pct_pipe` | 3.6 | % tap/pipe water |
| `water_pct_tubewell` | 3.6 | % tubewell water |
| `water_pct_bottled` | 3.6 | % bottled water |
| `water_pct_well` | 3.6 | % well water |
| `water_pct_pond_river` | 3.6 | % pond/river/canal water |
| `water_pct_spring` | 3.6 | % spring water |
| `water_pct_rain` | 3.6 | % rain water |
| `water_pct_others` | 3.6 | % other water sources |
| `toilet_pct_safe_flush` | 3.7 | % safe disposal flushing |
| `toilet_pct_unsafe_flush` | 3.7 | % unsafe disposal flushing |
| `toilet_pct_pit_slab` | 3.7 | % pit latrine with slab |
| `toilet_pct_pit_no_slab` | 3.7 | % pit latrine without slab |
| `toilet_pct_kutcha` | 3.7 | % kutcha/open/hanging latrine |
| `toilet_pct_open_defecation` | 3.7 | % open defecation/no latrine |
| `electricity_pct_grid` | 3.8 | % national grid electricity |
| `electricity_pct_solar` | 3.8 | % solar electricity |
| `electricity_pct_others` | 3.8 | % other electricity sources |
| `electricity_pct_none` | 3.8 | % no electricity |

### census_city_corporation.csv (12 city corporations)

| Column | Source | Description |
|--------|--------|-------------|
| `city_corporation` | 2.7 | City corporation name |
| `total_population` | 2.7 | Total population |
| `male_population` | 2.7 | Male population |
| `female_population` | 2.7 | Female population |
| `hijra_population` | 2.7 | Hijra population |
| `density` | 2.7 | Pop. density per sq.km |

## Notes

- Mymensingh division was created after 2011, so historical data is unavailable for it
- Rangpur division was separated from Rajshahi division after 2001
- Sylhet division was separated from Chittagong (Chattogram) division after 1974
- Literacy rate is for population aged 7 years and above
- All data from the PHC 2022 Preliminary Report (August 2022)
