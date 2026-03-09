#!/usr/bin/env python3
"""
Build upazila-to-constituency mapping for Bangladesh, cross-verified with multiple sources.

Sources:
1. seat_results.csv - Election results with upazila column per constituency
2. bangladesh-geocode (nuhil/github) - Canonical upazila list (494 upazilas)
3. pop_upazila.csv (HumData population stats) - Another upazila reference (527 entries)

Output: upazila_constituency_map.csv
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEAT_RESULTS = os.path.join(BASE_DIR, "results", "seat_results.csv")
POP_UPAZILA = os.path.join(BASE_DIR, "humdata_pop_stats", "pop_upazila.csv")
GEOCODE_UPAZILAS = "/tmp/bd_upazilas.json"
GEOCODE_DISTRICTS = "/tmp/bd_district_map.json"
OUTPUT_CSV = os.path.join(BASE_DIR, "config", "upazila_constituency_map.csv")
MISMATCH_REPORT = os.path.join(BASE_DIR, "config", "upazila_mismatch_report.txt")


def normalize(name):
    """Normalize upazila name for fuzzy matching."""
    s = name.strip().lower()
    # Remove common suffixes
    for suffix in [" upazila", " thana", " sadar", " city corporation", " municipality",
                   " pourashava", " paurashava"]:
        pass  # Don't strip these as they may be part of the canonical name
    # Remove parenthetical notes like "(partial)"
    s = re.sub(r'\s*\(partial\)\s*', '', s)
    s = re.sub(r'\s*\(.*?\)\s*', '', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def strip_upazila_suffix(name):
    """Remove 'Upazila' suffix for matching against sources that don't use it."""
    s = name.strip()
    s = re.sub(r'\s*\(partial\)', '', s)
    s = re.sub(r'\s+Upazila$', '', s, flags=re.IGNORECASE)
    return s.strip()


