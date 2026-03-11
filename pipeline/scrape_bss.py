"""
scrape_bss.py — Extract per-candidate vote data from BSS News.

Reads from result_from_source/result_from_bssnews.csv (winner + runner-up format).
BSS only has winner and runner-up per seat.

Output: pipeline/bss_candidates.csv
"""

import csv, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_party, normalize_seat_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT = os.path.join(BASE, "result_from_source", "result_from_bssnews.csv")
OUTPUT = os.path.join(BASE, "pipeline", "bss_candidates.csv")
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
            seat = normalize_seat_name(row["seat_name"])
            if not seat:
                continue
            # Extract winner and runner-up from the same row
            for prefix in ("winner", "runner"):
                name = row.get(f"{prefix}_name", "").strip()
                if not name:
                    continue
                # Strip status markers like "( Won )", "( Closest )"
                name = re.sub(r"\(\s*(Won|Closest)\s*\)", "", name).strip()
                party = normalize_party(row.get(f"{prefix}_party", "").strip())
                # BSS sometimes has "Unknown" party — use winner/runner position as hint
                if party == "Unknown" and prefix == "winner":
                    party = "Unknown (Winner)"
                elif party == "Unknown" and prefix == "runner":
                    party = "Unknown (Runner-up)"
                results.append({
                    "seat_name": seat,
                    "candidate": name,
                    "party": party,
                    "votes": parse_votes(row.get(f"{prefix}_votes", "")),
                })

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(results)

    seats = len({r["seat_name"] for r in results})
    print(f"Parsed {len(results)} candidate entries from BSS News")
    print(f"Saved to {OUTPUT} — {seats} seats, {len(results)} candidates")


if __name__ == "__main__":
    main()
