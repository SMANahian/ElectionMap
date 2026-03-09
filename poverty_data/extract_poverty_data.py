"""
Extract poverty data from 'Poverty Map of Bangladesh 2022' PDF (ELR 3605.pdf).

Produces:
  - poverty_district.csv: District-level poverty data (with upazila data aggregated)
  - poverty_upazila.csv: Upazila-level poverty data

Data from:
  Annex 1: Poverty rates (UPL) 2022 and 2010 — Population, Quintile, HCR%, SE%
  Annex 2: Extreme poverty categories (LPL) 2022 — Low/Moderate/High
"""
import pdfplumber
import pandas as pd
import re
import os

PDF_PATH = os.path.join(os.path.dirname(__file__), "ELR 3605.pdf")


def extract_annex1(pdf):
    """Extract Annex 1: Division, District and Upazila Level Poverty Rates of 2022 and 2010."""
    rows = []
    # Annex 1 spans pages 58-75 (0-indexed 57-74)
    for page_idx in range(57, 75):
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                # Skip header rows and empty rows
                if not row or not row[0]:
                    continue
                name = str(row[0]).strip()
                if not name or name.startswith('Name') or name.startswith('Division') or 'ANNEX' in name:
                    continue
                if name in ('2022', '201021', 'HCR', 'Quintile', 'Standard', 'Upper', 'Error (%)', '(%)'):
                    continue
                # Skip footnotes
                if name.startswith('20') and 'General' in str(row):
                    continue
                if name.startswith('21') and 'figures' in str(row):
                    continue
                if name.startswith('|') or name.startswith('Source'):
                    continue
                rows.append(row)
    return rows


def parse_annex1_rows(raw_rows):
    """Parse extracted rows into structured records."""
    records = []
    current_division = None
    current_district = None

    for row in raw_rows:
        # Clean up the row
        cells = [str(c).strip() if c else '' for c in row]
        raw_name = cells[0]

        if not raw_name or raw_name in ('None', ''):
            continue

        # Determine level BEFORE cleaning newlines (Division/District may be on next line)
        full_name = ' '.join(raw_name.split())  # normalize whitespace including newlines
        is_division = 'Division' in full_name and 'District' not in full_name
        is_district = 'District' in full_name

        # Clean name for output
        name = re.sub(r'\s*(Division|District)\s*', ' ', full_name).strip()
        name = re.sub(r'\| \d+$', '', name).strip()
        name = re.sub(r'\s+', ' ', name).strip()

        if not name:
            continue

        if is_division:
            current_division = name
        elif is_district:
            current_district = name

        # Try to extract numeric data
        # Expected: name, population, quintile_2022, hcr_2022, se_2022, quintile_2010, hcr_2010, se_2010
        if len(cells) >= 5:
            record = {
                'name': name,
                'division': current_division,
                'is_division': is_division,
                'is_district': is_district,
            }

            # Parse population (column 1)
            pop_str = cells[1] if len(cells) > 1 else ''
            pop_str = re.sub(r'[,\s]', '', pop_str)
            try:
                record['population'] = int(pop_str)
            except (ValueError, TypeError):
                record['population'] = None

            # Parse 2022 data
            if len(cells) >= 5:
                record['quintile_2022'] = cells[2] if len(cells) > 2 else ''
                try:
                    record['poverty_rate_2022'] = float(cells[3]) if cells[3] else None
                except (ValueError, TypeError):
                    record['poverty_rate_2022'] = None
                try:
                    record['se_2022'] = float(cells[4]) if cells[4] else None
                except (ValueError, TypeError):
                    record['se_2022'] = None

            # Parse 2010 data
            if len(cells) >= 8:
                record['quintile_2010'] = cells[5] if len(cells) > 5 else ''
                try:
                    record['poverty_rate_2010'] = float(cells[6]) if cells[6] else None
                except (ValueError, TypeError):
                    record['poverty_rate_2010'] = None
                try:
                    record['se_2010'] = float(cells[7]) if cells[7] else None
                except (ValueError, TypeError):
                    record['se_2010'] = None

            records.append(record)

    return records


def extract_annex2(pdf):
    """Extract Annex 2: Extreme Poverty categories (LPL) 2022."""
    extreme_poverty = {}
    # Annex 2 spans pages 76-84 (0-indexed 75-83)
    for page_idx in range(75, 84):
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or not row[0]:
                    continue
                name = str(row[0]).strip()
                if not name or 'Division, District' in name or 'Legend' in name or 'ANNEX' in name:
                    continue
                legend = str(row[1]).strip() if len(row) > 1 and row[1] else ''
                if legend in ('Low', 'Moderate', 'High'):
                    # Clean name
                    name = re.sub(r'\n.*', '', name).strip()
                    extreme_poverty[name] = legend
    return extreme_poverty


def classify_rows(records):
    """Classify each record as division/district/upazila and assign parent district."""
    classified = []
    current_division = None
    current_district = None

    for r in records:
        name = r['name']
        is_div = r.get('is_division', False)
        is_dist = r.get('is_district', False)

        if is_div:
            current_division = name.replace(' Division', '').strip()
            current_division = re.sub(r'\s*(Division|division).*', '', current_division).strip()
            r['level'] = 'division'
            r['division'] = current_division
            r['district'] = None
        elif is_dist:
            current_district = name.replace(' District', '').strip()
            r['level'] = 'district'
            r['division'] = current_division
            r['district'] = current_district
        else:
            r['level'] = 'upazila'
            r['division'] = current_division
            r['district'] = current_district

        classified.append(r)
    return classified


