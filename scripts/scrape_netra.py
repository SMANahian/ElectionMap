"""
scrape_netra.py — Scrape Bangladesh 2026 election data from Netra News interactive map.

Source: https://interactive.netra.news/bangladesh-election-2026-map/
Data sourced from Election Commission publications.

Two data files:
  - dict/inline-data.b64  — base64 JSON with union-level data + geometry
  - dict/alliance_level_data.csv — polling center-level data (39K+ centers)

Output directory: result_from_source/netra_news/
  - netra_centers.csv      — polling center-level records (39,761 rows)
  - netra_unions.csv       — aggregated union-level records (~5,593 rows)
  - netra_by_seat.csv      — aggregated per-constituency totals (297 rows)
  - netra_by_seat_wide.csv — same as above, wide format
"""

import csv, os, re, sys, urllib.request
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE, "result_from_source", "netra_news")
os.makedirs(OUT_DIR, exist_ok=True)

CSV_URL = "https://interactive.netra.news/bangladesh-election-2026-map/dict/alliance_level_data.csv"
CSV_CACHE = os.path.join(OUT_DIR, "alliance_level_data_raw.csv")

# ---------------------------------------------------------------------------
# Seat name normalization: Netra uses old/variant spellings
# ---------------------------------------------------------------------------
NETRA_SEAT_MAP = {
    "Bandarban": "Bandarban 1",
    "Khagrachhari": "Khagrachhari 1",
    "Rangamati": "Rangamati 1",
}

SPELLING = {
    "bogra": "Bogura", "chittagong": "Chattogram", "chaudanga": "Chuadanga",
    "comilla": "Cumilla", "gopalgonj": "Gopalganj", "hobigonj": "Habiganj",
    "jamaljpur": "Jamalpur", "jessor": "Jashore", "jheniadha": "Jhenaidah",
    "jhenidha": "Jhenaidah", "jhalokhati": "Jhalokathi",
    "kishorgonj": "Kishoreganj", "kustia": "Kushtia",
    "manikgonj": "Manikganj", "moulavibazar": "Moulvibazar",
    "munshigonj": "Munshiganj", "narayangonj": "Narayanganj",
    "narshingdi": "Narsingdi", "netrokona": "Netrakona",
    "noagoan": "Naogaon", "sariatpur": "Shariatpur",
    "sirajgong": "Sirajganj", "sirajgonj": "Sirajganj",
    "sunamgonj": "Sunamganj",
}


def normalize_netra_seat(name):
    if name in NETRA_SEAT_MAP:
        return NETRA_SEAT_MAP[name]
    n = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    n = n.replace("-", " ")
    parts = n.split()
    num = parts[-1] if parts[-1].isdigit() else ""
    district_parts = parts[:-1] if num else parts
    district = "".join(district_parts).lower()
    if district in SPELLING:
        district = SPELLING[district]
    else:
        district = "".join(district_parts)
    if "chapai" in district.lower():
        district = "Chapainawabganj"
    if "coxs" in district.lower() or "cox" in district.lower():
        district = "Cox's Bazar"
    return f"{district} {num}".strip()


def download_csv():
    """Download the polling center CSV (strips geometry on save)."""
    if os.path.exists(CSV_CACHE):
        print(f"Using cached {CSV_CACHE}")
        return

    print(f"Downloading {CSV_URL} ...")
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read().decode("utf-8")
    with open(CSV_CACHE, "w", encoding="utf-8") as f:
        f.write(data)
    print(f"Cached to {CSV_CACHE} ({len(data) / 1e6:.1f} MB)")


