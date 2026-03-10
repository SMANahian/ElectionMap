"""
build_wide.py — Build wide-format constituency table with metadata + party vote columns.

Collects metadata from all sources (DT JSON has the richest: total_voter, male/female,
centers, area, total_candidate, yes/no referendum), plus division/district from TBS/DS.

Then pivots combined_candidates.csv into party vote columns per constituency.
All independents are summed into one column.

Input:  pipeline/combined_candidates.csv
        data/dt_seats.json (DT metadata)
        result_from_source/tbsnews_party_by_seat.csv (division, district)
        result_from_source/dailystar_party_by_seat.csv (division, district)
Output: pipeline/constituency_wide.csv
"""

import csv
import json
import os
import re
import sys
from collections import defaultdict, OrderedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_seat_name, normalize_location_name, PARTY_CANONICAL

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.dirname(os.path.abspath(__file__))

COMBINED = os.path.join(PIPE, "combined_candidates.csv")
DT_SEATS = os.path.join(BASE, "data", "dt_seats.json")
TBS_CSV = os.path.join(BASE, "result_from_source", "tbsnews_party_by_seat.csv")
DS_CSV = os.path.join(BASE, "result_from_source", "dailystar_party_by_seat.csv")
DS_WIDE = os.path.join(BASE, "result_from_source", "result_from_dailystar.csv")
OUTPUT = os.path.join(PIPE, "constituency_wide.csv")


def parse_dt_number(s):
    """Parse DT number strings like '519,460' or '176197'."""
    if not s:
        return 0
    s = re.sub(r"[^\d]", "", str(s))
    return int(s) if s else 0


def load_metadata():
    """Collect per-seat metadata from all available sources."""
    meta = defaultdict(dict)  # seat_name -> {field: value}

    # DT seats JSON — richest metadata
    if os.path.exists(DT_SEATS):
        dt_seats = json.load(open(DT_SEATS))
        for s in dt_seats:
            seat = normalize_seat_name(s.get("seat_name", ""))
            if not seat:
                continue
            meta[seat]["total_voters"] = parse_dt_number(s.get("total_voter"))
            meta[seat]["male_voters"] = parse_dt_number(s.get("male_voter"))
            meta[seat]["female_voters"] = parse_dt_number(s.get("female_voter"))
            meta[seat]["total_centers"] = parse_dt_number(s.get("total_center"))
            meta[seat]["total_candidates"] = s.get("total_candidate", 0)
            meta[seat]["referendum_yes"] = parse_dt_number(s.get("yes"))
            meta[seat]["referendum_no"] = parse_dt_number(s.get("no"))
            area = s.get("seats_area", "")
            if area:
                meta[seat]["area"] = area

    # TBS — division, district
    if os.path.exists(TBS_CSV):
        with open(TBS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                if not seat:
                    continue
                if "division" not in meta[seat] and row.get("division"):
                    meta[seat]["division"] = normalize_location_name(row["division"])
                if "district" not in meta[seat] and row.get("district"):
                    meta[seat]["district"] = normalize_location_name(row["district"])

    # DS — division, district (fill gaps)
    if os.path.exists(DS_CSV):
        with open(DS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                if not seat:
                    continue
                if "division" not in meta[seat] and row.get("division"):
                    meta[seat]["division"] = normalize_location_name(row["division"])
                if "district" not in meta[seat] and row.get("district"):
                    meta[seat]["district"] = normalize_location_name(row["district"])

    # DS wide — extra voter stats if available
    if os.path.exists(DS_WIDE):
        with open(DS_WIDE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                if not seat:
                    continue
                # DS total_votes (actual votes cast)
                tv = row.get("total_votes", "")
                if tv and tv != "-":
                    try:
                        meta[seat]["total_votes_cast"] = int(float(tv))
                    except (ValueError, TypeError):
                        pass

    return meta


def canon_party(p):
    return PARTY_CANONICAL.get(p, p)


def main():
    # Load combined candidates
    candidates = []
    with open(COMBINED, encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))

    # Group by seat
    by_seat = defaultdict(list)
    for c in candidates:
        by_seat[c["seat_name"]].append(c)

    # Collect all party names (canonicalized), track which are "Independent"
    all_parties = set()
    for c in candidates:
        p = canon_party(c["party"])
        if "independent" not in p.lower():
            all_parties.add(p)

    # Sort parties by total votes across all seats (descending) for column order
    party_totals = defaultdict(int)
    for c in candidates:
        p = canon_party(c["party"])
        if "independent" not in p.lower():
            party_totals[p] += int(c["votes"])
    sorted_parties = sorted(all_parties, key=lambda p: -party_totals[p])

    # Load metadata
    meta = load_metadata()

    # Build rows
    meta_fields = [
        "seat_name", "division", "district", "area",
        "total_voters", "male_voters", "female_voters",
        "total_centers", "total_candidates",
        "total_votes_cast", "referendum_yes", "referendum_no",
        "winner", "winner_party", "winner_votes",
        "runner_up", "runner_up_party", "runner_up_votes",
        "independent_total",
    ]
    party_fields = sorted_parties
    all_fields = meta_fields + party_fields

    rows = []
    for seat in sorted(by_seat.keys()):
        seat_cands = by_seat[seat]
        m = meta.get(seat, {})

        row = OrderedDict()
        row["seat_name"] = seat
        row["division"] = m.get("division", "")
        row["district"] = m.get("district", "")
        row["area"] = m.get("area", "")
        row["total_voters"] = m.get("total_voters", "")
        row["male_voters"] = m.get("male_voters", "")
        row["female_voters"] = m.get("female_voters", "")
        row["total_centers"] = m.get("total_centers", "")
        row["total_candidates"] = m.get("total_candidates", "")
        row["total_votes_cast"] = m.get("total_votes_cast", "")
        row["referendum_yes"] = m.get("referendum_yes", "")
        row["referendum_no"] = m.get("referendum_no", "")

        # Sort candidates by votes desc
        sorted_cands = sorted(seat_cands, key=lambda c: -int(c["votes"]))

        if len(sorted_cands) >= 1:
            row["winner"] = sorted_cands[0]["candidate"]
            row["winner_party"] = canon_party(sorted_cands[0]["party"])
            row["winner_votes"] = sorted_cands[0]["votes"]
        else:
            row["winner"] = row["winner_party"] = row["winner_votes"] = ""

        if len(sorted_cands) >= 2:
            row["runner_up"] = sorted_cands[1]["candidate"]
            row["runner_up_party"] = canon_party(sorted_cands[1]["party"])
            row["runner_up_votes"] = sorted_cands[1]["votes"]
        else:
            row["runner_up"] = row["runner_up_party"] = row["runner_up_votes"] = ""

        # Party vote columns
        independent_total = 0
        party_votes = defaultdict(int)
        for c in seat_cands:
            p = canon_party(c["party"])
            v = int(c["votes"])
            if "independent" in p.lower():
                independent_total += v
            else:
                party_votes[p] += v

        row["independent_total"] = independent_total if independent_total else ""

        for p in sorted_parties:
            row[p] = party_votes[p] if party_votes[p] else ""

        rows.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Saved {len(rows)} constituencies to {OUTPUT}")
    print(f"Metadata fields: {len(meta_fields)}, Party columns: {len(party_fields)}")
    print(f"Total columns: {len(all_fields)}")


if __name__ == "__main__":
    main()
