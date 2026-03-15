"""
build_wide.py — Build wide-format constituency table with metadata + party vote columns.

Collects metadata from DT JSON (voters, centers, area, referendum),
plus division/district from TBS/DS CSVs.

Pivots combined_candidates.csv into party vote columns per constituency.
All independents are summed into one column.

Input:  pipeline/combined_candidates.csv
        data/dt_seats.json, result_from_source/{tbsnews,dailystar}_party_by_seat.csv
Output: pipeline/constituency_wide.csv
"""

import csv, json, os, re, sys
from collections import defaultdict, OrderedDict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_seat_name, normalize_location_name, PARTY_CANONICAL

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPE = os.path.dirname(os.path.abspath(__file__))

COMBINED = os.path.join(PIPE, "combined_candidates.csv")
DT_SEATS = os.path.join(BASE, "data", "dt_seats.json")
DS_WIDE = os.path.join(BASE, "result_from_source", "result_from_dailystar.csv")
OUTPUT = os.path.join(PIPE, "constituency_wide.csv")

# CSVs to pull division/district from (tried in order, first value wins)
DIVISION_SOURCES = [
    os.path.join(BASE, "result_from_source", "tbsnews_party_by_seat.csv"),
    os.path.join(BASE, "result_from_source", "dailystar_party_by_seat.csv"),
]


def parse_dt_number(s):
    """Parse DT number strings like '519,460' or '176197'."""
    if not s:
        return 0
    s = re.sub(r"[^\d]", "", str(s))
    return int(s) if s else 0


def canon_party(p):
    return PARTY_CANONICAL.get(p, p)


