"""
Extract census data from PHC Preliminary Report 2022 PDF.

Produces:
  - census_district.csv: All district-level data (Annex Tables A-1.1 to A-1.13)
  - census_division.csv: Division-level data (body Tables + Annex Tables A-1.5, A-1.8-A-1.10)

Source: PHC_Preliminary_Report_August_2022.pdf
"""
import pandas as pd
import re
import os
import subprocess

PDF_PATH = os.path.join(os.path.dirname(__file__), "PHC_Preliminary_Report_August_2022.pdf")

DIVISIONS = {'Barishal', 'Chattogram', 'Dhaka', 'Khulna', 'Mymensingh', 'Rajshahi', 'Rangpur', 'Sylhet'}
DIVISION_ORDER = sorted(DIVISIONS)

DISTRICT_TO_DIVISION = {}
for div, dists in {
    'Barishal': ['Barguna', 'Barishal', 'Bhola', 'Jhalokati', 'Patuakhali', 'Pirojpur'],
    'Chattogram': ['Bandarban', 'Brahmanbaria', 'Chandpur', 'Chattogram', 'Cumilla',
                   "Cox's Bazar", 'Feni', 'Khagrachhari', 'Lakshmipur', 'Noakhali', 'Rangamati'],
    'Dhaka': ['Dhaka', 'Faridpur', 'Gazipur', 'Gopalganj', 'Kishoregonj', 'Madaripur',
              'Manikganj', 'Munshiganj', 'Narayanganj', 'Narsingdi', 'Rajbari', 'Shariatpur', 'Tangail'],
    'Khulna': ['Bagerhat', 'Chuadanga', 'Jashore', 'Jhenaidah', 'Khulna', 'Kushtia',
               'Magura', 'Meherpur', 'Narail', 'Satkhira'],
    'Mymensingh': ['Jamalpur', 'Mymensingh', 'Netrakona', 'Sherpur'],
    'Rajshahi': ['Bogura', 'Joypurhat', 'Naogaon', 'Natore', 'Chapainawabganj',
                 'Pabna', 'Rajshahi', 'Sirajganj'],
    'Rangpur': ['Dinajpur', 'Gaibandha', 'Kurigram', 'Lalmonirhat', 'Nilphamari',
                'Panchagarh', 'Rangpur', 'Thakurgaon'],
    'Sylhet': ['Habiganj', 'Moulvibazar', 'Sunamganj', 'Sylhet'],
}.items():
    for d in dists:
        DISTRICT_TO_DIVISION[d] = div


def clean_num(s):
    s = str(s).strip().replace(',', '')
    if not s or s == '-':
        return None
    try:
        return int(s) if '.' not in s else float(s)
    except ValueError:
        return None


def parse_line(line):
    """Parse a data line: extract name and all numbers."""
    line = line.strip()
    if not line:
        return None, []

    # Match name (letters, spaces, apostrophes, hyphens) followed by numbers
    m = re.match(r"^([A-Za-z][A-Za-z\u2019'\s\.\-\*]*?)\s{2,}(.+)$", line)
    if not m:
        # Try: name might be just one word followed by numbers with single space
        m = re.match(r"^([A-Za-z][A-Za-z\u2019'\-\*]+)\s+(\d[\d,\.\s]+.*)$", line)
    if not m:
        return None, []

    name = m.group(1).strip().replace('\u2019', "'").rstrip('*')
    nums = [clean_num(n) for n in re.findall(r'[\d,]+\.?\d*', m.group(2))]
    return name, nums


