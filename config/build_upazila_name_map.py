#!/usr/bin/env python3
"""
Build comprehensive upazila name mapping across all data sources.

Creates:
1. upazila_name_map.csv - Maps standard name to each source's spelling
2. upazila_name_aliases.json - Maps variant spellings to standard name
3. Updated upazila_constituency_map.csv - ALL upazilas, including those not in any constituency

Sources:
- humdata_pop_stats/pop_upazila.csv (humdata_pop)
- poverty_data/poverty_upazila.csv (poverty)
- seat_results.csv (election)
- bangladesh-geocode upazilas.json (geocode)
"""

import csv
import json
import os
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Input files
SEAT_RESULTS = os.path.join(BASE_DIR, "results", "seat_results.csv")
POP_UPAZILA = os.path.join(BASE_DIR, "humdata_pop_stats", "pop_upazila.csv")
POVERTY_UPAZILA = os.path.join(BASE_DIR, "poverty_data", "poverty_upazila.csv")
GEOCODE_UPAZILAS = "/tmp/bd_upazilas.json"
GEOCODE_DISTRICTS = "/tmp/bd_districts.json"

# Output files
NAME_MAP_CSV = os.path.join(BASE_DIR, "config", "upazila_name_map.csv")
ALIASES_JSON = os.path.join(BASE_DIR, "config", "upazila_name_aliases.json")
CONSTITUENCY_MAP = os.path.join(BASE_DIR, "config", "upazila_constituency_map.csv")
MISMATCH_REPORT = os.path.join(BASE_DIR, "config", "upazila_mismatch_report.txt")

# District name normalization (reuse existing)
DISTRICT_ALIASES_FILE = os.path.join(BASE_DIR, "config", "district_name_aliases.json")


def load_district_aliases():
    with open(DISTRICT_ALIASES_FILE) as f:
        return json.load(f)


def normalize_district(name, aliases):
    name = name.strip()
    return aliases.get(name, name)


def norm_key(name):
    """Create a normalized key for matching: lowercase, no special chars, no common suffixes."""
    s = name.strip().lower()
    s = re.sub(r'\s*\(partial\)', '', s)
    s = re.sub(r'\s*\(.*?\)', '', s)
    s = re.sub(r'\s+upazila$', '', s)
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_clean(name):
    """Clean an upazila name from election data."""
    s = name.strip()
    s = re.sub(r'\s*\(partial\)', '', s)
    s = re.sub(r'\s+Upazila$', '', s, flags=re.IGNORECASE)
    return s.strip()


def is_ward_or_number(name):
    """Check if entry is a city corporation ward number, not an upazila."""
    s = name.strip()
    # Pure numbers like "51", "52"
    if re.match(r'^\d+$', s):
        return True
    # Ranges like "16-24", "27-31)", "37-40", "38-41"
    if re.match(r'^\d+-\d+\)?$', s):
        return True
    # Trailing number with paren like "32)"
    if re.match(r'^\d+\)$', s):
        return True
    # Ward references
    if 'ward no' in s.lower():
        return True
    # "and Matuail Union Parishad Area"
    if s.lower().startswith('and '):
        return True
    # Union entries like "Basundia Union"
    if s.lower().endswith(' union'):
        return True
    return False


