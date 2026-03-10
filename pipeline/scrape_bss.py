"""
scrape_bss.py — Extract per-candidate vote data from BSS News.

Reads from result_from_source/result_from_bssnews.csv (winner + runner-up format).
BSS only has winner and runner-up per seat.

Output: pipeline/bss_candidates.csv
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_party, normalize_seat_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "result_from_source", "result_from_bssnews.csv")
OUTPUT = os.path.join(BASE, "pipeline", "bss_candidates.csv")


def main():
    results = []
    with open(INPUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seat = normalize_seat_name(row["seat_name"])
            if not seat:
                continue

            # Winner
            wname = row.get("winner_name", "").strip()
            if wname:
                wvotes_raw = row.get("winner_votes", "")
                try:
                    wvotes = int(float(wvotes_raw)) if wvotes_raw and wvotes_raw not in ("-", "") else 0
                except (ValueError, TypeError):
                    wvotes = 0
                results.append({
                    "seat_name": seat,
                    "candidate": wname,
                    "party": normalize_party(row.get("winner_party", "").strip()),
                    "votes": wvotes,
                })

            # Runner-up
            rname = row.get("runner_name", "").strip()
            if rname:
                rvotes_raw = row.get("runner_votes", "")
                try:
                    rvotes = int(float(rvotes_raw)) if rvotes_raw and rvotes_raw not in ("-", "") else 0
                except (ValueError, TypeError):
                    rvotes = 0
                results.append({
                    "seat_name": seat,
                    "candidate": rname,
                    "party": normalize_party(row.get("runner_party", "").strip()),
                    "votes": rvotes,
                })

    print(f"Parsed {len(results)} candidate entries from BSS News")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["seat_name", "candidate", "party", "votes"])
        w.writeheader()
        w.writerows(results)
    print(f"Saved to {OUTPUT}")

    seats = len({r["seat_name"] for r in results})
    print(f"Seats: {seats}, Candidates: {len(results)}")


if __name__ == "__main__":
    main()
