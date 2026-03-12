"""District-level column metadata for `poverty_district.csv`."""

DISTRICT_COLUMN_DESCRIPTIONS = {
    'division': 'Parent division name.',
    'name': 'District name.',
    'population': 'General household population used in the poverty map.',
    'quintile_2022': '2022 poverty quintile group, from Very Low (Q1) to Very High (Q5).',
    'poverty_rate_2022': '2022 upper poverty line headcount rate in percent.',
    'se_2022': 'Standard error of the 2022 poverty estimate, in percentage points.',
    'quintile_2010': '2010 poverty quintile group.',
    'poverty_rate_2010': '2010 upper poverty line headcount rate in percent, re-estimated for comparability.',
    'se_2010': 'Standard error of the 2010 poverty estimate, in percentage points.',
    'extreme_poverty_category': '2022 lower poverty line category: Low, Moderate, or High.',
    'poverty_change_2010_2022': 'Change in poverty rate between 2010 and 2022, in percentage points.',
}

DISTRICT_COLUMN_KEYS = list(DISTRICT_COLUMN_DESCRIPTIONS.keys())

__all__ = ["DISTRICT_COLUMN_DESCRIPTIONS", "DISTRICT_COLUMN_KEYS"]
