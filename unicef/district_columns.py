"""District-level column metadata for `mics6_district_indicators.csv`."""

DISTRICT_COLUMN_DESCRIPTIONS = {
    'district': 'District name.',
    'n_households': 'Number of surveyed households.',
    'wealth_score_mean': 'Mean household wealth score.',
    'wealth_score_median': 'Median household wealth score.',
    'pct_poorest': 'Share of surveyed households in the poorest wealth quintile.',
    'pct_richest': 'Share of surveyed households in the richest wealth quintile.',
    'pct_electricity': 'Share of surveyed households with electricity.',
    'pct_mobile': 'Share of surveyed households with a mobile phone.',
    'pct_internet': 'Share of surveyed households with internet access.',
    'pct_urban': 'Share of surveyed households in urban areas.',
    'pct_improved_water': 'Share of households using an improved drinking water source.',
    'pct_improved_sanitation': 'Share of households using an improved sanitation facility.',
    'pct_ever_school': 'Share of people who ever attended school.',
    'pct_secondary_plus': 'Share of people with secondary or higher education.',
    'pct_female_ever_school': 'Share of females who ever attended school.',
    'pct_female_secondary_plus': 'Share of females with secondary or higher education.',
    'pct_women_no_education': 'Share of surveyed women with no education.',
    'pct_women_secondary_plus': 'Share of surveyed women with secondary or higher education.',
    'median_marriage_age': 'Median age at first marriage among surveyed women.',
    'pct_women_internet': 'Share of surveyed women who use the internet.',
    'pct_women_newspaper': 'Share of surveyed women who read newspapers or magazines.',
    'pct_birth_registered': 'Share of surveyed children whose births were registered.',
    'pct_stunted': 'Share of surveyed children who are stunted based on height-for-age z-scores.',
    'pct_underweight': 'Share of surveyed children who are underweight based on weight-for-age z-scores.',
    'total_births': 'Total recorded births in the survey data.',
    'pct_child_mortality': 'Share of recorded births where the child is no longer alive.',
    'avg_births_per_woman': 'Average number of recorded births per surveyed woman.',
    'n_children_5_17': 'Number of surveyed children ages 5-17.',
    'pct_children_ever_school': 'Share of surveyed children ages 5-17 who ever attended school.',
    'pct_read_fluently': 'Share of surveyed children who can read a story fluently.',
    'pct_can_read': 'Share of surveyed children who can read with difficulty or fluently.',
    'pct_numeracy': 'Share of surveyed children who answered at least 3 of 5 addition problems correctly.',
    'pct_comprehension': 'Share of surveyed children who answered at least 2 of 3 reading comprehension questions correctly.',
}

DISTRICT_COLUMN_KEYS = list(DISTRICT_COLUMN_DESCRIPTIONS.keys())

__all__ = ["DISTRICT_COLUMN_DESCRIPTIONS", "DISTRICT_COLUMN_KEYS"]
