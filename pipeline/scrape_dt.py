"""
scrape_dt.py — Extract per-candidate vote data from Dhaka Tribune.

Reads from result_from_source/dhakatribune_party_by_seat.csv (long format).
DT has all candidates with vote counts for all seats.

Output: pipeline/dt_candidates.csv
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_party, normalize_seat_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "result_from_source", "dhakatribune_party_by_seat.csv")
OUTPUT = os.path.join(BASE, "pipeline", "dt_candidates.csv")


def main():
    results = []
    with open(INPUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            votes_raw = row.get("votes", "")
            try:
                votes = int(float(votes_raw)) if votes_raw and votes_raw not in ("-", "") else 0
            except (ValueError, TypeError):
                votes = 0
            candidate = row.get("candidate", "").strip()
            if not candidate:
                continue
            results.append({
                "seat_name": normalize_seat_name(row["seat_name"]),
                "candidate": candidate,
                "party": normalize_party(row.get("party", "").strip()),
                "votes": votes,
            })

    print(f"Parsed {len(results)} candidate entries from Dhaka Tribune")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["seat_name", "candidate", "party", "votes"])
        w.writeheader()
        w.writerows(results)
    print(f"Saved to {OUTPUT}")

    seats = len({r["seat_name"] for r in results})
    print(f"Seats: {seats}, Candidates: {len(results)}")


if __name__ == "__main__":
    main()