def parse_centers():
    """Parse raw CSV into center-level records."""
    centers = []
    with open(CSV_CACHE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            seat_raw = r.get("constituency_name_en", "")
            centers.append({
                "seat_name": normalize_netra_seat(seat_raw),
                "constituency_id": r.get("constituency_id", ""),
                "center_id": r.get("center_id", ""),
                "center_no": r.get("center_no", ""),
                "center_name": r.get("center_name", ""),
                "lat": r.get("lat", ""),
                "lon": r.get("lon", ""),
                "district": r.get("District", ""),
                "upazila": r.get("Upazila", ""),
                "union": r.get("Union", ""),
                "total_voters": int(float(r.get("total_voters", 0) or 0)),
                "valid_votes": int(float(r.get("valid_votes", 0) or 0)),
                "rejected_votes": int(float(r.get("rejected_votes", 0) or 0)),
                "absent_voters": int(float(r.get("absent_voters", 0) or 0)),
                "bnp_alliance": int(float(r.get("BNP-led alliance", 0) or 0)),
                "jamaat_alliance": int(float(r.get("Jamaat-led alliance", 0) or 0)),
                "independent": int(float(r.get("Independent", 0) or 0)),
                "other_party": int(float(r.get("Other party", 0) or 0)),
            })
    return centers


def write_centers_csv(centers):
    """Write polling center-level CSV (no geometry)."""
    path = os.path.join(OUT_DIR, "netra_centers.csv")
    fields = [
        "seat_name", "constituency_id", "center_id", "center_no", "center_name",
        "lat", "lon", "district", "upazila", "union",
        "total_voters", "valid_votes", "rejected_votes", "absent_voters",
        "bnp_alliance", "jamaat_alliance", "independent", "other_party",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(centers)
    print(f"Wrote {len(centers)} centers to {path}")


def write_unions_csv(centers):
    """Aggregate centers to union level."""
    agg = defaultdict(lambda: {
        "district": "", "upazila": "", "union": "", "seat_name": "",
        "center_count": 0, "total_voters": 0, "valid_votes": 0,
        "rejected_votes": 0, "absent_voters": 0,
        "bnp_alliance": 0, "jamaat_alliance": 0, "independent": 0, "other_party": 0,
    })
    num_fields = ["total_voters", "valid_votes", "rejected_votes", "absent_voters",
                  "bnp_alliance", "jamaat_alliance", "independent", "other_party"]
    for r in centers:
        key = (r["seat_name"], r["district"], r["upazila"], r["union"])
        a = agg[key]
        a["seat_name"] = r["seat_name"]
        a["district"] = r["district"]
        a["upazila"] = r["upazila"]
        a["union"] = r["union"]
        a["center_count"] += 1
        for f in num_fields:
            a[f] += r[f]

    path = os.path.join(OUT_DIR, "netra_unions.csv")
    fields = ["seat_name", "district", "upazila", "union", "center_count",
              "total_voters", "valid_votes", "rejected_votes", "absent_voters",
              "bnp_alliance", "jamaat_alliance", "independent", "other_party"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k in sorted(agg):
            w.writerow(agg[k])
    print(f"Wrote {len(agg)} unions to {path}")


def write_seat_csvs(centers):
    """Aggregate centers to constituency level."""
    agg = defaultdict(lambda: {
        "district": "", "center_count": 0, "union_count": 0,
        "total_voters": 0, "valid_votes": 0, "rejected_votes": 0, "absent_voters": 0,
        "bnp_alliance": 0, "jamaat_alliance": 0, "independent": 0, "other_party": 0,
    })
    num_fields = ["total_voters", "valid_votes", "rejected_votes", "absent_voters",
                  "bnp_alliance", "jamaat_alliance", "independent", "other_party"]

    unions_seen = defaultdict(set)
    for r in centers:
        seat = r["seat_name"]
        a = agg[seat]
        if not a["district"]:
            a["district"] = r["district"]
        a["center_count"] += 1
        for f in num_fields:
            a[f] += r[f]
        unions_seen[seat].add((r["district"], r["upazila"], r["union"]))

    for seat in agg:
        agg[seat]["union_count"] = len(unions_seen[seat])

    fields = ["seat_name", "district", "union_count", "center_count",
              "total_voters", "valid_votes", "rejected_votes", "absent_voters",
              "total_votes_cast",
              "bnp_alliance", "jamaat_alliance", "independent", "other_party"]

    rows = []
    for seat in sorted(agg):
        a = agg[seat]
        row = {
            "seat_name": seat, "district": a["district"],
            "union_count": a["union_count"], "center_count": a["center_count"],
            "total_votes_cast": a["valid_votes"] + a["rejected_votes"],
        }
        for f in num_fields:
            row[f] = a[f]
        rows.append(row)

    for name in ["netra_by_seat.csv", "netra_by_seat_wide.csv"]:
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"Wrote {len(rows)} seats to {path}")

    # Stats
    total_valid = sum(r["valid_votes"] for r in rows)
    total_rejected = sum(r["rejected_votes"] for r in rows)
    total_voters = sum(r["total_voters"] for r in rows)
    total_cast = total_valid + total_rejected
    print(f"\nStats: {len(rows)} seats, {sum(r['center_count'] for r in rows)} centers")
    print(f"Total voters: {total_voters:,}")
    print(f"Valid votes: {total_valid:,}  Rejected: {total_rejected:,}")
    print(f"Total votes cast: {total_cast:,}  Turnout: {total_cast / total_voters * 100:.1f}%")


def main():
    download_csv()
    centers = parse_centers()
    write_centers_csv(centers)
    write_unions_csv(centers)
    write_seat_csvs(centers)


if __name__ == "__main__":
    main()