# ============================================================
# KNOWN SPELLING MAPPINGS (manually verified)
# Format: {variant_lower: standard_name}
# The standard name is chosen from the geocode source when available,
# falling back to the most commonly used modern spelling.
# ============================================================
KNOWN_MAPPINGS = {
    # Geocode uses different names than other sources
    "sadarsouth": "Comilla Sadar Dakshin",
    "comilla sadar": "Comilla Sadar",  # geocode name
    "cumilla sadar": "Comilla Sadar",
    "comilla adarsha sadar": "Comilla Sadar",  # poverty uses this
    "comilla sadar dakshin": "Comilla Sadar Dakshin",

    # Barishal variations
    "barisal sadar (kotwali)": "Barishal Sadar",
    "barisal sadar": "Barishal Sadar",
    "barishal sadar": "Barishal Sadar",

    # Bogura/Bogra
    "bogra sadar": "Bogura Sadar",
    "bogura sadar": "Bogura Sadar",

    # Spacing variations
    "banari para": "Banaripara",
    "banaripara": "Banaripara",
    "bagati para": "Bagatipara",
    "bagatipara": "Bagatipara",
    "bagher para": "Bagherpara",
    "bagherpara": "Bagherpara",
    "bagerpara": "Bagherpara",
    "brahman para": "Brahmanpara",
    "brahmanpara": "Brahmanpara",
    "char fasson": "Charfasson",
    "charfasson": "Charfasson",
    "kotali para": "Kotalipara",
    "kotalipara": "Kotalipara",
    "kuliar char": "Kuliarchar",
    "kuliarchar": "Kuliarchar",
    "haim char": "Haimchar",
    "haimchar": "Haimchar",
    "balia kandi": "Baliakandi",
    "baliakandi": "Baliakandi",
    "mujib nagar": "Mujibnagar",
    "mujibnagar": "Mujibnagar",
    "jiban nagar": "Jibannagar",
    "jibannagar": "Jibannagar",
    "kamrangir char": "Kamrangichar",
    "kamrangichar": "Kamrangichar",
    "tungi para": "Tungipara",
    "tungipara": "Tungipara",

    # Geocode-specific spelling variants (geocode -> standard from humdata/poverty/election)
    "badalgachi": "Badalgachhi",
    "badalgachhi": "Badalgachhi",
    "badargonj": "Badarganj",
    "badarganj": "Badarganj",
    "baghaichari": "Baghaichhari",
    "belaichari": "Belaichhari",
    "bokshiganj": "Bakshiganj",
    "bakshiganj": "Bakshiganj",
    "borhan sddin": "Burhanuddin",
    "botiaghata": "Batiaghata",
    "batiaghata": "Batiaghata",
    "charfesson": "Charfasson",
    "charrajibpur": "Char Rajibpur",
    "chougachha": "Chaugachha",
    "chaugachha": "Chaugachha",
    "coxsbazar sadar": "Cox's Bazar Sadar",
    "cox's bazar sadar": "Cox's Bazar Sadar",
    "dakop": "Dacope",
    "dacope": "Dacope",
    "dakshinsurma": "Dakshin Surma",
    "dewangonj": "Dewanganj",
    "dewanganj": "Dewanganj",
    "dhunot": "Dhunat",
    "dhunat": "Dhunat",
    "digholia": "Dighalia",
    "dighalia": "Dighalia",
    "doulatkhan": "Daulatkhan",
    "daulatkhan": "Daulatkhan",
    "doulatpur": "Daulatpur",
    "faridgonj": "Faridganj",
    "faridganj": "Faridganj",
    "fatikchhari": "Fatikchhari",
    "fultola": "Phultala",
    "gajaria": "Gazaria",
    "gazaria": "Gazaria",
    "gior": "Ghior",
    "ghior": "Ghior",
    "gomostapur": "Gomastapur",
    "gomastapur": "Gomastapur",
    "hatia": "Hatiya",
    "hatiya": "Hatiya",
    "ishurdi": "Ishwardi",
    "ishwardi": "Ishwardi",
    "iswarganj": "Ishwarganj",
    "ishwarganj": "Ishwarganj",
    "jhalakathi sadar": "Jhalokati Sadar",
    "jhikargacha": "Jhikargachha",
    "jhikargachha": "Jhikargachha",
    "kaharol": "Kaharole",
    "kaharole": "Kaharole",
    "kamarkhand": "Kamarkhanda",
    "kamarkhanda": "Kamarkhanda",
    "kamolganj": "Kamalganj",
    "kamalganj": "Kamalganj",
    "karimgonj": "Karimganj",
    "karimganj": "Karimganj",
    "karnafuli": "Karnaphuli",
    "kishorganj": "Kishoreganj",
    "laxmichhari": "Lakshmichhari",
    "louhajanj": "Lohajang",
    "manikchari": "Manikchhari",
    "manikchhari": "Manikchhari",
    "mithamoin": "Mithamain",
    "mithamain": "Mithamain",
    "mohadevpur": "Mahadebpur",
    "mahadebpur": "Mahadebpur",
    "mohalchari": "Mahalchhari",
    "mahalchhari": "Mahalchhari",
    "moheshkhali": "Maheshkhali",
    "maheshkhali": "Maheshkhali",
    "mohongonj": "Mohanganj",
    "mohanganj": "Mohanganj",
    "mohonpur": "Mohanpur",
    "mohanpur": "Mohanpur",
    "muktagacha": "Muktagachha",
    "muktagachha": "Muktagachha",
    "nachol": "Nachole",
    "nachole": "Nachole",
    "nokla": "Nakla",
    "nakla": "Nakla",
    "nondigram": "Nandigram",
    "nandigram": "Nandigram",
    "paikgasa": "Paikgachha",
    "panchari": "Panchhari",
    "panchhari": "Panchhari",
    "pangsa": "Pangsha",
    "pangsha": "Pangsha",
    "pathorghata": "Patharghata",
    "patharghata": "Patharghata",
    "phulchari": "Fulchhari",
    "pirgacha": "Pirgachha",
    "pirgachha": "Pirgachha",
    "pirgonj": "Pirganj",
    "pirganj": "Pirganj",
    "raigonj": "Royganj",
    "rupsha": "Rupsa",
    "rupsa": "Rupsa",
    "senbug": "Senbagh",
    "shariakandi": "Sariakandi",
    "sariakandi": "Sariakandi",
    "shibaloy": "Shibalaya",
    "singiar": "Singair",
    "singair": "Singair",
    "sonaimori": "Sonaimuri",
    "sonaimuri": "Sonaimuri",
    "sreebordi": "Sreebardi",
    "sreebardi": "Sreebardi",
    "syedpur": "Saidpur",
    "saidpur": "Saidpur",
    "taragonj": "Taraganj",
    "taraganj": "Taraganj",
    "ukhiya": "Ukhia",
    "ukhia": "Ukhia",
    "zianagar": "Zianagar",

    # Spelling variations
    "anwara": "Anowara",
    "anowara": "Anowara",
    "ashashuni": "Assasuni",
    "assasuni": "Assasuni",
    "beani bazar": "Beanibazar",
    "beanibazar": "Beanibazar",
    "bhuanpur": "Bhuapur",
    "bhuapur": "Bhuapur",
    "baghaichhari": "Baghaichhari",
    "baghai chhari": "Baghaichhari",
    "belai chhari": "Belaichhari",
    "belaichhari": "Belaichhari",
    "bishwambharpur": "Bishwambarpur",
    "bishwambarpur": "Bishwambarpur",
    "borhanuddin": "Burhanuddin",
    "burhanuddin": "Burhanuddin",
    "darussalam": "Darussalam",
    "darus salam": "Darussalam",
    "dakkhin surma": "Dakshin Surma",
    "dakshin surma": "Dakshin Surma",
    "south surma": "Dakshin Surma",
    "dakkhinkhan": "Dakshinkhan",
    "dakshinkhan": "Dakshinkhan",
    "doarabazar": "Dowarabazar",
    "dowarabazar": "Dowarabazar",
    "dirai": "Derai",
    "derai": "Derai",
    "dupchachia": "Dhupchanchia",
    "dhupchanchia": "Dhupchanchia",
    "faridpur": "Faridpur Sadar",  # in poverty data "Faridpur" means the sadar
    "fulpur": "Phulpur",
    "phulpur": "Phulpur",
    "fultala": "Phultala",
    "phultala": "Phultala",
    "fulbari": "Phulbari",
    "phulbari": "Phulbari",
    "fulgazi": "Fulgazi",
    "phulgazi": "Fulgazi",
    "fulchhari": "Fulchhari",
    "phulchhari": "Fulchhari",
    "gafargaon": "Gaffargaon",
    "gaffargaon": "Gaffargaon",
    "goainghat": "Gowainghat",
    "gowainghat": "Gowainghat",
    "gouripur": "Gauripur",
    "gauripur": "Gauripur",
    "goalanda": "Goalandaghat",
    "goalandaghat": "Goalandaghat",
    "golapganj": "Golabganj",
    "golabganj": "Golabganj",
    "hajirhat": "Hajirhat",
    "haragachh": "Haragachh",
    "harinakundu": "Harinakunda",
    "harinakunda": "Harinakunda",
    "hazaribag": "Hazaribagh",
    "hazaribagh": "Hazaribagh",
    "hijla": "Hizla",
    "hizla": "Hizla",
    "indurkani": "Indurkani",
    "jaintapur": "Jaintiapur",
    "jaintiapur": "Jaintiapur",
    "jhalokati sadar": "Jhalokati Sadar",
    "jurachhari": "Jurai Chhari",
    "jurai chhari": "Jurai Chhari",
    "kolapara": "Kala Para",
    "kala para": "Kala Para",
    "kalapara": "Kala Para",
    "karnaphuli": "Karnaphuli",
    "lakkhichhari": "Lakshmichhari",
    "lakshmichhari": "Lakshmichhari",
    "laxmipur sadar": "Lakshmipur Sadar",
    "lakshmipur sadar": "Lakshmipur Sadar",
    "lalbag": "Lalbagh",
    "lalbagh": "Lalbagh",
    "louhajang": "Lohajang",
    "lohajang": "Lohajang",
    "mirsarai": "Mirsharai",
    "mirsharai": "Mirsharai",
    "moglabazar": "Moglabazar",
    "monohargonj": "Manoharganj",
    "manoharganj": "Manoharganj",
    "monirampur": "Manirampur",
    "manirampur": "Manirampur",
    "monpura": "Manpura",
    "manpura": "Manpura",
    "morelganj": "Morrelganj",
    "morrelganj": "Morrelganj",
    "moulvibazar sadar": "Moulvibazar Sadar",
    "maulvi bazar sadar": "Moulvibazar Sadar",
    "nababganj": "Nawabganj",
    "nawabganj": "Nawabganj",
    "nawabganj sadar": "Chapainawabganj Sadar",
    "nageshwari": "Nageshwari",
    "nageswari": "Nageshwari",
    "naikkhongchhari": "Naikhongchhari",
    "naikhongchhari": "Naikhongchhari",
    "nalchhity": "Nalchity",
    "nalchity": "Nalchity",
    "naldanga": "Naldanga",
    "nesarabad (swarupkathi)": "Nesarabad (Swarupkati)",
    "nesarabad (swarupkati)": "Nesarabad (Swarupkati)",
    "netrakona sadar": "Netrokona Sadar",
    "netrokona sadar": "Netrokona Sadar",
    "noakhali sadar": "Noakhali Sadar",
    "noakhali sadar (sudharam)": "Noakhali Sadar",
    "osmaninagar": "Osmaninagar",
    "paikgacha": "Paikgachha",
    "paikgachha": "Paikgachha",
    "palong": "Palong",  # part of Shariatpur - not in geocode but real upazila (newer)
    "parashuram": "Parshuram",
    "parshuram": "Parshuram",
    "pubail": "Pubail",
    "pubail thana area": "Pubail",
    "raiganj": "Royganj",
    "royganj": "Royganj",
    "rayganj": "Royganj",
    "raipur": "Roypur",
    "roypur": "Roypur",
    "raipura": "Roypura",
    "roypura": "Roypura",
    "rajibpur": "Char Rajibpur",
    "char rajibpur": "Char Rajibpur",
    "rangabali": "Rangabali",
    "ranisankail": "Ranisankail",
    "ranishankail": "Ranisankail",
    "roumari": "Raumari",
    "raumari": "Raumari",
    "rupnagar": "Rupnagar",
    "sabujbag": "Sabujbagh",
    "sabujbagh": "Sabujbagh",
    "sadar dakkhin": "Comilla Sadar Dakshin",
    "salta": "Saltha",
    "saltha": "Saltha",
    "senbag": "Senbagh",
    "senbagh": "Senbagh",
    "shaghata": "Saghatta",
    "saghata": "Saghatta",
    "saghatta": "Saghatta",
    "shahjahanpur": "Shajahanpur",
    "shajahanpur": "Shajahanpur",
    "sharankhola": "Sarankhola",
    "sarankhola": "Sarankhola",
    "shaistaganj": "Shayestaganj",
    "shayestaganj": "Shayestaganj",
    "shibchar": "Shib Char",
    "shib char": "Shib Char",
    "shibalay": "Shibalaya",
    "shibalaya": "Shibalaya",
    "sirajdikhan": "Serajdikhan",
    "serajdikhan": "Serajdikhan",
    "srinagar": "Sreenagar",
    "sreenagar": "Sreenagar",
    "sonatala": "Sonatola",
    "sonatola": "Sonatola",
    "ashtagram": "Austagram",
    "austagram": "Austagram",
    "atowari": "Atwari",
    "atwari": "Atwari",
    "avoynagar": "Abhaynagar",
    "abhaynagar": "Abhaynagar",
    "baralekha": "Barlekha",
    "barlekha": "Barlekha",
    "bagmara": "Baghmara",
    "baghmara": "Baghmara",
    "basundia union": "Basundia Union",  # not a real upazila
    "bimanbandar": "Biman Bandar",
    "biman bandar": "Biman Bandar",
    "chalk bazar": "Chak Bazar",
    "chak bazar": "Chak Bazar",
    "chattogram port": "Chittagong Port",
    "chittagong port": "Chittagong Port",
    "chandrima": "Chandrima",
    "dasherhat": "Dasar",  # Madaripur new upazila name
    "dasar": "Dasar",
    "dakshin sunamganj": "Dakshin Sunamganj",
    "dharampasha": "Dharmapasha",
    "dharmapasha": "Dharmapasha",
    "gachha": "Gachha",
    "hatirjheel": "Hatirjheel",
    "jajira": "Zanjira",
    "zajira": "Zanjira",
    "zanjira": "Zanjira",
    "jalalabad": "Jalalabad",
    "kashiadanga": "Kashiadanga",
    "kasimpur": "Kashimpur",
    "kashimpur": "Kashimpur",
    "konabari": "Konabari",
    "kotwali": "Kotwali",
    "lalmai": "Lalmai",
    "madhyanagar": "Madhyanagar",
    "mahiganj": "Mahiganj",
    "newmarket": "New Market",
    "new market": "New Market",
    "eidgaon": "Eidgaon",
    "epz": "EPZ",
    "guimara": "Guimara",
    "adarsha sadar": "Comilla Sadar",
    "shalla": "Sulla",
    "sulla": "Sulla",
    "shantiganj": "Shantiganj",
    "tajhat": "Tajhat",
    "ullah para": "Ullapara",
    "ullapara": "Ullapara",
    "ujirpur": "Ujirpur",
    "wazirpur": "Wazirpur",
    "uttar khan": "Uttarkhan",
    "uttarkhan": "Uttarkhan",
    "uttara pashchim": "Uttara",
    "uttara purba": "Uttara",
    "uttara": "Uttara",
    "tongi pashchim": "Tongi",
    "tongi purba": "Tongi",
    "basan": "Basan",
    "bhasantek": "Bhasantek",
    "bhatara": "Bhatara",
    # Kishoreganj from poverty
    "kishoreganj": "Kishoreganj",
    # Some poverty entries that are thana-level in city corps
    "adabar": "Adabor",
    "adabor": "Adabor",
    "airport": "Biman Bandar",
    "akbarshah": "Akbarshah",
    "badda": "Badda",
    "bakalia": "Bakalia",
    "banani": "Banani",
    "bangshal": "Bangshal",
    "bayejid bostami": "Bayejid Bostami",
    "boalia": "Boalia",
    "cantonment": "Cantonment",
    "chandgaon": "Chandgaon",
    "chawkbazar": "Chawkbazar",
    "double mooring": "Double Mooring",
    "gendaria": "Gendaria",
    "gulshan": "Gulshan",
    "halishahar": "Halishahar",
    "jatrabari": "Jatrabari",
    "kadamtali": "Kadamtali",
    "kafrul": "Kafrul",
    "kalabagan": "Kalabagan",
    "khalishpur": "Khalishpur",
    "khan jahan ali": "Khan Jahan Ali",
    "khilgaon": "Khilgaon",
    "khilkhet": "Khilkhet",
    "khulshi": "Khulshi",
    "lohagara": "Lohagara",
    "matihar": "Matihar",
    "mirpur": "Mirpur",
    "mohammadpur": "Mohammadpur",
    "motijheel": "Motijheel",
    "mugda": "Mugda",
    "pahartali": "Pahartali",
    "pallabi": "Pallabi",
    "paltan": "Paltan",
    "panchlaish": "Panchlaish",
    "patenga": "Patenga",
    "rajpara": "Rajpara",
    "ramna": "Ramna",
    "rampura": "Rampura",
    "sabujbagh": "Sabujbagh",
    "sadarghat": "Sadarghat",
    "shah ali": "Shah Ali",
    "shah makhdum": "Shah Makhdum",
    "shahbag": "Shahbagh",
    "shahbagh": "Shahbagh",
    "sher-e-bangla nagar": "Sher-E-Bangla Nagar",
    "sher-e-bangla nagar": "Sher-E-Bangla Nagar",
    "shyampur": "Shyampur",
    "sonadanga": "Sonadanga",
    "sutrapur": "Sutrapur",
    "tejgaon": "Tejgaon",
    "tejgaon shilpa elaka": "Tejgaon Ind. Area",
    "tejgaon ind. area": "Tejgaon Ind. Area",
    "turag": "Turag",
    "wari": "Wari",
    "demra": "Demra",
    "daulatpur": "Daulatpur",
    "joydebpur": "Gazipur Sadar",  # Joydebpur is old name
    "sherpur": "Sherpur",
}


