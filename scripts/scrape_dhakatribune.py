"""
scrape_dhakatribune.py
======================

Scrapes ALL candidate-level results from Dhaka Tribune election API.

The DT site (election.dhakatribune.com) loads data via a JSON API:
  - GET /get-seats/{division_id}  → list of seats per division (divisions 1-8)
  - GET /get-candidate/{seat_id}  → all candidates with votes for a seat

This gives us complete per-candidate vote counts for all 300 constituencies,
making it as detailed as TBS News — and a strong cross-verification source.

Output files:
  - result_from_source/result_from_dhakatribune.csv        (winner + runner-up per seat)
  - result_from_source/dhakatribune_party_by_seat.csv      (all candidates, all parties)

Usage::

    python3 scripts/scrape_dhakatribune.py
"""

import csv
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from normalize import normalize_party, normalize_seat_name

BASE_URL = "https://election.dhakatribune.com"
OUTPUT_MAIN = "result_from_source/result_from_dhakatribune.csv"
OUTPUT_PBS = "result_from_source/dhakatribune_party_by_seat.csv"
NUM_DIVISIONS = 8  # Bangladesh has 8 administrative divisions

# DT uses its own party names — map to our canonical forms
DT_PARTY_MAP = {
    "Bangladesh Nationalist Party (BNP)": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "Independent": "Independent Candidate (Independent)",
    "National Citizen Party (NCP)": "National Citizen Party (NCP)",
    "Khelafat Majlish": "Khelafat Majlis",
    "Bangladesh Khelafat Majlish": "Bangladesh Khelafat Majlish (BKM)",
    "Revolutionary Workers Party of Bangladesh": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Islami Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Gonoshonghoti Andolon": "Ganosanhati Andolan (GSA)",
    "Gono Odhikar Parishad (GOP)": "Gono Odhikar Parishad (GOP)",
    "Bangladesh Jatiya Party": "Bangladesh Jatiya Party (BJP)",
    "Bangladesh Jatiya Party (BJP)": "Bangladesh Jatiya Party (BJP)",
    "Jatiya Party (JP)": "Jatiya Party (JaPa)",
    "Jatiya Party (JaPa)": "Jatiya Party (JaPa)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JASAD)": "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)",
    "Bangladesh Supreme Party (BSP)": "Bangladesh Supreme Party (BSP)",
    "Bangladesh Labour Party": "Bangladesh Labour Party",
    "Bangladesh Nationalist Front (BNF)": "Bangladesh Nationalist Front (BNF)",
    "Bangladesh Congress": "Bangladesh Congress",
    "Nationalist Democratic Movement (NDM)": "Nationalist Democratic Movement (NDM)",
    "National People's Party (NPP)": "National People's Party (NPP)",
    "Bangladesh Islami Front (BIF)": "Bangladesh Islami Front (BIF)",
    "Islamic Front Bangladesh (IFB)": "Islamic Front Bangladesh (IFB)",
    "Bangladesh Khelafat Andolon": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Khelafat Andolon (BKA)": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Development Party (BDP)": "Bangladesh Development Party (BDP)",
    "Bangladesh Nezame Islam Party (BNIP)": "Bangladesh Nezame Islam Party (BNIP)",
    "Bangladesh Liberal Democratic Party (LDP)": "Bangladesh Liberal Democratic Party (LDP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Amar Bangladesh Party (AB)": "Amar Bangladesh Party (AB)",
    "Bangladesh Muslim League (BML)": "Bangladesh Muslim League (BML)",
    "Bangladesh Muslim League": "Bangladesh Muslim League (BML)",
    "Bangladesh Republican Party (BRP)": "Bangladesh Republican Party (BRP)",
    "Communist Party of Bangladesh (CPB)": "Communist Party of Bangladesh (CPB)",
    "Bangladesh Samajtantrik Dal (Basad)": "Bangladesh Samajtantrik Dal (Basad)",
    "Gono Forum (GF)": "Gono Forum (GF)",
    "Zaker Party (ZP)": "Zaker Party (ZP)",
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Nagorik Oikya (NO)": "Nagorik Oikya (NO)",
    "Insaniyat Biplob Bangladesh (IBB)": "Insaniyat Biplob Bangladesh (IBB)",
    "Bangladesh Sangskritik Muktijote (BSM)": "Bangladesh Sangskritik Muktijote (BSM)",
    "Islami Oikya Jote (IOJ)": "Islami Oikya Jote (IOJ)",
    "Bangladesh Kallyan Party (BKP)": "Bangladesh Kallyan Party (BKP)",
    "Bangladesh Minority Janata Party (BMJP)": "Bangladesh Minority Janata Party (BMJP)",
    "Ganatantri Party (GP)": "Ganatantri Party (GP)",
}