def extract_table(lines, start_marker, end_marker, col_names, min_cols, skip_names=None):
    """Generic table extractor between markers.

    Returns dict with keys: 'divisions' and 'districts'.
    Division rows are identified by being in DIVISIONS set and appearing
    before their child district rows. Districts with the same name as their
    division are distinguished by position.
    """
    if skip_names is None:
        skip_names = {'National', 'Bangladesh', ''}

    collecting = False
    divisions = {}
    districts = {}
    current_division = None

    for line in lines:
        if start_marker in line:
            collecting = True
            continue
        if collecting and end_marker in line:
            break
        if not collecting:
            continue

        # Skip non-data lines
        stripped = line.strip()
        if not stripped or stripped.startswith('Population and Housing'):
            continue
        if stripped[0].isdigit() and len(stripped) < 15:
            continue

        name, nums = parse_line(stripped)
        if not name or name in skip_names:
            continue

        if name in DIVISIONS and name != current_division:
            # First occurrence of a division name = division row
            current_division = name
            if len(nums) >= min_cols:
                record = {}
                for i, col in enumerate(col_names):
                    record[col] = nums[i] if i < len(nums) else None
                divisions[name] = record
        elif len(nums) >= min_cols:
            record = {}
            for i, col in enumerate(col_names):
                record[col] = nums[i] if i < len(nums) else None
            districts[name] = record

    return {'divisions': divisions, 'districts': districts}