def main():
    pdf = pdfplumber.open(PDF_PATH)

    # ---- Extract Annex 1 ----
    print("Extracting Annex 1 (Poverty Rates 2022 & 2010)...")
    raw_rows = extract_annex1(pdf)
    print(f"  Raw rows extracted: {len(raw_rows)}")

    records = parse_annex1_rows(raw_rows)
    print(f"  Parsed records: {len(records)}")

    records = classify_rows(records)

    # ---- Extract Annex 2 ----
    print("Extracting Annex 2 (Extreme Poverty Categories)...")
    extreme_poverty = extract_annex2(pdf)
    print(f"  Extreme poverty entries: {len(extreme_poverty)}")

    # Match extreme poverty to records
    for r in records:
        name = r['name']
        level = 'division' if r.get('is_division') else ('district' if r.get('is_district') else 'upazila')

        # Try multiple name variants — prioritize suffixed versions for district/division
        if r.get('is_district'):
            candidates = [f"{name} District", name]
        elif r.get('is_division'):
            candidates = [f"{name} Division", name]
        else:
            candidates = [name, f"{name} District", f"{name} Division"]
        # For upazilas, also try with Sadar variants
        if 'Sadar' in name:
            base = name.replace(' Sadar', '').strip()
            candidates.append(f"{base} Sadar")
            candidates.append(f"{base} Sadar (Kotwali)")

        ep = None
        for c in candidates:
            if c in extreme_poverty:
                ep = extreme_poverty[c]
                break
        # Fuzzy fallback: normalize both sides and compare
        if not ep:
            norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
            name_norm = norm(name)
            for k, v in extreme_poverty.items():
                k_norm = norm(k.replace(' District', '').replace(' Division', ''))
                if name_norm in k_norm or k_norm in name_norm or name_norm == k_norm:
                    ep = v
                    break
            # Last resort: first 6 chars match
            if not ep:
                for k, v in extreme_poverty.items():
                    k_norm = norm(k)
                    if len(name_norm) >= 6 and name_norm[:6] == k_norm[:6] and abs(len(name_norm) - len(k_norm)) <= 3:
                        ep = v
                        break
        r['extreme_poverty_category'] = ep or ''

    # Build DataFrames
    df = pd.DataFrame(records)

    # Clean up quintile strings
    for col in ['quintile_2022', 'quintile_2010']:
        if col in df.columns:
            df[col] = df[col].str.replace(r'\n.*', '', regex=True).str.strip()

    # Separate into levels
    divisions = df[df['level'] == 'division'].copy()
    districts = df[df['level'] == 'district'].copy()
    upazilas = df[df['level'] == 'upazila'].copy()

    print(f"\n  Divisions: {len(divisions)}")
    print(f"  Districts: {len(districts)}")
    print(f"  Upazilas: {len(upazilas)}")

    # ---- Build district-level CSV ----
    district_df = districts[['division', 'district', 'population',
                              'quintile_2022', 'poverty_rate_2022', 'se_2022',
                              'quintile_2010', 'poverty_rate_2010', 'se_2010',
                              'extreme_poverty_category']].copy()
    district_df.rename(columns={'district': 'name'}, inplace=True)

    # Calculate poverty change
    district_df['poverty_change_2010_2022'] = district_df['poverty_rate_2022'] - district_df['poverty_rate_2010']

    # Add division-level rows
    div_df = divisions[['division', 'population',
                         'quintile_2022', 'poverty_rate_2022', 'se_2022',
                         'quintile_2010', 'poverty_rate_2010', 'se_2010',
                         'extreme_poverty_category']].copy()
    div_df['name'] = div_df['division']
    div_df['poverty_change_2010_2022'] = div_df['poverty_rate_2022'] - div_df['poverty_rate_2010']

    # ---- Build upazila-level CSV ----
    upazila_df = upazilas[['division', 'district', 'name', 'population',
                            'quintile_2022', 'poverty_rate_2022', 'se_2022',
                            'quintile_2010', 'poverty_rate_2010', 'se_2010',
                            'extreme_poverty_category']].copy()
    # Clean upazila names
    upazila_df['name'] = upazila_df['name'].str.replace(r'\n.*', '', regex=True).str.strip()

    upazila_df['poverty_change_2010_2022'] = upazila_df['poverty_rate_2022'] - upazila_df['poverty_rate_2010']

    # Round
    for col in ['poverty_rate_2022', 'se_2022', 'poverty_rate_2010', 'se_2010', 'poverty_change_2010_2022']:
        if col in district_df.columns:
            district_df[col] = district_df[col].round(2)
        if col in upazila_df.columns:
            upazila_df[col] = upazila_df[col].round(2)

    # Save
    out_dir = os.path.dirname(__file__)
    district_path = os.path.join(out_dir, "poverty_district.csv")
    upazila_path = os.path.join(out_dir, "poverty_upazila.csv")

    district_df.to_csv(district_path, index=False)
    upazila_df.to_csv(upazila_path, index=False)

    print(f"\nSaved {len(district_df)} districts to {district_path}")
    print(f"Saved {len(upazila_df)} upazilas to {upazila_path}")
    print(f"\nDistrict columns: {list(district_df.columns)}")
    print(f"Upazila columns: {list(upazila_df.columns)}")

    # Validation
    print(f"\n--- Validation ---")
    print(f"Districts with missing poverty_rate_2022: {district_df['poverty_rate_2022'].isna().sum()}")
    print(f"Upazilas with missing poverty_rate_2022: {upazila_df['poverty_rate_2022'].isna().sum()}")
    print(f"Districts with missing extreme_poverty: {(district_df['extreme_poverty_category'] == '').sum()}")
    print(f"Upazilas with missing extreme_poverty: {(upazila_df['extreme_poverty_category'] == '').sum()}")

    # Show sample
    print(f"\nSample district data:")
    print(district_df.head(10).to_string(index=False))

    pdf.close()


if __name__ == "__main__":
    main()