def normalize_dt_party(raw):
    """Normalize Dhaka Tribune party name to canonical form."""
    if not raw:
        return "Unknown"
    raw = raw.strip()
    if raw in DT_PARTY_MAP:
        return DT_PARTY_MAP[raw]
    # Try the general normalizer as fallback
    result = normalize_party(raw)
    return result


def api_get(endpoint):
    """Make a GET request to the DT API and return parsed JSON."""
    url = BASE_URL + endpoint
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_seats():
    """Fetch all seat metadata across all 8 divisions."""
    cache_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "dt_seats.json"
    )

    # Use cache if it exists and has 300 seats
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            seats = json.load(f)
        if len(seats) >= 300:
            print(f"Using cached seat list ({len(seats)} seats)")
            return seats

    print("Fetching seat list from API...")
    all_seats = []
    for div_id in range(1, NUM_DIVISIONS + 1):
        data = api_get(f"/get-seats/{div_id}")
        all_seats.extend(data)
        print(f"  Division {div_id}: {len(data)} seats")
        time.sleep(0.2)  # Be polite

    print(f"Total seats: {len(all_seats)}")

    # Cache
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_seats, f, indent=2)

    return all_seats


def fetch_all_candidates(seats):
    """
    Fetch all candidates for all seats via the API.

    Uses cached JSON if available to avoid hitting the API repeatedly.

    Returns: {seat_id: [candidate_dicts]}
    """
    cache_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "dt_candidates.json"
    )

    # Use cache if it exists
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            cached = json.load(f)
        # Check completeness
        if len(cached) >= 295:  # Allow for a couple missing
            print(f"Using cached candidate data ({len(cached)} seats)")
            return cached

    print("Fetching candidate data from API (300 requests, ~60 seconds)...")
    all_candidates = {}
    for i, seat in enumerate(seats):
        seat_id = seat["id"]
        try:
            candidates = api_get(f"/get-candidate/{seat_id}")
            all_candidates[str(seat_id)] = candidates
        except Exception as e:
            print(f"  ERROR fetching seat {seat_id} ({seat['seat_name']}): {e}")

        # Progress update every 50 seats
        if (i + 1) % 50 == 0:
            print(f"  Fetched {i + 1}/{len(seats)} seats...")

        time.sleep(0.15)  # Rate limiting — ~6-7 requests/sec

    print(f"Fetched candidates for {len(all_candidates)} seats")

    # Cache
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(all_candidates, f, indent=2)
    print(f"Cached to {cache_path}")

    return all_candidates


