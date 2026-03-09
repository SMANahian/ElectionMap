"""
Extract subnational population statistics from HumData COD-PS Bangladesh dataset.

Source: https://data.humdata.org/dataset/cod-ps-bgd
Raw files in raw/ directory (downloaded CSVs and XLSX).

Produces:
  - pop_district.csv: District-level (ADM2) population by sex and age group
  - pop_upazila.csv: Upazila-level (ADM3) population by sex and age group
  - pop_division.csv: Division-level (ADM1) population by sex and age group
"""
import pandas as pd
import os

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")

AGE_GROUPS = [
    '00_04', '05_09', '10_14', '15_19', '20_24', '25_29', '30_34', '35_39',
    '40_44', '45_49', '50_54', '55_59', '60_64', '65_69', '70_74', '75_79', '80Plus'
]


def process_level(csv_file, admin_cols, name_col, pcode_col):
    """Read a raw CSV and reshape into a clean output."""
    df = pd.read_csv(os.path.join(RAW_DIR, csv_file))

    # Keep admin columns + all population columns
    keep = admin_cols.copy()

    # Total population
    keep += ['F_TL', 'M_TL', 'T_TL']

    # Age-sex columns
    for prefix in ['F', 'M', 'T']:
        for ag in AGE_GROUPS:
            col = f'{prefix}_{ag}'
            if col in df.columns:
                keep.append(col)

    df = df[[c for c in keep if c in df.columns]].copy()

    # Rename admin columns for clarity
    rename = {
        'ADM1_NAME': 'division', 'ADM1_PCODE': 'division_pcode',
        'ADM2_NAME': 'district', 'ADM2_PCODE': 'district_pcode',
        'ADM3_NAME': 'upazila', 'ADM3_PCODE': 'upazila_pcode',
        'F_TL': 'female_total', 'M_TL': 'male_total', 'T_TL': 'total_population',
    }
    # Rename age-sex columns to readable names
    for prefix, label in [('F', 'female'), ('M', 'male'), ('T', 'total')]:
        for ag in AGE_GROUPS:
            old = f'{prefix}_{ag}'
            new = f'{label}_{ag.lower()}'
            rename[old] = new

    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Drop metadata columns
    for col in ['year', 'ISO3', 'ADM0_NAME', 'ADM0_PCODE']:
        if col in df.columns:
            df = df.drop(columns=[col])

    return df


def main():
    out_dir = os.path.dirname(__file__)

    # Division level (ADM1)
    print("Processing ADM1 (divisions)...")
    div_df = process_level(
        'bgd_admpop_adm1_2022.csv',
        admin_cols=['ADM1_NAME', 'ADM1_PCODE'],
        name_col='ADM1_NAME', pcode_col='ADM1_PCODE'
    )
    div_path = os.path.join(out_dir, "pop_division.csv")
    div_df.to_csv(div_path, index=False)
    print(f"  {len(div_df)} divisions, {len(div_df.columns)} columns -> {div_path}")

    # District level (ADM2)
    print("Processing ADM2 (districts)...")
    dist_df = process_level(
        'bgd_admpop_adm2_2022.csv',
        admin_cols=['ADM1_NAME', 'ADM1_PCODE', 'ADM2_NAME', 'ADM2_PCODE'],
        name_col='ADM2_NAME', pcode_col='ADM2_PCODE'
    )
    dist_path = os.path.join(out_dir, "pop_district.csv")
    dist_df.to_csv(dist_path, index=False)
    print(f"  {len(dist_df)} districts, {len(dist_df.columns)} columns -> {dist_path}")

    # Upazila level (ADM3)
    print("Processing ADM3 (upazilas)...")
    upz_df = process_level(
        'bgd_admpop_adm3_2022.csv',
        admin_cols=['ADM1_NAME', 'ADM1_PCODE', 'ADM2_NAME', 'ADM2_PCODE',
                    'ADM3_NAME', 'ADM3_PCODE'],
        name_col='ADM3_NAME', pcode_col='ADM3_PCODE'
    )
    upz_path = os.path.join(out_dir, "pop_upazila.csv")
    upz_df.to_csv(upz_path, index=False)
    print(f"  {len(upz_df)} upazilas, {len(upz_df.columns)} columns -> {upz_path}")

    # Validation
    print(f"\n--- Validation ---")
    print(f"Divisions: {len(div_df)}")
    print(f"Districts: {len(dist_df)}")
    print(f"Upazilas: {len(upz_df)}")

    # Check totals match
    div_total = div_df['total_population'].sum()
    dist_total = dist_df['total_population'].sum()
    upz_total = upz_df['total_population'].sum()
    print(f"\nPopulation totals: div={div_total:,}, dist={dist_total:,}, upz={upz_total:,}")
    if div_total == dist_total == upz_total:
        print("  All levels match!")
    else:
        print("  WARNING: Totals don't match across levels")

    # Missing values
    for name, df in [('Division', div_df), ('District', dist_df), ('Upazila', upz_df)]:
        missing = df.isna().sum().sum()
        if missing > 0:
            print(f"  {name}: {missing} missing values")

    # Sample
    print(f"\nSample district data:")
    print(dist_df[['division', 'district', 'total_population', 'male_total', 'female_total']].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
