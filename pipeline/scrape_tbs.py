"""
scrape_tbs.py — Extract per-candidate vote data from TBS News.

Source: https://www.tbsnews.net/election-2026
Data is embedded as JSON inside a <script> tag in the page HTML.
Cached locally at data/tbs_election_2026.html.

TBS has the most complete data: all candidates with vote counts for all seats.

Output: pipeline/tbs_candidates.csv
"""

import csv
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalize import normalize_party, normalize_seat_name

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://www.tbsnews.net/election-2026"
CACHE = os.path.join(BASE, "data", "tbs_election_2026.html")
OUTPUT = os.path.join(BASE, "pipeline", "tbs_candidates.csv")


def download():
    if os.path.exists(CACHE):
        print(f"Using cached HTML: {CACHE}")
        with open(CACHE, encoding="utf-8") as f:
            return f.read()

    print(f"Downloading {URL}...")
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        f.write(html)
    return html


def parse(html):
    # Find the embedded JSON object with election data
    # Pattern: var election2026 = {...} or window.election2026 = {...}
    m = re.search(r'"election2026"\s*:\s*(\{.*?\})\s*[,;}\n]', html, re.DOTALL)
    if not m:
        # Try alternative patterns
        m = re.search(r'election2026["\']?\s*[:=]\s*(\{.*?\})\s*[,;}\n]', html, re.DOTALL)
    if not m:
        # Try to find constituencies + candidates JSON
        m = re.search(r'(\{"constituencies":\[.*?"candidates":\{.*?\}\})', html, re.DOTALL)
    if not m:
        print("ERROR: Could not find election JSON in HTML")
        return []

    data = json.loads(m.group(1))
    constituencies = data.get("constituencies", [])
    candidates_map = data.get("candidates", {})

    results = []
    for seat in constituencies:
        seat_id = str(seat.get("diid", seat.get("id", "")))
        seat_name = normalize_seat_name(seat.get("name", ""))
        if not seat_name:
            continue

        seat_candidates = candidates_map.get(seat_id, [])
        for cand in seat_candidates:
            name = cand.get("candidate_name", cand.get("name", "")).strip()
            party = normalize_party(cand.get("party", "").strip())
            votes_raw = cand.get("votes", cand.get("vote", 0))
            try:
                votes = int(str(votes_raw).replace(",", "")) if votes_raw else 0
            except (ValueError, TypeError):
                votes = 0

            if name:
                results.append({
                    "seat_name": seat_name,
                    "candidate": name,
                    "party": party,
                    "votes": votes,
                })

    return results


def main():
    # Fallback: if we can't parse the HTML, read from the existing party_by_seat CSV
    existing = os.path.join(BASE, "result_from_source", "tbsnews_party_by_seat.csv")

    if os.path.exists(existing):
        print(f"Reading from existing: {existing}")
        results = []
        with open(existing, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                votes_raw = row.get("votes", "")
                try:
                    votes = int(float(votes_raw)) if votes_raw and votes_raw != "-" else 0
                except (ValueError, TypeError):
                    votes = 0
                results.append({
                    "seat_name": normalize_seat_name(row["seat_name"]),
                    "candidate": row.get("candidate", "").strip(),
                    "party": normalize_party(row.get("party", "").strip()),
                    "votes": votes,
                })
    else:
        html = download()
        results = parse(html)

    # Deduplicate exact duplicates (same seat + candidate + party + votes)
    seen = set()
    deduped = []
    for r in results:
        key = (r["seat_name"], r["candidate"], r["party"], r["votes"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    if len(deduped) < len(results):
        print(f"Removed {len(results) - len(deduped)} exact duplicates")
    results = deduped

    print(f"Parsed {len(results)} candidate entries")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["seat_name", "candidate", "party", "votes"])
        w.writeheader()
        w.writerows(results)
    print(f"Saved to {OUTPUT}")

    seats = len({r["seat_name"] for r in results})
    print(f"Seats: {seats}, Candidates: {len(results)}")


if __name__ == "__main__":
    main()
