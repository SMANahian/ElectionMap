"""
scrape_dt.py — Extract per-candidate vote data from Dhaka Tribune.

Reads from result_from_source/dhakatribune_party_by_seat.csv (long format).
DT has all candidates with vote counts for all seats.

Output: pipeline/dt_candidates.csv
"""

import csv, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_party, normalize_seat_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "result_from_source", "dhakatribune_party_by_seat.csv")
OUTPUT = os.path.join(BASE, "pipeline", "dt_candidates.csv")
FIELDS = ["seat_name", "candidate", "party", "votes"]


def parse_votes(raw):
    try:
        return int(float(raw)) if raw and raw not in ("-", "") else 0
    except (ValueError, TypeError):
        return 0


def main():
    results = []
    with open(INPUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            candidate = row.get("candidate", "").strip()
            if not candidate:
                continue
            results.append({
                "seat_name": normalize_seat_name(row["seat_name"]),
                "candidate": candidate,
                "party": normalize_party(row.get("party", "").strip()),
                "votes": parse_votes(row.get("votes", "")),
            })

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(results)

    seats = len({r["seat_name"] for r in results})
    print(f"Parsed {len(results)} candidate entries from Dhaka Tribune")
    print(f"Saved to {OUTPUT} — {seats} seats, {len(results)} candidates")


if __name__ == "__main__":
    main()
