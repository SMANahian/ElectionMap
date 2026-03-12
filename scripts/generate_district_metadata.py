"""
Generate district-level column metadata modules and README files.

Outputs:
  - <dataset>/district_columns.py
  - <dataset>/README.md
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import csv
import re

import pandas as pd


BASE = Path(__file__).resolve().parents[1]


def age_label(code: str) -> str:
    if code == "80plus":
        return "80 and above"
    start, end = code.split("_")
    return f"{int(start)}-{int(end)}"


def census_sid_descriptions() -> OrderedDict[str, str]:
    return OrderedDict(
        [
            ("division", "Parent division name."),
            ("district", "District name."),
            ("total_population", "Total district population in the 2022 Population and Housing Census."),
            ("male_population", "Male population in the district."),
            ("female_population", "Female population in the district."),
            ("hijra_population", "Hijra population in the district."),
            ("sex_ratio", "Males per 100 females."),
            ("rural_male", "Rural male population."),
            ("rural_female", "Rural female population."),
            ("rural_hijra", "Rural hijra population."),
            ("rural_total", "Total rural population."),
            ("urban_male", "Urban male population."),
            ("urban_female", "Urban female population."),
            ("urban_hijra", "Urban hijra population."),
            ("urban_total", "Total urban population."),
            ("ethnic_minority_total", "Total ethnic minority population."),
            ("ethnic_minority_male", "Male ethnic minority population."),
            ("ethnic_minority_female", "Female ethnic minority population."),
            ("ethnic_minority_pct", "Ethnic minority population as a share of the district population."),
            ("pct_muslim", "Muslim share of the district population."),
            ("pct_hindu", "Hindu share of the district population."),
            ("pct_buddhist", "Buddhist share of the district population."),
            ("pct_christian", "Christian share of the district population."),
            ("pct_other_religion", "Share of the population in all other religions combined."),
            ("literacy_rate_total", "Literacy rate for people age 7 and above."),
            ("literacy_rate_male", "Male literacy rate for people age 7 and above."),
            ("literacy_rate_female", "Female literacy rate for people age 7 and above."),
            ("literacy_rate_hijra", "Hijra literacy rate for people age 7 and above."),
            ("total_households", "Total number of households."),
            ("slum_households", "Households classified as slum households."),
            ("slum_population", "Population living in slum households."),
            ("floating_households", "Households classified as floating households."),
            ("floating_population", "Population in floating households."),
            ("regular_households", "Households excluding slum and floating households."),
            ("regular_population", "Population excluding slum and floating households."),
            ("household_size", "Average household size."),
            ("population_2011", "District population from the 2011 census."),
            ("households_2011", "District households from the 2011 census."),
            ("hh_size_2011", "Average household size in 2011."),
            ("density_2011", "Population density per square kilometer in 2011."),
            ("population_2022", "District population from the 2022 census."),
            ("households_2022", "District households from the 2022 census."),
            ("hh_size_2022", "Average household size in 2022."),
            ("density_2022", "Population density per square kilometer in 2022."),
            ("dwelling_units_rural", "Number of rural dwelling units."),
            ("dwelling_units_urban", "Number of urban dwelling units."),
            ("dwelling_units_total", "Total number of dwelling units."),
        ]
    )


def humdata_pop_descriptions() -> OrderedDict[str, str]:
    descriptions: OrderedDict[str, str] = OrderedDict(
        [
            ("division", "Division name from the HumData COD admin hierarchy."),
            ("division_pcode", "Division P-code from the HumData COD admin hierarchy."),
            ("district", "District name from the HumData COD admin hierarchy."),
            ("district_pcode", "District P-code from the HumData COD admin hierarchy."),
            ("female_total", "Total female population estimate."),
            ("male_total", "Total male population estimate."),
            ("total_population", "Total population estimate."),
        ]
    )

    age_codes = [
        "00_04",
        "05_09",
        "10_14",
        "15_19",
        "20_24",
        "25_29",
        "30_34",
        "35_39",
        "40_44",
        "45_49",
        "50_54",
        "55_59",
        "60_64",
        "65_69",
        "70_74",
        "75_79",
        "80plus",
    ]

    for prefix, label in [("female", "Female"), ("male", "Male"), ("total", "Total")]:
        for code in age_codes:
            descriptions[f"{prefix}_{code}"] = f"{label} population estimate ages {age_label(code)}."

    return descriptions


def poverty_descriptions() -> OrderedDict[str, str]:
    return OrderedDict(
        [
            ("division", "Parent division name."),
            ("name", "District name."),
            ("population", "General household population used in the poverty map."),
            ("quintile_2022", "2022 poverty quintile group, from Very Low (Q1) to Very High (Q5)."),
            ("poverty_rate_2022", "2022 upper poverty line headcount rate in percent."),
            ("se_2022", "Standard error of the 2022 poverty estimate, in percentage points."),
            ("quintile_2010", "2010 poverty quintile group."),
            ("poverty_rate_2010", "2010 upper poverty line headcount rate in percent, re-estimated for comparability."),
            ("se_2010", "Standard error of the 2010 poverty estimate, in percentage points."),
            ("extreme_poverty_category", "2022 lower poverty line category: Low, Moderate, or High."),
            ("poverty_change_2010_2022", "Change in poverty rate between 2010 and 2022, in percentage points."),
        ]
    )


def unicef_descriptions() -> OrderedDict[str, str]:
    return OrderedDict(
        [
            ("district", "District name."),
            ("n_households", "Number of surveyed households."),
            ("wealth_score_mean", "Mean household wealth score."),
            ("wealth_score_median", "Median household wealth score."),
            ("pct_poorest", "Share of surveyed households in the poorest wealth quintile."),
            ("pct_richest", "Share of surveyed households in the richest wealth quintile."),
            ("pct_electricity", "Share of surveyed households with electricity."),
            ("pct_mobile", "Share of surveyed households with a mobile phone."),
            ("pct_internet", "Share of surveyed households with internet access."),
            ("pct_urban", "Share of surveyed households in urban areas."),
            ("pct_improved_water", "Share of households using an improved drinking water source."),
            ("pct_improved_sanitation", "Share of households using an improved sanitation facility."),
            ("pct_ever_school", "Share of people who ever attended school."),
            ("pct_secondary_plus", "Share of people with secondary or higher education."),
            ("pct_female_ever_school", "Share of females who ever attended school."),
            ("pct_female_secondary_plus", "Share of females with secondary or higher education."),
            ("pct_women_no_education", "Share of surveyed women with no education."),
            ("pct_women_secondary_plus", "Share of surveyed women with secondary or higher education."),
            ("median_marriage_age", "Median age at first marriage among surveyed women."),
            ("pct_women_internet", "Share of surveyed women who use the internet."),
            ("pct_women_newspaper", "Share of surveyed women who read newspapers or magazines."),
            ("pct_birth_registered", "Share of surveyed children whose births were registered."),
            ("pct_stunted", "Share of surveyed children who are stunted based on height-for-age z-scores."),
            ("pct_underweight", "Share of surveyed children who are underweight based on weight-for-age z-scores."),
            ("total_births", "Total recorded births in the survey data."),
            ("pct_child_mortality", "Share of recorded births where the child is no longer alive."),
            ("avg_births_per_woman", "Average number of recorded births per surveyed woman."),
            ("n_children_5_17", "Number of surveyed children ages 5-17."),
            ("pct_children_ever_school", "Share of surveyed children ages 5-17 who ever attended school."),
            ("pct_read_fluently", "Share of surveyed children who can read a story fluently."),
            ("pct_can_read", "Share of surveyed children who can read with difficulty or fluently."),
            ("pct_numeracy", "Share of surveyed children who answered at least 3 of 5 addition problems correctly."),
            ("pct_comprehension", "Share of surveyed children who answered at least 2 of 3 reading comprehension questions correctly."),
        ]
    )


def official_result_descriptions() -> OrderedDict[str, str]:
    return OrderedDict(
        [
            ("district", "Standardized English district name derived from the seat names."),
            ("district_bn", "Bangla district name from the Election Commission source data."),
            ("seat_count", "Number of parliamentary constituencies in the district."),
            ("total_voters", "Total registered voters across all constituencies in the district."),
            ("total_votes_cast", "Total ballots cast across all constituencies in the district."),
            ("valid_votes", "Total valid votes across all constituencies in the district."),
            ("rejected_votes", "Total rejected ballots across all constituencies in the district."),
            ("absent_voters", "Registered voters who did not cast a ballot."),
            ("turnout_pct", "Votes cast as a share of total registered voters."),
            ("rejection_pct", "Rejected ballots as a share of all ballots cast."),
            ("absence_pct", "Absent voters as a share of total registered voters."),
            ("total_centers", "Total polling centers across the district."),
            ("total_candidates", "Total candidate entries across all district constituencies."),
            ("avg_voters_per_center", "Average registered voters per polling center."),
            ("avg_candidates_per_seat", "Average number of candidates per constituency in the district."),
            ("safe_seats", "Number of constituencies in the district classified as safe."),
            ("competitive_seats", "Number of constituencies in the district classified as competitive."),
            ("marginal_seats", "Number of constituencies in the district classified as marginal."),
            ("very_close_seats", "Number of constituencies in the district classified as very close."),
            ("bnp_plus_votes", "Total valid votes for the BNP-led alliance bloc."),
            ("bnp_plus_pct", "BNP-led alliance votes as a share of district valid votes."),
            ("eleven_parties_votes", "Total valid votes for the eleven-party bloc."),
            ("eleven_parties_pct", "Eleven-party bloc votes as a share of district valid votes."),
            ("duf_votes", "Total valid votes for DUF-aligned candidates."),
            ("duf_pct", "DUF votes as a share of district valid votes."),
            ("ndf_votes", "Total valid votes for NDF-aligned candidates."),
            ("ndf_pct", "NDF votes as a share of district valid votes."),
            ("greater_sunni_votes", "Total valid votes for Greater Sunni-aligned candidates."),
            ("greater_sunni_pct", "Greater Sunni votes as a share of district valid votes."),
            ("independent_votes", "Total valid votes for independent candidates."),
            ("independent_pct", "Independent votes as a share of district valid votes."),
            ("other_party_votes", "Total valid votes for parties outside the named blocs and top tracked parties."),
            ("other_party_pct", "Other-party votes as a share of district valid votes."),
            ("bnp_votes", "Total valid votes for Bangladesh Nationalist Party - BNP candidates."),
            ("bnp_pct", "BNP votes as a share of district valid votes."),
            ("jamaat_votes", "Total valid votes for Bangladesh Jamaat-e-Islami candidates."),
            ("jamaat_pct", "Jamaat votes as a share of district valid votes."),
            ("ncp_votes", "Total valid votes for Jatiyo Nagorik Party - NCP candidates."),
            ("ncp_pct", "NCP votes as a share of district valid votes."),
            ("leading_party", "Party with the highest aggregate vote total in the district."),
            ("leading_party_votes", "Aggregate votes won by the district-level leading party."),
            ("leading_party_pct", "Leading party votes as a share of district valid votes."),
            ("runner_up_party", "Party with the second-highest aggregate vote total in the district."),
            ("runner_up_votes", "Aggregate votes won by the district-level runner-up party."),
            ("runner_up_pct", "Runner-up party votes as a share of district valid votes."),
            ("vote_margin", "Vote difference between the district-level leading party and runner-up party."),
            ("vote_margin_pct", "Vote margin as a share of district valid votes."),
            ("most_winning_seats_party", "Party that won the most constituencies in the district."),
            ("most_winning_seats_count", "Number of constituencies won by the district seat leader."),
            ("bnp_won_seats", "Number of district constituencies won by BNP."),
            ("jamaat_won_seats", "Number of district constituencies won by Jamaat."),
            ("ncp_won_seats", "Number of district constituencies won by NCP."),
            ("independent_won_seats", "Number of district constituencies won by independents."),
            ("other_party_won_seats", "Number of district constituencies won by all other parties combined."),
            ("effective_num_parties", "Laakso-Taagepera effective number of parties based on district vote shares."),
        ]
    )


def normalize_whitespace(value: str) -> str:
    value = value.replace("\\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def census_humdata_descriptions() -> OrderedDict[str, str]:
    folder = BASE / "census_from_humdata"
    xlsx_path = folder / "bangladesh_bbs_population-and-housing-census-dataset_2022_admin-02.xlsx"
    readme_path = folder / "README.md"

    columns = list(pd.read_excel(xlsx_path, nrows=0).columns)
    readme_text = readme_path.read_text(encoding="utf-8")
    entry_pattern = re.compile(r"- \*\*(.*?)\*\*: (.*)")
    parsed_entries = OrderedDict(entry_pattern.findall(readme_text))
    normalized_entries = {normalize_whitespace(key): value for key, value in parsed_entries.items()}

    descriptions: OrderedDict[str, str] = OrderedDict()
    missing = []
    for column in columns:
        description = parsed_entries.get(column)
        if description is None:
            description = normalized_entries.get(normalize_whitespace(column))
        if description is None:
            missing.append(column)
            description = "Description inferred from the original column glossary in README.md."
        descriptions[column] = description

    if missing:
        raise ValueError(f"Missing descriptions for census_from_humdata columns: {missing}")

    return descriptions


DATASETS = [
    {
        "folder": "census_from_humdata",
        "csv": "bangladesh_bbs_population-and-housing-census-dataset_2022_admin-02.xlsx",
        "title": "Bangladesh BBS Population and Housing Census Dataset 2022 (Admin 2)",
        "source": "Bangladesh Bureau of Statistics admin-02 workbook.",
        "descriptions": census_humdata_descriptions(),
        "regen": [
            "pip install pandas openpyxl",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This dataset is already district-level (admin-02).",
            "The README glossary is preserved; the generator only adds district_columns.py for importable metadata.",
        ],
        "header_format": "xlsx",
        "write_readme": False,
    },
    {
        "folder": "census_from_sid",
        "csv": "census_district.csv",
        "title": "Population and Housing Census 2022 (District-Level)",
        "source": "Bangladesh Bureau of Statistics PHC Preliminary Report 2022.",
        "descriptions": census_sid_descriptions(),
        "regen": [
            "pip install pandas",
            "# Requires pdftotext (poppler-utils)",
            "python census_from_sid/extract_census_data.py",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This README documents only the district-level file.",
            "Column meanings follow the district output produced by extract_census_data.py.",
        ],
    },
    {
        "folder": "humdata_pop_stats",
        "csv": "pop_district.csv",
        "title": "HumData Population Statistics (District-Level)",
        "source": "OCHA HumData COD-PS Bangladesh 2022.",
        "descriptions": humdata_pop_descriptions(),
        "regen": [
            "pip install pandas openpyxl",
            "python humdata_pop_stats/extract_pop_stats.py",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This README documents only the district-level file.",
            "Age groups are five-year bands except 80plus, which means age 80 and above.",
        ],
    },
    {
        "folder": "poverty_data",
        "csv": "poverty_district.csv",
        "title": "Poverty Map of Bangladesh 2022 (District-Level)",
        "source": "Poverty Map of Bangladesh 2022: Small Area Estimation - District and Upazila Results.",
        "descriptions": poverty_descriptions(),
        "regen": [
            "pip install pdfplumber pandas",
            "python poverty_data/extract_poverty_data.py",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This README documents only the district-level file.",
            "Poverty rates use the upper poverty line; extreme poverty categories use the lower poverty line.",
        ],
    },
    {
        "folder": "unicef",
        "csv": "mics6_district_indicators.csv",
        "title": "UNICEF MICS6 District Indicators",
        "source": "Bangladesh MICS6 SPSS datasets, aggregated to district level.",
        "descriptions": unicef_descriptions(),
        "regen": [
            "pip install pyreadstat pandas numpy",
            "python unicef/extract_district_indicators.py",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This README documents only the district-level file.",
            "Most indicator columns are percentages computed from the surveyed records used in the extraction script.",
        ],
    },
    {
        "folder": "official_result",
        "csv": "ec_district_wide.csv",
        "title": "Election Commission Official Results (District-Level Aggregate)",
        "source": "District aggregate built from official_result/ec_constituency_wide.csv.",
        "descriptions": official_result_descriptions(),
        "regen": [
            "python scripts/build_ec_wide.py",
            "python scripts/build_ec_district_wide.py",
            "python scripts/generate_district_metadata.py",
        ],
        "notes": [
            "This README documents only the district-level aggregate file.",
            "The district aggregate is derived from constituency-level official results rather than scraped directly at district level.",
        ],
        "header_format": "csv",
        "write_readme": True,
    },
]


def read_csv_header(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        return next(csv.reader(handle))


def read_xlsx_header(path: Path) -> list[str]:
    return list(pd.read_excel(path, nrows=0).columns)


def read_header(path: Path, header_format: str) -> list[str]:
    if header_format == "xlsx":
        return read_xlsx_header(path)
    return read_csv_header(path)


def write_metadata_module(folder: Path, csv_name: str, descriptions: OrderedDict[str, str]) -> None:
    lines = [
        f'"""District-level column metadata for `{csv_name}`."""',
        "",
        "DISTRICT_COLUMN_DESCRIPTIONS = {",
    ]
    for column, description in descriptions.items():
        lines.append(f"    {column!r}: {description!r},")
    lines.extend(
        [
            "}",
            "",
            "DISTRICT_COLUMN_KEYS = list(DISTRICT_COLUMN_DESCRIPTIONS.keys())",
            "",
            '__all__ = ["DISTRICT_COLUMN_DESCRIPTIONS", "DISTRICT_COLUMN_KEYS"]',
            "",
        ]
    )
    (folder / "district_columns.py").write_text("\n".join(lines), encoding="utf-8")


def write_readme(
    folder: Path,
    title: str,
    csv_name: str,
    source: str,
    regen: list[str],
    notes: list[str],
    descriptions: OrderedDict[str, str],
) -> None:
    lines = [
        f"# {title}",
        "",
        f"This README documents the district-level columns in `{csv_name}`.",
        "",
        f"Source: {source}",
        "",
        "## Files",
        "",
        f"- `{csv_name}`: District-level dataset.",
        "- `district_columns.py`: Importable column description dict and ordered key list.",
        "",
        "## How to regenerate",
        "",
        "```bash",
        *regen,
        "```",
        "",
        "## Columns",
        "",
        "| Column | Description |",
        "|--------|-------------|",
    ]

    for column, description in descriptions.items():
        lines.append(f"| `{column}` | {description} |")

    lines.extend(["", "## Notes", ""])
    for note in notes:
        lines.append(f"- {note}")
    lines.append("")

    (folder / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    for dataset in DATASETS:
        folder = BASE / dataset["folder"]
        csv_path = folder / dataset["csv"]
        descriptions = dataset["descriptions"]
        header = read_header(csv_path, dataset.get("header_format", "csv"))
        description_keys = list(descriptions.keys())
        if header != description_keys:
            raise ValueError(
                f"Header mismatch for {csv_path}: expected {description_keys}, got {header}"
            )

        write_metadata_module(folder, dataset["csv"], descriptions)
        if dataset.get("write_readme", True):
            write_readme(
                folder=folder,
                title=dataset["title"],
                csv_name=dataset["csv"],
                source=dataset["source"],
                regen=dataset["regen"],
                notes=dataset["notes"],
                descriptions=descriptions,
            )
        print(f"Updated metadata for {dataset['folder']}")


if __name__ == "__main__":
    main()
