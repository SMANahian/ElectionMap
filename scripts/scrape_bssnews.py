"""
scrape_bssnews.py
=================

Scrapes constituency-level results from BSS News election page.

Usage::

    python3 scripts/scrape_bssnews.py
"""

import csv
import os
import re
import sys
import urllib.request

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(__file__))
from normalize import normalize_party, normalize_seat_name


URL = "https://www.bssnews.net/perlament-election-2026"
OUTPUT = "result_from_source/result_from_bssnews.csv"

BSS_PARTY_MAP = {
    "BNP": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "National Citizen Party - NCP": "National Citizen Party (NCP)",
    "National Citizens Party - NCP": "National Citizen Party (NCP)",
    "National Citizens Party (NCP)": "National Citizen Party (NCP)",
    "Islamic movement Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Islami Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Islamic Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Jamiat Ulamae Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Jamiat Ulama-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Jatiya Party - JAPA": "Jatiya Party (JaPa)",
    "Bangladesh Khilafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Khelafat Majlis": "Khelafat Majlis",
    "Khilafat Majlis": "Khelafat Majlis",
    "Bangladesh Development Party - BDP": "Bangladesh Development Party (BDP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Amar Bangladesh Party": "Amar Bangladesh Party (AB)",
    "Bangladesh National Party-BJP": "Bangladesh Jatiya Party (BJP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Mass Solidarity Movement": "Ganosanhati Andolan (GSA)",
    "Individual - Rumin Farhana": "Independent Candidate (Independent)",
    "Gono Odhikar Parishad": "Gono Odhikar Parishad (GOP)",
    "Khelafat Majlis": "Khelafat Majlis",
}


def normalize_bss_party(raw):
    """Normalize BSS party name."""
    if not raw:
        return "Unknown"
    raw = raw.strip()
    if "independent" in raw.lower():
        return "Independent Candidate (Independent)"
    if raw in BSS_PARTY_MAP:
        return BSS_PARTY_MAP[raw]
    result = normalize_party(raw)
    return result


def parse_candidate_cell(text):
    """Parse 'Name( Won )Party' or 'Name( Closest )Party' format."""
    # Pattern: "Name( Won )Party" or "Name( Closest )Party"
    m = re.match(r'^(.+?)\(\s*(?:Won|Closest|Runner)\s*\)(.+)$', text, re.I)
    if m:
        name = m.group(1).strip()
        party = m.group(2).strip()
        return name, normalize_bss_party(party)
    # Fallback: try to split on known party names at the end
    for party_key in sorted(BSS_PARTY_MAP.keys(), key=len, reverse=True):
        if text.endswith(party_key):
            name = text[:-len(party_key)].strip()
            return name, normalize_bss_party(party_key)
    # Try common patterns without markers
    for suffix in ["BNP", "Bangladesh Jamaat-e-Islami", "National Citizen Party - NCP",
                    "Jatiya Party", "Jatiya Party - JAPA", "Independent"]:
        if text.endswith(suffix):
            name = text[:-len(suffix)].strip()
            return name, normalize_bss_party(suffix)
    return text.strip(), "Unknown"


def download_page(url):
    """Download the full HTML page."""
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "bssnews_election_2026.html")

    # Use cache if exists
    if os.path.exists(cache_path):
        print(f"Using cached HTML from {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    print(f"Downloading {url}...")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    print(f"Downloaded {len(html):,} bytes")

    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved raw HTML to {cache_path}")
    return html


def parse_bss_html(html):
    """Parse the BSS News election results — multiple tables across divisions."""
    # Strip inline base64 images (large data URIs confuse the parser)
    html = re.sub(r'src="data:image/[^"]*"', 'src=""', html)
    # Fix malformed cells: some candidate cells have </div> without opening <div>
    # (missing <div style="color:green/red">) — add it so BeautifulSoup doesn't break
    html = re.sub(r'(<td[^>]*>)\s*<img ', r'\1<div><img ', html)
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Find ALL tr elements across all tables (page has one table per division)
    all_rows = soup.find_all("tr")
    print(f"Found {len(all_rows)} total table rows")

    for row in all_rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Columns: Seat No. | Seat | Total Center | Top Scorer | Votes Received | Nearest Contender | (runner votes?)
        seat_no = cells[0].get_text(strip=True)
        seat_name_raw = cells[1].get_text(strip=True)

        # Skip header rows
        if seat_name_raw in ("Seat", "") or seat_no in ("Seat No.", ""):
            continue

        # Normalize seat name
        seat_name = normalize_seat_name(seat_name_raw)

        # Parse winner (cell 3) — always present if we have 4+ cells
        winner_cell = cells[3].get_text(strip=True)
        winner_name, winner_party = parse_candidate_cell(winner_cell)

        # Parse winner votes (cell 4) — may be missing for incomplete rows
        winner_votes = None
        if len(cells) > 4:
            v = re.sub(r'[^\d]', '', cells[4].get_text(strip=True))
            if v:
                winner_votes = int(v)

        # Parse runner-up (cell 5) — may be missing
        runner_name, runner_party = "", "Unknown"
        runner_votes = None
        if len(cells) > 5:
            runner_cell = cells[5].get_text(strip=True)
            runner_name, runner_party = parse_candidate_cell(runner_cell)
        if len(cells) > 6:
            v = re.sub(r'[^\d]', '', cells[6].get_text(strip=True))
            if v:
                runner_votes = int(v)

        results.append({
            "seat_number": seat_no,
            "seat_name": seat_name,
            "winner_name": winner_name,
            "winner_party": winner_party,
            "winner_votes": winner_votes,
            "runner_name": runner_name,
            "runner_party": runner_party,
            "runner_votes": runner_votes,
        })

    return results


def main():
    html = download_page(URL)
    results = parse_bss_html(html)
    print(f"Parsed {len(results)} seat results")

    if not results:
        print("ERROR: No results parsed")
        return

    # Write CSV
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), OUTPUT)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "seat_number", "seat_name",
            "winner_name", "winner_party", "winner_votes",
            "runner_name", "runner_party", "runner_votes"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"Saved to {output_path}")

    # Quick stats
    parties = {}
    for r in results:
        p = r["winner_party"]
        parties[p] = parties.get(p, 0) + 1
    print("\nSeats won by party:")
    for p, c in sorted(parties.items(), key=lambda x: -x[1]):
        print(f"  {p}: {c}")


if __name__ == "__main__":
    main()