def main():
    print("Extracting text from PDF...")
    result = subprocess.run(['pdftotext', '-layout', PDF_PATH, '-'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    print(f"  {len(lines)} lines")

    # ===== DISTRICT-LEVEL TABLES =====

    # Table A-1.1: Population and Sex Ratio
    print("\nTable A-1.1 (Population & Sex Ratio)...")
    a11_raw = extract_table(lines, 'Table A-1.1', 'Table A-1.2',
                        ['total_population', 'male_population', 'female_population',
                         'hijra_population', '_total_mf', 'sex_ratio'], 5)
    # Remove the redundant _total_mf column
    for r in list(a11_raw['divisions'].values()) + list(a11_raw['districts'].values()):
        r.pop('_total_mf', None)
    print(f"  {len(a11_raw['districts'])} districts, {len(a11_raw['divisions'])} divisions")

    # Table A-1.2: Rural-Urban Population
    print("Table A-1.2 (Rural-Urban Population)...")
    a12_raw = extract_table(lines, 'Table A-1.2', 'Table A-1.3',
                        ['rural_male', 'rural_female', 'rural_hijra', 'rural_total',
                         'urban_male', 'urban_female', 'urban_hijra', 'urban_total'], 7)
    print(f"  {len(a12_raw['districts'])} districts, {len(a12_raw['divisions'])} divisions")

    # Table A-1.3: Ethnic Minority
    print("Table A-1.3 (Ethnic Minority)...")
    a13_raw = extract_table(lines, 'Table A-1.3', 'Table A-1.4',
                        ['ethnic_minority_total', 'ethnic_minority_male',
                         'ethnic_minority_female', 'ethnic_minority_pct'], 3)
    print(f"  {len(a13_raw['districts'])} districts, {len(a13_raw['divisions'])} divisions")

    # Table A-1.6: Religion
    print("Table A-1.6 (Religion)...")
    a16_raw = extract_table(lines, 'Table A-1.6', 'Table A-1.7',
                        ['pct_muslim', 'pct_hindu', 'pct_buddhist',
                         'pct_christian', 'pct_other_religion'], 4)
    print(f"  {len(a16_raw['districts'])} districts, {len(a16_raw['divisions'])} divisions")

    # Table A-1.7: Literacy Rate
    print("Table A-1.7 (Literacy Rate)...")
    a17_raw = extract_table(lines, 'Table A-1.7', 'Table A-1.8',
                        ['literacy_rate_total', 'literacy_rate_male',
                         'literacy_rate_female', 'literacy_rate_hijra'], 2)
    print(f"  {len(a17_raw['districts'])} districts, {len(a17_raw['divisions'])} divisions")

    # Table A-1.11: Households & Dwelling Types
    print("Table A-1.11 (Households & Dwelling)...")
    a111_raw = extract_table(lines, 'Table A-1.11', 'Table A-1.12',
                         ['total_households', 'slum_households', 'slum_population',
                          'floating_households', 'floating_population',
                          'regular_households', 'regular_population', 'household_size'], 7)
    print(f"  {len(a111_raw['districts'])} districts, {len(a111_raw['divisions'])} divisions")

    # Table A-1.12: Population, HH, HH Size, Density (2011 vs 2022)
    print("Table A-1.12 (Density & HH Size)...")
    a112_raw = extract_table(lines, 'Table A-1.12', 'Table A-1.13',
                         ['population_2011', 'households_2011', 'hh_size_2011', 'density_2011',
                          'population_2022', 'households_2022', 'hh_size_2022', 'density_2022'], 7)
    print(f"  {len(a112_raw['districts'])} districts, {len(a112_raw['divisions'])} divisions")

    # Table A-1.13: Dwelling Units
    print("Table A-1.13 (Dwelling Units)...")
    a113_raw = extract_table(lines, 'Table A-1.13', 'Annex 2',
                         ['dwelling_units_rural', 'dwelling_units_urban', 'dwelling_units_total'], 2)
    print(f"  {len(a113_raw['districts'])} districts, {len(a113_raw['divisions'])} divisions")

    # ===== MERGE DISTRICT DATA =====
    all_tables = [a11_raw, a12_raw, a13_raw, a16_raw, a17_raw, a111_raw, a112_raw, a113_raw]
    all_district_names = set()
    for t in all_tables:
        all_district_names.update(t['districts'].keys())

    district_names = sorted(all_district_names)

    rows = []
    for name in district_names:
        row = {'district': name, 'division': DISTRICT_TO_DIVISION.get(name, '')}
        for t in all_tables:
            if name in t['districts']:
                row.update(t['districts'][name])
        rows.append(row)

    district_df = pd.DataFrame(rows)
    first_cols = ['division', 'district']
    other_cols = [c for c in district_df.columns if c not in first_cols]
    district_df = district_df[first_cols + other_cols]

    # ===== DIVISION-LEVEL TABLES =====
    print("\nParsing division-level tables...")
    div_data = {d: {} for d in DIVISION_ORDER}

    # Add division rows from district tables
    for t in all_tables:
        for d in DIVISION_ORDER:
            if d in t['divisions']:
                div_data[d].update(t['divisions'][d])

    # Table A-1.5: Marital Status (division-level)
    is_male = True
    collecting = False
    for line in lines:
        if 'Table A-1.5' in line:
            collecting = True
            continue
        if collecting and 'Table A-1.6' in line:
            break
        if not collecting:
            continue
        stripped = line.strip()
        if 'Female' in stripped and not any(d in stripped for d in DIVISIONS):
            is_male = False
            continue
        if 'Male' in stripped and not any(d in stripped for d in DIVISIONS):
            is_male = True
            continue
        name, nums = parse_line(stripped)
        if name in DIVISIONS and len(nums) >= 5:
            prefix = 'male_' if is_male else 'female_'
            # nums: total(100), unmarried, married, widowed, divorced, separated
            div_data[name][f'{prefix}unmarried_pct'] = nums[1]
            div_data[name][f'{prefix}married_pct'] = nums[2]
            div_data[name][f'{prefix}widowed_pct'] = nums[3]
            div_data[name][f'{prefix}divorced_pct'] = nums[4]
            if len(nums) > 5:
                div_data[name][f'{prefix}separated_pct'] = nums[5]

    # Table A-1.8: Dependency Ratio (division-level)
    collecting = False
    for line in lines:
        if 'Table A-1.8' in line:
            collecting = True
            continue
        if collecting and 'Table A-1.9' in line:
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 12:
            div_data[name]['dependency_ratio_total'] = nums[3]
            div_data[name]['dependency_ratio_rural'] = nums[7]
            div_data[name]['dependency_ratio_urban'] = nums[11]

    # Table A-1.9: Mobile Phone Users (division-level)
    collecting = False
    for line in lines:
        if 'Table A-1.9' in line:
            collecting = True
            continue
        if collecting and ('Table A-1.10' in line or 'Table 2' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 3:
            div_data[name]['mobile_users_total_pct'] = nums[0]
            div_data[name]['mobile_users_male_pct'] = nums[1]
            div_data[name]['mobile_users_female_pct'] = nums[2]
            if len(nums) >= 6:
                div_data[name]['mobile_users_rural_total_pct'] = nums[3]
                div_data[name]['mobile_users_rural_male_pct'] = nums[4]
                div_data[name]['mobile_users_rural_female_pct'] = nums[5]
            if len(nums) >= 9:
                div_data[name]['mobile_users_urban_total_pct'] = nums[6]
                div_data[name]['mobile_users_urban_male_pct'] = nums[7]
                div_data[name]['mobile_users_urban_female_pct'] = nums[8]

    # Table A-1.10: Internet Users (division-level)
    collecting = False
    for line in lines:
        if 'Table A-1.10' in line:
            collecting = True
            continue
        if collecting and 'Table A-1.11' in line:
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 3:
            div_data[name]['internet_users_total_pct'] = nums[0]
            div_data[name]['internet_users_male_pct'] = nums[1]
            div_data[name]['internet_users_female_pct'] = nums[2]
            if len(nums) >= 6:
                div_data[name]['internet_users_rural_total_pct'] = nums[3]
                div_data[name]['internet_users_rural_male_pct'] = nums[4]
                div_data[name]['internet_users_rural_female_pct'] = nums[5]
            if len(nums) >= 9:
                div_data[name]['internet_users_urban_total_pct'] = nums[6]
                div_data[name]['internet_users_urban_male_pct'] = nums[7]
                div_data[name]['internet_users_urban_female_pct'] = nums[8]

    # Body Table 2.4: Growth Rate
    collecting = False
    for line in lines:
        if 'Table 2.4' in line and 'Growth' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.5' in line or 'Table 2.4 shows' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name and name in DIVISIONS and nums:
            div_data[name]['growth_rate_2022'] = nums[-1]

    # Body Table 2.10: Floating Population
    collecting = False
    for line in lines:
        if 'Table 2.10' in line and 'Floating' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.10 depicts' in line or line.strip().startswith('*')):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and nums:
            div_data[name]['floating_pop_total'] = nums[0]
            if len(nums) > 1:
                div_data[name]['floating_pop_male'] = nums[1]
            if len(nums) > 2:
                div_data[name]['floating_pop_female'] = nums[2]

    # Table 2.9: Population by Type of Dwelling (division-level)
    collecting = False
    for line in lines:
        if 'Table 2.9' in line and 'Dwelling' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.9 shows' in line or 'Table 2.10' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 4:
            div_data[name]['dwelling_total_pop'] = nums[0]
            div_data[name]['dwelling_slum_pop'] = nums[1]
            div_data[name]['dwelling_floating_pop'] = nums[2]
            div_data[name]['dwelling_others_pop'] = nums[3]

    # Table 2.13: Child-Woman Ratio (division-level)
    collecting = False
    for line in lines:
        if 'Table 2.13' in line and 'Child' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.13 portrays' in line or 'Table 2.14' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 3:
            div_data[name]['child_woman_ratio_total'] = nums[0]
            div_data[name]['child_woman_ratio_rural'] = nums[1]
            div_data[name]['child_woman_ratio_urban'] = nums[2]

    # Table 2.18: Persons with Disabilities (division-level)
    collecting = False
    for line in lines:
        if 'Table 2.18' in line and 'Disabilit' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.18 portrays' in line or 'Table 2.19' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 6:
            div_data[name]['disability_total'] = nums[0]
            div_data[name]['disability_rate_total'] = nums[1]
            div_data[name]['disability_male'] = nums[2]
            div_data[name]['disability_rate_male'] = nums[3]
            div_data[name]['disability_female'] = nums[4]
            div_data[name]['disability_rate_female'] = nums[5]

    # Body Table 2.11: Population Density (historical, division-level)
    collecting = False
    for line in lines:
        if 'Table 2.11' in line and 'Density' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.11 displays' in line or (line.strip().startswith('*') and 'Division' in line)):
            break
        if not collecting:
            continue
        stripped = line.strip()
        name_raw, _ = parse_line(stripped)
        if not name_raw:
            continue
        name = re.sub(r'\*+$', '', name_raw).strip()
        if name in DIVISIONS:
            remainder = stripped[stripped.index(name) + len(name):]
            # Strip trailing asterisks from remainder too
            remainder = re.sub(r'\*+', '', remainder)
            tokens = re.findall(r'[\d,]+\.?\d*|-', remainder)
            density_cols = ['density_1974', 'density_1981', 'density_1991',
                            'density_2001', 'density_2011_body', 'density_2022_body']
            for i, col in enumerate(density_cols):
                if i < len(tokens):
                    val = clean_num(tokens[i])
                    if val is not None:
                        div_data[name][col] = val

    # Table 2.5: Sex Ratio historical (division-level)
    # Uses positional parsing because some cells contain '-' which we must preserve as None
    collecting = False
    for line in lines:
        if 'Table 2.5' in line and 'Sex Ratio' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.5 illustrates' in line or 'Figure' in line):
            break
        if not collecting:
            continue
        stripped = line.strip()
        name_raw, _ = parse_line(stripped)
        if not name_raw:
            continue
        name = re.sub(r'\*+$', '', name_raw).strip()
        if name in DIVISIONS:
            # Parse all tokens (numbers and dashes) from the remainder
            remainder = stripped[stripped.index(name) + len(name):]
            tokens = re.findall(r'[\d,]+\.?\d*|-', remainder)
            col_names_sr = ['sex_ratio_1974', 'sex_ratio_1981', 'sex_ratio_1991',
                            'sex_ratio_2001', 'sex_ratio_2011', 'sex_ratio_2022']
            for i, col in enumerate(col_names_sr):
                if i < len(tokens):
                    val = clean_num(tokens[i])
                    if val is not None:
                        div_data[name][col] = val

    # Table 2.7: City Corporation Population (separate CSV)
    city_corp_rows = []
    collecting = False
    for line in lines:
        if 'Table 2.7' in line and 'City Corporation' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 2.7 shows' in line or 'Table 2.8' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name and len(nums) >= 5:
            city_corp_rows.append({
                'city_corporation': name,
                'total_population': nums[0],
                'male_population': nums[1],
                'female_population': nums[2],
                'hijra_population': nums[3],
                'density': nums[4],
            })

    # Table 3.3: Households by Location (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.3' in line and 'Household' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.3 delineates' in line or 'Table 3.4' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 6:
            div_data[name]['hh_total_3_3'] = nums[0]
            div_data[name]['hh_rural'] = nums[1]
            div_data[name]['hh_urban'] = nums[2]
            div_data[name]['hh_size_total_3_3'] = nums[3]
            div_data[name]['hh_size_rural'] = nums[4]
            div_data[name]['hh_size_urban'] = nums[5]

    # Table 3.4: Households by Type of Dwelling (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.4' in line and 'Dwelling' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.4 depicts' in line or 'Table 3.5' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 4:
            div_data[name]['hh_total_3_4'] = nums[0]
            div_data[name]['hh_slum'] = nums[1]
            div_data[name]['hh_floating'] = nums[2]
            div_data[name]['hh_others'] = nums[3]

    # Table 3.5: Dwelling Units (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.5' in line and 'Dwelling' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.5 presents' in line or 'Table 3.6' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 3:
            div_data[name]['dwelling_units_total_body'] = nums[0]
            div_data[name]['dwelling_units_rural_body'] = nums[1]
            div_data[name]['dwelling_units_urban_body'] = nums[2]

    # Table 3.6: Drinking Water Sources (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.6' in line and 'Water' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.6 displays' in line or 'Figure' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 9:
            div_data[name]['water_pct_pipe'] = nums[1]
            div_data[name]['water_pct_tubewell'] = nums[2]
            div_data[name]['water_pct_bottled'] = nums[3]
            div_data[name]['water_pct_well'] = nums[4]
            div_data[name]['water_pct_pond_river'] = nums[5]
            div_data[name]['water_pct_spring'] = nums[6]
            div_data[name]['water_pct_rain'] = nums[7]
            div_data[name]['water_pct_others'] = nums[8]

    # Table 3.7: Toilet Facilities (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.7' in line and 'Toilet' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.7 portrays' in line or 'Figure' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 7:
            div_data[name]['toilet_pct_safe_flush'] = nums[1]
            div_data[name]['toilet_pct_unsafe_flush'] = nums[2]
            div_data[name]['toilet_pct_pit_slab'] = nums[3]
            div_data[name]['toilet_pct_pit_no_slab'] = nums[4]
            div_data[name]['toilet_pct_kutcha'] = nums[5]
            div_data[name]['toilet_pct_open_defecation'] = nums[6]

    # Table 3.8: Electricity Sources (division-level)
    collecting = False
    for line in lines:
        if 'Table 3.8' in line and 'Electricity' in line and '...' not in line:
            collecting = True
            continue
        if collecting and ('Table 3.8 provides' in line or 'Figure' in line):
            break
        if not collecting:
            continue
        name, nums = parse_line(line.strip())
        if name in DIVISIONS and len(nums) >= 5:
            div_data[name]['electricity_pct_grid'] = nums[1]
            div_data[name]['electricity_pct_solar'] = nums[2]
            div_data[name]['electricity_pct_others'] = nums[3]
            div_data[name]['electricity_pct_none'] = nums[4]

    div_rows = []
    for d in DIVISION_ORDER:
        row = {'division': d}
        row.update(div_data.get(d, {}))
        div_rows.append(row)
    division_df = pd.DataFrame(div_rows)

    # ===== CITY CORPORATION CSV =====
    city_corp_df = pd.DataFrame(city_corp_rows) if city_corp_rows else pd.DataFrame()

    # ===== SAVE =====
    out_dir = os.path.dirname(__file__)
    dist_path = os.path.join(out_dir, "census_district.csv")
    div_path = os.path.join(out_dir, "census_division.csv")
    city_path = os.path.join(out_dir, "census_city_corporation.csv")

    district_df.to_csv(dist_path, index=False)
    division_df.to_csv(div_path, index=False)
    if not city_corp_df.empty:
        city_corp_df.to_csv(city_path, index=False)
        print(f"Saved {len(city_corp_df)} city corporations to {city_path}")

    print(f"\nSaved {len(district_df)} districts to {dist_path}")
    print(f"Saved {len(division_df)} divisions to {div_path}")
    print(f"\nDistrict columns ({len(district_df.columns)}): {list(district_df.columns)}")
    print(f"Division columns ({len(division_df.columns)}): {list(division_df.columns)}")

    # ===== VALIDATION =====
    print(f"\n--- Validation ---")
    print(f"Expected 64 districts, got {len(district_df)}")
    no_div = district_df[district_df['division'] == '']['district'].tolist()
    if no_div:
        print(f"  Without division: {no_div}")

    for col in district_df.columns[2:]:
        missing = district_df[col].isna().sum()
        if missing > 0:
            print(f"  {col}: {missing}/{len(district_df)} missing")

    # Spot checks
    print(f"\nSpot checks (from PDF):")
    for name, expected in [('Barguna', {'total_population': 1010530, 'sex_ratio': 95.93, 'literacy_rate_total': 80.49}),
                           ('Dhaka', {'total_population': 14734025, 'sex_ratio': 115.45}),
                           ('Rangamati', {'total_population': 647587})]:
        row = district_df[district_df['district'] == name]
        if len(row) == 0:
            print(f"  MISSING: {name}")
            continue
        r = row.iloc[0]
        for k, v in expected.items():
            actual = r.get(k)
            status = "OK" if actual == v else f"FAIL (got {actual})"
            print(f"  {name}.{k}: {status}")

    print(f"\nDivision spot checks:")
    for d in ['Barishal', 'Dhaka']:
        row = division_df[division_df['division'] == d].iloc[0]
        print(f"  {d}: pop={row.get('total_population')}, literacy={row.get('literacy_rate_total')}")


if __name__ == "__main__":
    main()