def parse_seat_results():
    """Parse seat_results.csv to extract upazila-constituency mapping."""
    mapping = []  # list of (upazila_raw, upazila_clean, district, constituency, seat_number)
    with open(SEAT_RESULTS, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            constituency = row["seat_name"].strip()
            district = row["district"].strip()
            seat_number = row["seat_number"].strip()
            upazila_raw = row["upazila"].strip()

            if not upazila_raw:
                continue

            # Split comma-separated upazilas
            parts = [p.strip() for p in upazila_raw.split(",") if p.strip()]
            for part in parts:
                clean = strip_upazila_suffix(part)
                mapping.append({
                    "upazila_raw": part,
                    "upazila_clean": clean,
                    "district": district,
                    "constituency": constituency,
                    "seat_number": seat_number,
                })
    return mapping


def load_geocode_upazilas():
    """Load upazilas from bangladesh-geocode JSON."""
    with open(GEOCODE_UPAZILAS) as f:
        data = json.load(f)

    # Load district mapping
    with open(GEOCODE_DISTRICTS) as f:
        district_map = json.load(f)

    upazilas = {}
    for item in data:
        if item.get("type") == "table" and item.get("name") == "upazilas":
            for rec in item["data"]:
                name = rec["name"]
                dist_id = rec["district_id"]
                dist_name = district_map.get(dist_id, "")
                upazilas[name.lower()] = {
                    "name": name,
                    "district": dist_name,
                }
    return upazilas


def load_pop_upazilas():
    """Load upazilas from pop_upazila.csv."""
    upazilas = {}
    with open(POP_UPAZILA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["upazila"].strip()
            district = row["district"].strip()
            upazilas[name.lower()] = {
                "name": name,
                "district": district,
            }
    return upazilas


def cross_verify(seat_mapping, geocode_upazilas, pop_upazilas):
    """Cross-verify upazilas from seat_results against reference sources."""
    results = []
    mismatches = []

    # Build lookup keys for geocode (already lowered)
    # Build lookup keys for pop (already lowered)

    for entry in seat_mapping:
        clean = entry["upazila_clean"]
        raw = entry["upazila_raw"]
        clean_lower = clean.lower()

        sources = ["seat_results"]

        # Check against geocode
        geocode_match = False
        if clean_lower in geocode_upazilas:
            geocode_match = True
        else:
            # Try without "Sadar" variations
            for gk in geocode_upazilas:
                if clean_lower.replace(" sadar", "") == gk.replace(" sadar", ""):
                    geocode_match = True
                    break
                # Handle spelling variants
                if _fuzzy_match(clean_lower, gk):
                    geocode_match = True
                    break

        if geocode_match:
            sources.append("geocode")

        # Check against pop_upazila
        pop_match = False
        if clean_lower in pop_upazilas:
            pop_match = True
        else:
            # Try common variations
            for pk in pop_upazilas:
                if _fuzzy_match(clean_lower, pk):
                    pop_match = True
                    break

        if pop_match:
            sources.append("pop_stats")

        # Check for city corporations and wards (not upazilas, won't match)
        is_city_corp = "city corporation" in raw.lower() or "ward" in raw.lower()
        if is_city_corp:
            sources.append("city_corp_area")

        if not geocode_match and not pop_match and not is_city_corp:
            mismatches.append({
                "upazila": clean,
                "raw": raw,
                "constituency": entry["constituency"],
                "district": entry["district"],
                "issue": "Not found in geocode or pop_stats",
            })

        results.append({
            "upazila": clean,
            "district": entry["district"],
            "constituency": entry["constituency"],
            "constituency_number": entry["seat_number"],
            "source": "; ".join(sources),
        })

    return results, mismatches


# Common spelling variations in Bangladesh upazila names
SPELLING_ALIASES = {
    "debiganj": "deviganj",
    "bochaganj": "bochaganj",
    "chirirbandar": "chirirbandar",
    "fulbari": "phulbari",
    "ghoraghat": "ghoraghat",
    "hatibandha": "hatibandha",
    "kaliganj": "kaligonj",
    "aditmari": "aditmari",
    "gangachara": "gangachara",
    "taraganj": "taraganj",
    "badarganj": "badarganj",
    "mithapukur": "mithapukur",
    "pirganj": "pirgonj",
    "pirgachha": "pirgachha",
    "sundarganj": "sundarganj",
    "lalmonirhat": "lalmonirhat",
    "kurigram": "kurigram",
    "gaibandha": "gaibandha",
    "joypurhat": "jaipurhat",
    "bogra": "bogura",
    "chapainawabganj": "chapai nawabganj",
    "nawabganj": "chapai nawabganj",
    "moulvibazar": "moulvi bazar",
    "brahmanbaria": "brahamanbaria",
    "cumilla": "comilla",
    "coxs bazar": "cox's bazar",
    "cox's bazar": "coxs bazar",
    "jhenaidah": "jhenaidah",
    "narail": "narail",
    "netrakona": "netrokona",
    "habiganj": "habiganj",
    "munshiganj": "munshiganj",
    "kishoreganj": "kishoreganj",
}


def _fuzzy_match(a, b):
    """Simple fuzzy matching for upazila names."""
    if a == b:
        return True
    # Strip common suffixes for comparison
    a2 = a.replace(" sadar", "").replace(" city", "").strip()
    b2 = b.replace(" sadar", "").replace(" city", "").strip()
    if a2 == b2:
        return True
    # Check aliases
    if a in SPELLING_ALIASES and SPELLING_ALIASES[a] == b:
        return True
    if b in SPELLING_ALIASES and SPELLING_ALIASES[b] == a:
        return True
    # Handle Kotwali suffix
    if a.replace(" (kotwali)", "") == b or b.replace(" (kotwali)", "") == a:
        return True
    # Remove all non-alphanumeric and compare
    a3 = re.sub(r'[^a-z0-9]', '', a)
    b3 = re.sub(r'[^a-z0-9]', '', b)
    if a3 == b3:
        return True
    # One contains the other
    if len(a3) > 4 and len(b3) > 4:
        if a3 in b3 or b3 in a3:
            return True
    return False


def load_upazila_aliases():
    """Load upazila name aliases from the generated aliases file."""
    aliases_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upazila_name_aliases.json")
    if os.path.exists(aliases_file):
        with open(aliases_file) as f:
            return json.load(f)
    return {}


def normalize_upazila_name(name, aliases):
    """Normalize an upazila name using the aliases map."""
    clean = strip_upazila_suffix(name)
    if clean in aliases:
        return aliases[clean]
    return clean


def main():
    print("NOTE: For comprehensive upazila mapping, run build_upazila_name_map.py instead.")
    print("This script is kept for backward compatibility.\n")

    # Load upazila aliases for name normalization
    upazila_aliases = load_upazila_aliases()
    if upazila_aliases:
        print(f"Loaded {len(upazila_aliases)} upazila name aliases for normalization")

    print("Parsing seat_results.csv...")
    seat_mapping = parse_seat_results()
    print(f"  Found {len(seat_mapping)} upazila-constituency entries from {len(set(e['constituency'] for e in seat_mapping))} constituencies")

    # Apply name normalization
    if upazila_aliases:
        for entry in seat_mapping:
            entry["upazila_clean"] = normalize_upazila_name(entry["upazila_raw"], upazila_aliases)

    print("Loading geocode upazilas...")
    geocode = load_geocode_upazilas()
    print(f"  Found {len(geocode)} upazilas")

    print("Loading pop_upazila.csv...")
    pop = load_pop_upazilas()
    print(f"  Found {len(pop)} upazilas")

    print("Cross-verifying...")
    results, mismatches = cross_verify(seat_mapping, geocode, pop)

    # Count sources
    source_counts = defaultdict(int)
    for r in results:
        for s in r["source"].split("; "):
            source_counts[s] += 1

    print(f"\nSource verification counts:")
    for s, c in sorted(source_counts.items()):
        print(f"  {s}: {c}")

    print(f"\nMismatches/unverified: {len(mismatches)}")
    for m in mismatches:
        print(f"  [{m['constituency']}] {m['upazila']} ({m['raw']}) - {m['issue']}")

    # Write output CSV
    print(f"\nWriting {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["upazila", "district", "constituency", "constituency_number", "source", "type"])
        writer.writeheader()
        writer.writerows(results)

    print(f"  Wrote {len(results)} rows")

    # Write mismatch report
    with open(MISMATCH_REPORT, "w", encoding="utf-8") as f:
        f.write("Upazila Cross-Verification Mismatch Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total entries from seat_results: {len(seat_mapping)}\n")
        f.write(f"Geocode reference upazilas: {len(geocode)}\n")
        f.write(f"Pop stats reference upazilas: {len(pop)}\n")
        f.write(f"Unverified entries: {len(mismatches)}\n\n")
        if mismatches:
            f.write("Unverified entries:\n")
            f.write("-" * 50 + "\n")
            for m in mismatches:
                f.write(f"  Constituency: {m['constituency']}\n")
                f.write(f"  Upazila: {m['upazila']}\n")
                f.write(f"  Raw: {m['raw']}\n")
                f.write(f"  District: {m['district']}\n")
                f.write(f"  Issue: {m['issue']}\n\n")
        else:
            f.write("All entries verified against at least one reference source.\n")

    print(f"  Mismatch report: {MISMATCH_REPORT}")
    print("\nDone.")


if __name__ == "__main__":
    main()
