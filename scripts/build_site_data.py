#!/usr/bin/env python3
"""Build site/data/seat_data.json from results/seat_results.csv."""

import csv
import json
import os
import sys

# Add parent dir so we can import normalize
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from normalize import normalize_seat_name


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base, "results", "seat_results.csv")
    out_dir = os.path.join(base, "site", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "seat_data.json")

    data = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seat = row["seat_name"]
            key = normalize_seat_name(seat)

            def flt(col):
                v = row.get(col, "")
                if v == "" or v is None:
                    return 0.0
                return float(v)

            total_votes = int(flt("total_votes"))
            total_voters = int(flt("total_voters"))
            turnout = flt("turnout_ratio")
            margin = flt("victory_margin_ratio")

            bnp_r = flt("bnp_ratio")
            jamaat_r = flt("jamaat_ratio")
            dem_r = flt("democracy_platform_ratio")
            eleven_r = flt("eleven_party_alliance_ratio")
            bnp_all_r = flt("bnp_alliance_ratio")

            denom = bnp_r + eleven_r
            bnp_vs = bnp_r / denom if denom > 0 else 0.0

            # Parse top 3 from the top_three column
            top3_raw = row.get("top_three", "")
            top3 = []
            if top3_raw:
                import re
                # Split by %), then parse each chunk
                parts = top3_raw.split("%)")
                for part in parts[:3]:
                    part = part.strip().strip(",").strip()
                    if not part:
                        continue
                    # Find last '(' which precedes the percentage
                    idx = part.rfind("(")
                    if idx < 0:
                        continue
                    party = part[:idx].strip()
                    pct_str = part[idx+1:]
                    try:
                        top3.append({"party": party, "pct": round(float(pct_str), 1)})
                    except ValueError:
                        pass

            entry = {
                "name": key,
                "district": row.get("district", ""),
                "division": row.get("division", ""),
                "total_votes": total_votes,
                "total_voters": total_voters,
                "winner": row.get("winner_party", ""),
                "turnout": round(turnout, 6),
                "margin": round(margin, 6),
                "top3": top3,
                "stats": {
                    "bnp": round(bnp_r, 6),
                    "jamaat": round(jamaat_r, 6),
                    "democracy_platform": round(dem_r, 6),
                    "eleven_party_alliance": round(eleven_r, 6),
                    "bnp_alliance": round(bnp_all_r, 6),
                    "bnp_vs_eleven_party_alliance": round(bnp_vs, 6),
                    "turnout": round(turnout, 6),
                    "victory_margin": round(margin, 6),
                },
            }
            data[key] = entry

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"Wrote {len(data)} seats to {out_path}")


if __name__ == "__main__":
    main()