def load_metadata():
    """Collect per-seat metadata from all available sources."""
    meta = defaultdict(dict)

    # DT seats JSON — richest metadata
    if os.path.exists(DT_SEATS):
        dt_fields = {
            "total_voters": "total_voter", "male_voters": "male_voter",
            "female_voters": "female_voter", "total_centers": "total_center",
            "referendum_yes": "yes", "referendum_no": "no",
        }
        for s in json.load(open(DT_SEATS)):
            seat = normalize_seat_name(s.get("seat_name", ""))
            if not seat:
                continue
            for our_key, dt_key in dt_fields.items():
                meta[seat][our_key] = parse_dt_number(s.get(dt_key))
            meta[seat]["total_candidates"] = s.get("total_candidate", 0)
            if s.get("seats_area"):
                meta[seat]["area"] = s["seats_area"]

    # Division/district from TBS then DS (first value wins)
    for csv_path in DIVISION_SOURCES:
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                if not seat:
                    continue
                for field in ("division", "district"):
                    if field not in meta[seat] and row.get(field):
                        meta[seat][field] = normalize_location_name(row[field])

    # Total votes cast — collect from all sources, pick best agreement
    votes_cast_sources = defaultdict(dict)  # seat → {source_name: value}

    # DT wide CSV
    DT_WIDE = os.path.join(BASE, "result_from_source", "result_from_dhakatribune.csv")
    for label, path in [("ds", DS_WIDE), ("dt", DT_WIDE)]:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                tv = row.get("total_votes", "")
                if seat and tv and tv != "-":
                    try:
                        votes_cast_sources[seat][label] = int(float(tv))
                    except (ValueError, TypeError):
                        pass

    # TBS wide CSV
    TBS_WIDE = os.path.join(BASE, "result_from_source", "tbsnews_party_by_seat.csv")
    if os.path.exists(TBS_WIDE):
        with open(TBS_WIDE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seat = normalize_seat_name(row.get("seat_name", ""))
                tv = row.get("total_votes", "")
                if seat and tv and tv != "-":
                    try:
                        votes_cast_sources[seat]["tbs"] = int(float(tv))
                    except (ValueError, TypeError):
                        pass

    # Note: Netra News data (netra_total_votes.csv) has union-level valid_votes
    # but 518/5034 unions span multiple constituencies, inflating per-seat totals.
    # Not used for total_votes_cast resolution.

    # Store raw sources; resolve later when we know total_known_votes
    meta["_votes_cast_sources"] = votes_cast_sources

    return meta


def resolve_total_votes_cast(meta, seat, total_known):
    """Resolve total_votes_cast using source clustering + total_known_votes as reference."""
    votes_cast_sources = meta.get("_votes_cast_sources", {})
    src_vals = votes_cast_sources.get(seat, {})
    vals = {s: v for s, v in src_vals.items() if v > 0}
    if not vals:
        return 0
    if len(vals) == 1:
        return next(iter(vals.values()))

    # Cluster within 5%
    clusters = []
    for s, v in sorted(vals.items(), key=lambda x: x[1]):
        placed = False
        for cl in clusters:
            ref = cl[0][1]
            if ref > 0 and abs(v - ref) / ref <= 0.05:
                cl.append((s, v))
                placed = True
                break
        if not placed:
            clusters.append([(s, v)])

    if len(clusters) == 1:
        return max(v for _, v in clusters[0])

    # Multiple disagreeing clusters: prefer the one closest to total_known_votes
    if total_known > 0:
        def cluster_score(cl):
            best_v = max(v for _, v in cl)
            # Simply pick the value closest to total_known_votes
            return (-abs(best_v - total_known), len(cl))
        best = max(clusters, key=cluster_score)
    else:
        best = max(clusters, key=lambda cl: (len(cl), max(v for _, v in cl)))

    return max(v for _, v in best)


META_FIELDS = [
    "seat_name", "division", "district", "area",
    "total_voters", "male_voters", "female_voters",
    "total_centers", "total_candidates",
    "total_votes_cast", "total_known_votes", "vote_diff",
    "referendum_yes", "referendum_no",
    "winner", "winner_party", "winner_votes",
    "runner_up", "runner_up_party", "runner_up_votes",
    "independent_total",
]


def main():
    with open(COMBINED, encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))

    by_seat = defaultdict(list)
    for c in candidates:
        by_seat[c["seat_name"]].append(c)

    # Collect parties sorted by total votes (for column order)
    party_totals = defaultdict(int)
    for c in candidates:
        p = canon_party(c["party"])
        if not p.lower().startswith("independent"):
            party_totals[p] += int(c["votes"])
    sorted_parties = sorted(party_totals, key=lambda p: -party_totals[p])

    meta = load_metadata()
    all_fields = META_FIELDS + sorted_parties

    # Fields populated from metadata (everything except winner/runner-up/independent)
    META_FROM_DICT = [
        "division", "district", "area",
        "total_voters", "male_voters", "female_voters",
        "total_centers", "total_candidates",
        "total_votes_cast", "referendum_yes", "referendum_no",
    ]

    rows = []
    for seat in sorted(by_seat):
        seat_cands = sorted(by_seat[seat], key=lambda c: -int(c["votes"]))
        m = meta.get(seat, {})

        row = OrderedDict()
        row["seat_name"] = seat

        # Metadata from external sources (DT JSON, TBS/DS CSVs)
        for field in META_FROM_DICT:
            row[field] = m.get(field, "")

        # Winner = highest votes, runner-up = second highest
        for i, prefix in enumerate(["winner", "runner_up"]):
            if i < len(seat_cands):
                row[prefix] = seat_cands[i]["candidate"]
                row[f"{prefix}_party"] = canon_party(seat_cands[i]["party"])
                row[f"{prefix}_votes"] = seat_cands[i]["votes"]
            else:
                row[prefix] = row[f"{prefix}_party"] = row[f"{prefix}_votes"] = ""

        # Per-party vote columns + independent total
        independent_total = 0
        party_votes = defaultdict(int)
        for c in seat_cands:
            p = canon_party(c["party"])
            v = int(c["votes"])
            if "independent" in p.lower():
                independent_total += v
            else:
                party_votes[p] += v

        row["independent_total"] = independent_total or ""
        for p in sorted_parties:
            row[p] = party_votes[p] or ""

        # Total known votes = sum of all candidate votes in this seat
        total_known = independent_total + sum(party_votes.values())
        row["total_known_votes"] = total_known or ""
        # Resolve total_votes_cast using total_known as reference
        tvc = resolve_total_votes_cast(meta, seat, total_known)
        if tvc:
            row["total_votes_cast"] = tvc
        row["vote_diff"] = (tvc - total_known) if tvc and total_known else ""

        rows.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Saved {len(rows)} constituencies to {OUTPUT}")
    print(f"Metadata fields: {len(META_FIELDS)}, Party columns: {len(sorted_parties)}")
    print(f"Total columns: {len(all_fields)}")


if __name__ == "__main__":
    main()