def load_geocode():
    """Load geocode upazilas with district mapping."""
    with open(GEOCODE_DISTRICTS) as f:
        dist_data = json.load(f)
    dist_map = {}
    for item in dist_data:
        if item.get("type") == "table" and item.get("name") == "districts":
            for rec in item["data"]:
                dist_map[rec["id"]] = rec["name"]

    with open(GEOCODE_UPAZILAS) as f:
        data = json.load(f)
    upazilas = []
    for item in data:
        if item.get("type") == "table" and item.get("name") == "upazilas":
            for rec in item["data"]:
                upazilas.append({
                    "name": rec["name"],
                    "district": dist_map.get(rec["district_id"], ""),
                    "bn_name": rec.get("bn_name", ""),
                })
    return upazilas


def load_humdata_pop():
    """Load humdata population upazilas."""
    upazilas = []
    with open(POP_UPAZILA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            upazilas.append({
                "name": row["upazila"].strip(),
                "district": row["district"].strip(),
                "division": row["division"].strip(),
            })
    return upazilas


def load_poverty():
    """Load poverty data upazilas."""
    upazilas = []
    with open(POVERTY_UPAZILA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["name"].strip()
            if not name or name == "name":
                continue
            upazilas.append({
                "name": name,
                "district": row["district"].strip(),
                "division": row["division"].strip(),
            })
    return upazilas


def load_election():
    """Load election seat results and extract upazila entries."""
    entries = []
    with open(SEAT_RESULTS, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            constituency = row["seat_name"].strip()
            district = row["district"].strip()
            seat_number = row["seat_number"].strip()
            raw = row["upazila"].strip()
            if not raw:
                continue
            for part in raw.split(","):
                part = part.strip()
                if not part:
                    continue
                clean = strip_clean(part)
                entries.append({
                    "raw": part,
                    "clean": clean,
                    "district": district,
                    "constituency": constituency,
                    "seat_number": seat_number,
                    "is_ward": is_ward_or_number(clean),
                })
    return entries


def resolve_standard_name(name):
    """Resolve a name to its standard form using KNOWN_MAPPINGS."""
    key = name.strip().lower()
    if key in KNOWN_MAPPINGS:
        return KNOWN_MAPPINGS[key]
    return None


def build_master_list(geocode, humdata, poverty, election, district_aliases):
    """
    Build master upazila list. Priority for standard name:
    1. Humdata pop (most entries, modern spelling)
    2. Geocode
    3. Poverty
    4. Election (cleaned)
    """
    # Collect all unique upazilas by normalized key
    # Each entry: {standard_name, district, sources: {source: name_used}}
    master = {}  # norm_key -> entry

    def add_entry(name, district, source, norm_district=None):
        if not name or name.lower() == 'name' or name.lower() == 'upazila':
            return
        std = resolve_standard_name(name)
        if std:
            actual_name = std
        else:
            actual_name = name

        nk = norm_key(actual_name)
        if not nk:
            return

        if norm_district:
            dist = norm_district
        else:
            dist = normalize_district(district, district_aliases)

        if nk not in master:
            master[nk] = {
                "standard_name": actual_name,
                "district": dist,
                "sources": {},
            }

        master[nk]["sources"][source] = name
        # Update district if we didn't have one
        if not master[nk]["district"] and dist:
            master[nk]["district"] = dist

    # Process humdata pop (priority source for naming)
    for u in humdata:
        dist = normalize_district(u["district"], district_aliases)
        add_entry(u["name"], u["district"], "humdata_pop", dist)

    # Process geocode
    for u in geocode:
        dist = normalize_district(u["district"], district_aliases)
        add_entry(u["name"], u["district"], "geocode", dist)

    # Process poverty
    for u in poverty:
        dist = normalize_district(u["district"], district_aliases)
        add_entry(u["name"], u["district"], "poverty", dist)

    # Process election (only non-ward entries)
    for e in election:
        if e["is_ward"]:
            continue
        dist = normalize_district(e["district"], district_aliases)
        add_entry(e["clean"], e["district"], "election", dist)

    return master


def build_name_map_and_aliases(master):
    """Build the name map CSV data and aliases JSON."""
    rows = []
    aliases = {}

    for nk, entry in sorted(master.items(), key=lambda x: x[1]["standard_name"]):
        std = entry["standard_name"]
        sources = entry["sources"]

        row = {
            "standard_name": std,
            "district": entry["district"],
            "humdata_pop": sources.get("humdata_pop", ""),
            "poverty": sources.get("poverty", ""),
            "election": sources.get("election", ""),
            "geocode": sources.get("geocode", ""),
        }
        rows.append(row)

        # Build aliases: any name different from standard
        for source, name in sources.items():
            if name != std and name.strip():
                aliases[name] = std

    return rows, aliases


def build_constituency_map(master, election, district_aliases):
    """Build comprehensive constituency map including ALL upazilas."""
    # First, build election mapping: standard_name -> list of constituencies
    election_map = defaultdict(list)  # standard_name -> [{constituency, seat_number}]
    ward_entries = []

    for e in election:
        if e["is_ward"]:
            ward_entries.append(e)
            continue

        clean = e["clean"]
        std = resolve_standard_name(clean)
        if not std:
            # Try to find in master by norm_key
            nk = norm_key(clean)
            for mk, mv in master.items():
                if mk == nk:
                    std = mv["standard_name"]
                    break
            if not std:
                std = clean

        election_map[std].append({
            "constituency": e["constituency"],
            "seat_number": e["seat_number"],
            "district": normalize_district(e["district"], district_aliases),
            "raw": e["raw"],
        })

    rows = []

    # Add all upazilas from master
    added = set()
    for nk, entry in sorted(master.items(), key=lambda x: x[1]["standard_name"]):
        std = entry["standard_name"]
        if std in added:
            continue

        if std in election_map:
            for em in election_map[std]:
                sources = ["election"]
                if "geocode" in entry["sources"]:
                    sources.append("geocode")
                if "humdata_pop" in entry["sources"]:
                    sources.append("humdata_pop")
                if "poverty" in entry["sources"]:
                    sources.append("poverty")
                rows.append({
                    "upazila": std,
                    "district": em["district"] or entry["district"],
                    "constituency": em["constituency"],
                    "constituency_number": em["seat_number"],
                    "source": "; ".join(sources),
                    "type": "upazila",
                })
            added.add(std)
        else:
            # Upazila exists in reference sources but not in election data
            sources = []
            if "geocode" in entry["sources"]:
                sources.append("geocode")
            if "humdata_pop" in entry["sources"]:
                sources.append("humdata_pop")
            if "poverty" in entry["sources"]:
                sources.append("poverty")
            rows.append({
                "upazila": std,
                "district": entry["district"],
                "constituency": "",
                "constituency_number": "",
                "source": "; ".join(sources),
                "type": "upazila" if not is_city_thana(std, entry) else "thana",
            })
            added.add(std)

    # Add ward entries separately
    for e in ward_entries:
        dist = normalize_district(e["district"], district_aliases)
        rows.append({
            "upazila": e["clean"],
            "district": dist,
            "constituency": e["constituency"],
            "constituency_number": e["seat_number"],
            "source": "election",
            "type": "city_corp_ward",
        })

    return rows


# City corporation thana names (not upazilas)
CITY_THANAS = {
    "adabor", "badda", "banani", "bangshal", "biman bandar", "cantonment",
    "chak bazar", "chandgaon", "chawkbazar", "dakshinkhan", "darussalam",
    "demra", "double mooring", "gendaria", "gulshan", "halishahar",
    "jatrabari", "kadamtali", "kafrul", "kalabagan", "khalishpur",
    "khan jahan ali", "khilgaon", "khilkhet", "khulshi", "kotwali",
    "lalbagh", "mirpur", "mohammadpur", "motijheel", "mugda", "new market",
    "pahartali", "pallabi", "paltan", "panchlaish", "patenga", "rajpara",
    "ramna", "rampura", "rupnagar", "sabujbagh", "sadarghat", "shah ali",
    "shah makhdum", "shahbagh", "sher-e-bangla nagar", "shyampur",
    "sonadanga", "sutrapur", "tejgaon", "tejgaon ind. area", "turag",
    "uttarkhan", "uttara", "wari", "boalia", "matihar", "rajpara",
    "shah makhdum", "daulatpur", "hazaribagh", "konabari",
    "akbarshah", "bakalia", "bayejid bostami", "chittagong port",
    "epz", "gazipur sadar",
    "tongi", "bhasantek", "bhatara", "basan",
    "hatirjheel", "chandrima", "madhyanagar", "mahiganj", "tajhat",
}


def is_city_thana(name, entry):
    """Check if this is a city corporation thana rather than a proper upazila."""
    return name.lower() in CITY_THANAS


def write_mismatch_report(master, election, district_aliases):
    """Write updated mismatch report."""
    unmatched_election = []
    for e in election:
        if e["is_ward"]:
            continue
        clean = e["clean"]
        std = resolve_standard_name(clean)
        nk = norm_key(clean)
        found = False
        if std:
            found = True
        else:
            for mk in master:
                if mk == nk:
                    found = True
                    break
        if not found:
            unmatched_election.append(e)

    # Upazilas in geocode but not in election
    election_stds = set()
    for e in election:
        if e["is_ward"]:
            continue
        std = resolve_standard_name(e["clean"])
        if std:
            election_stds.add(std)
        else:
            nk = norm_key(e["clean"])
            for mk, mv in master.items():
                if mk == nk:
                    election_stds.add(mv["standard_name"])
                    break

    geocode_only = []
    for nk, entry in master.items():
        if "geocode" in entry["sources"] and entry["standard_name"] not in election_stds:
            if not is_city_thana(entry["standard_name"], entry):
                geocode_only.append(entry)

    with open(MISMATCH_REPORT, "w", encoding="utf-8") as f:
        f.write("Upazila Cross-Verification Report\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Master upazila list: {len(master)} entries\n")
        f.write(f"Election upazila entries (non-ward): {len([e for e in election if not e['is_ward']])}\n")
        f.write(f"Unmatched election entries: {len(unmatched_election)}\n")
        f.write(f"Geocode upazilas not in election: {len(geocode_only)}\n\n")

        if unmatched_election:
            f.write("Unmatched Election Entries (need manual mapping):\n")
            f.write("-" * 60 + "\n")
            for e in unmatched_election:
                f.write(f"  [{e['constituency']}] {e['clean']} (raw: {e['raw']})\n")
            f.write("\n")

        if geocode_only:
            f.write("Geocode Upazilas Not Found in Election Data:\n")
            f.write("-" * 60 + "\n")
            for entry in sorted(geocode_only, key=lambda x: x["standard_name"]):
                f.write(f"  {entry['standard_name']} ({entry['district']})\n")
            f.write("\n")

        f.write("All entries verified or mapped.\n")

    return unmatched_election, geocode_only


def main():
    print("Loading district aliases...")
    district_aliases = load_district_aliases()

    print("Loading geocode upazilas...")
    geocode = load_geocode()
    print(f"  {len(geocode)} entries")

    print("Loading humdata pop upazilas...")
    humdata = load_humdata_pop()
    print(f"  {len(humdata)} entries")

    print("Loading poverty upazilas...")
    poverty = load_poverty()
    print(f"  {len(poverty)} entries")

    print("Loading election data...")
    election = load_election()
    print(f"  {len(election)} entries ({len([e for e in election if not e['is_ward']])} non-ward)")

    print("\nBuilding master upazila list...")
    master = build_master_list(geocode, humdata, poverty, election, district_aliases)
    print(f"  {len(master)} unique upazilas")

    print("\nBuilding name map and aliases...")
    name_rows, aliases = build_name_map_and_aliases(master)

    # Write name map CSV
    print(f"\nWriting {NAME_MAP_CSV}...")
    with open(NAME_MAP_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "standard_name", "district", "humdata_pop", "poverty", "election", "geocode"
        ])
        writer.writeheader()
        writer.writerows(name_rows)
    print(f"  {len(name_rows)} rows")

    # Write aliases JSON
    print(f"Writing {ALIASES_JSON}...")
    with open(ALIASES_JSON, "w", encoding="utf-8") as f:
        json.dump(aliases, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  {len(aliases)} aliases")

    print("\nBuilding constituency map...")
    const_rows = build_constituency_map(master, election, district_aliases)

    print(f"Writing {CONSTITUENCY_MAP}...")
    with open(CONSTITUENCY_MAP, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "upazila", "district", "constituency", "constituency_number", "source", "type"
        ])
        writer.writeheader()
        writer.writerows(const_rows)
    print(f"  {len(const_rows)} rows")

    # Count types
    type_counts = defaultdict(int)
    for r in const_rows:
        type_counts[r["type"]] += 1
    for t, c in sorted(type_counts.items()):
        print(f"    {t}: {c}")

    # Count upazilas with and without constituencies
    upazila_rows = [r for r in const_rows if r["type"] == "upazila"]
    with_const = len([r for r in upazila_rows if r["constituency"]])
    without_const = len([r for r in upazila_rows if not r["constituency"]])
    print(f"  Upazilas with constituency: {with_const}")
    print(f"  Upazilas without constituency mapping: {without_const}")

    print("\nWriting mismatch report...")
    unmatched, geocode_only = write_mismatch_report(master, election, district_aliases)
    print(f"  Unmatched election entries: {len(unmatched)}")
    print(f"  Geocode-only upazilas: {len(geocode_only)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