def process_results(seats, all_candidates):
    """
    Process API data into two result sets:
    1. Main results (winner + runner-up per seat)
    2. Party-by-seat (all candidates, all parties)

    Returns: (main_results, pbs_results)
    """
    main_results = []
    pbs_results = []

    # Build seat_id → seat info lookup
    seat_lookup = {s["id"]: s for s in seats}

    for seat in seats:
        seat_id = str(seat["id"])
        seat_name_raw = seat["seat_name"]
        seat_name = normalize_seat_name(seat_name_raw)
        seat_no = seat["seat_no"]

        candidates = all_candidates.get(seat_id, [])

        if not candidates:
            # No candidate data — record as missing
            main_results.append({
                "seat_number": seat_no,
                "seat_name": seat_name,
                "total_voters": seat.get("total_voter", "").replace(",", ""),
                "total_centers": seat.get("total_center", ""),
                "winner_name": "",
                "winner_party": "Unknown",
                "winner_votes": None,
                "runner_name": "",
                "runner_party": "Unknown",
                "runner_votes": None,
            })
            continue

        # Sort candidates by votes (descending)
        for c in candidates:
            import re as _re
            vote_str = str(c.get("vote", 0) or 0)
            vote_str = _re.sub(r"[^\d]", "", vote_str)  # Strip everything non-digit
            c["_votes"] = int(vote_str) if vote_str else 0
        candidates.sort(key=lambda c: c["_votes"], reverse=True)

        # Winner and runner-up
        winner = candidates[0] if candidates else None
        runner = candidates[1] if len(candidates) > 1 else None

        total_voter_str = seat.get("total_voter", "").replace(",", "")

        main_results.append({
            "seat_number": seat_no,
            "seat_name": seat_name,
            "total_voters": total_voter_str,
            "total_centers": seat.get("total_center", ""),
            "winner_name": winner["name"] if winner else "",
            "winner_party": normalize_dt_party(winner["league"]) if winner else "Unknown",
            "winner_votes": winner["_votes"] if winner else None,
            "runner_name": runner["name"] if runner else "",
            "runner_party": normalize_dt_party(runner["league"]) if runner else "Unknown",
            "runner_votes": runner["_votes"] if runner else None,
        })

        # All candidates for party-by-seat
        for c in candidates:
            pbs_results.append({
                "seat_name": seat_name,
                "party": normalize_dt_party(c["league"]),
                "candidate": c["name"],
                "votes": c["_votes"],
            })

    return main_results, pbs_results


def build_wide_format(main_results, pbs_results):
    """
    Convert per-candidate results into wide format matching TBS/DS CSV structure:
    one row per seat, with columns for metadata, alliance votes/ratios, and per-party votes.
    """
    import json as _json

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    coalitions_path = os.path.join(base, "config/coalitions.json")

    # Build per-seat party→votes mapping (sum multiple candidates of same party)
    seat_party_votes = {}
    for r in pbs_results:
        seat = r["seat_name"]
        party = r["party"]
        votes = r["votes"]
        seat_party_votes.setdefault(seat, {})
        seat_party_votes[seat][party] = seat_party_votes[seat].get(party, 0) + votes

    # Collect all unique party names across all seats
    all_parties = sorted({p for spv in seat_party_votes.values() for p in spv})

    # Build top_three string per seat
    seat_top_three = {}
    seat_top_three_candidates = {}
    for seat, pvotes in seat_party_votes.items():
        sorted_parties = sorted(pvotes.items(), key=lambda x: -x[1])
        total = sum(pvotes.values())
        top3 = sorted_parties[:3]
        # Find candidate names for top 3
        cand_lookup = {}
        for r in pbs_results:
            if r["seat_name"] == seat:
                cand_lookup.setdefault(r["party"], []).append((r["candidate"], r["votes"]))

        top3_cand_parts = []
        top3_parts = []
        for party, votes in top3:
            pct = votes / total * 100 if total > 0 else 0
            # Get top candidate for this party
            cands = cand_lookup.get(party, [])
            cands.sort(key=lambda x: -x[1])
            cand_name = cands[0][0] if cands else ""
            top3_cand_parts.append(f"{cand_name} ({party}) {pct:.1f}%")
            top3_parts.append(f"{party} ({pct:.1f}%)")

        seat_top_three_candidates[seat] = ", ".join(top3_cand_parts)
        seat_top_three[seat] = ", ".join(top3_parts)

    # Load coalitions for alliance vote computation
    coalitions = {}
    if os.path.exists(coalitions_path):
        with open(coalitions_path) as f:
            coalitions = _json.load(f)

    # Build rows
    rows = []
    for mr in main_results:
        seat = mr["seat_name"]
        pvotes = seat_party_votes.get(seat, {})
        total_votes = sum(pvotes.values())

        row = {
            "seat_name": seat,
            "total_voters": mr.get("total_voters", ""),
            "total_votes": total_votes if total_votes > 0 else "-",
            "top_three_candidates": seat_top_three_candidates.get(seat, ""),
            "top_three": seat_top_three.get(seat, ""),
        }

        # Alliance vote columns + ratios
        for alliance_key, config in coalitions.items():
            keywords = config.get("keywords", [])
            alliance_total = 0
            for party, votes in pvotes.items():
                for kw in keywords:
                    if kw.lower() in party.lower():
                        alliance_total += votes
                        break
            votes_col = f"{alliance_key}_votes"
            ratio_col = f"{alliance_key}_ratio"
            row[votes_col] = alliance_total if alliance_total > 0 else "-"
            if total_votes > 0 and alliance_total > 0:
                row[ratio_col] = round(alliance_total / total_votes, 6)
            else:
                row[ratio_col] = "-"

        # Per-party vote columns
        for party in all_parties:
            row[party] = pvotes.get(party, "-")

        rows.append(row)

    return rows, all_parties


