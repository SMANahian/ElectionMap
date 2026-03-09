# UNICEF MICS6 District Indicators

Data extracted from the **Bangladesh MICS6 (Multiple Indicator Cluster Survey, 2019)** SPSS datasets, aggregated per district (64 districts).

## How to regenerate

```bash
pip install pyreadstat pandas numpy
python unicef/extract_district_indicators.py
```

Requires the SPSS `.sav` files in `Bangladesh MICS6 SPSS Datasets/`.

## Output

**`mics6_district_indicators.csv`** — one row per district, with the following columns:

### Household (from hh.sav)
| Column | Description |
|--------|-------------|
| `n_households` | Number of surveyed households |
| `wealth_score_mean` | Mean composite wealth score |
| `wealth_score_median` | Median composite wealth score |
| `pct_poorest` | % in poorest wealth quintile |
| `pct_richest` | % in richest wealth quintile |
| `pct_electricity` | % with electricity |
| `pct_mobile` | % with mobile phone |
| `pct_internet` | % with internet access |
| `pct_urban` | % urban households |
| `pct_improved_water` | % using improved drinking water source |
| `pct_improved_sanitation` | % using improved sanitation facility |

### Education (from hl.sav)
| Column | Description |
|--------|-------------|
| `pct_ever_school` | % who ever attended school (all) |
| `pct_secondary_plus` | % with secondary or higher education (all) |
| `pct_female_ever_school` | % females who ever attended school |
| `pct_female_secondary_plus` | % females with secondary or higher education |

### Women's indicators (from wm.sav)
| Column | Description |
|--------|-------------|
| `pct_women_no_education` | % women with no education |
| `pct_women_secondary_plus` | % women with secondary or higher education |
| `median_marriage_age` | Median age at first marriage |
| `pct_women_internet` | % women who use internet |
| `pct_women_newspaper` | % women who read newspaper/magazine |

### Child health (from ch.sav)
| Column | Description |
|--------|-------------|
| `pct_birth_registered` | % births registered |
| `pct_stunted` | % children stunted (height-for-age z-score < -2, WHO) |
| `pct_underweight` | % children underweight (weight-for-age z-score < -2, WHO) |

### Birth history / fertility (from bh.sav)
| Column | Description |
|--------|-------------|
| `total_births` | Total recorded births in survey |
| `pct_child_mortality` | % of births where child is no longer alive |
| `avg_births_per_woman` | Average number of births per woman |

### Foundational learning skills (from fs.sav)
| Column | Description |
|--------|-------------|
| `n_children_5_17` | Number of surveyed children age 5-17 |
| `pct_children_ever_school` | % children who ever attended school |
| `pct_read_fluently` | % who can read a story fluently |
| `pct_can_read` | % who can read (with difficulty or fluently) |
| `pct_numeracy` | % who answered 3+ out of 5 addition problems correctly |
| `pct_comprehension` | % who answered 2+ out of 3 reading comprehension questions correctly |

## Joining with election data

The `district` column can be joined with the election results' district column. Both use standard district names (e.g. Bogura, Cumilla, Chattogram).