def main():
    # Step 1: Get all seat metadata
    seats = fetch_all_seats()

    # Step 2: Fetch all candidates for all seats
    all_candidates = fetch_all_candidates(seats)

    # Step 3: Process into result sets
    main_results, pbs_results = process_results(seats, all_candidates)
    print(f"\nProcessed {len(main_results)} seats, {len(pbs_results)} candidate entries")

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Step 4: Write main CSV in wide format (matching TBS/DS structure)
    wide_rows, all_parties = build_wide_format(main_results, pbs_results)

    # Build fieldnames matching TBS/DS order: metadata, alliance cols, party cols
    import json as _json
    coalitions_path = os.path.join(base, "config/coalitions.json")
    coalitions = {}
    if os.path.exists(coalitions_path):
        with open(coalitions_path) as f:
            coalitions = _json.load(f)

    alliance_fields = []
    for key in coalitions:
        alliance_fields.extend([f"{key}_votes", f"{key}_ratio"])

    fieldnames = (
        ["seat_name", "total_voters", "total_votes",
         "top_three_candidates", "top_three"]
        + alliance_fields
        + sorted(all_parties)
    )

    main_path = os.path.join(base, OUTPUT_MAIN)
    os.makedirs(os.path.dirname(main_path), exist_ok=True)
    with open(main_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in wide_rows:
            writer.writerow(r)
    print(f"Saved main results (wide format) to {main_path}")

    # Step 5: Write party-by-seat CSV (long format, all candidates)
    pbs_path = os.path.join(base, OUTPUT_PBS)
    with open(pbs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "seat_name", "party", "candidate", "votes",
        ])
        writer.writeheader()
        for r in pbs_results:
            writer.writerow(r)
    print(f"Saved party-by-seat (long format) to {pbs_path}")

    # Stats
    parties = {}
    for r in main_results:
        p = r["winner_party"]
        parties[p] = parties.get(p, 0) + 1
    print("\nSeats won by party:")
    for p, c in sorted(parties.items(), key=lambda x: -x[1]):
        print(f"  {p}: {c}")

    total_candidates = len(pbs_results)
    seats_with_data = sum(1 for r in main_results if r["winner_votes"])
    print(f"\nTotal candidates across all seats: {total_candidates}")
    print(f"Seats with vote data: {seats_with_data}/{len(main_results)}")


if __name__ == "__main__":
    main()
