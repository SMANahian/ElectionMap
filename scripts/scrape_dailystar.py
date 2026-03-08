"""
scrape_dailystar.py
===================

Scrapes constituency-level vote data from locally downloaded
Daily Star election 2026 HTML pages (produced by download_dailystar.py).

The Daily Star pages show the top 2 candidates with vote counts per
constituency, plus all candidate names and party affiliations.  This
script extracts that data and produces CSV files with the same
structure as the TBS News scraper output so results can be
cross-verified.

Output CSVs:

* **Seat results** (``--output_seat_results``): one row per
  constituency with total votes, candidate details, coalition
  vote totals and ratios.
* **Party totals** (``--output_party_votes``): total votes by party
  across all constituencies.
* **Party by seat** (``--output_party_by_seat``): one row per
  party per constituency with vote counts.

Usage::

    python3 scripts/scrape_dailystar.py

Note: Only the top 2 candidates per seat have vote counts on the
Daily Star.  Other candidates are listed with 0 votes.
"""

import argparse
import glob
import json
import logging
import os
import re
from typing import Any

from bs4 import BeautifulSoup
import pandas as pd


# Normalize Daily Star party names to match TBS naming convention.
PARTY_NAME_MAP = {
    "BNP": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "Independent": "Independent Candidate (Independent)",
    "National Citizens Party - NCP": "National Citizen Party (NCP)",
    "Islamic Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Bangladesh Islamic Front": "Bangladesh Islami Front (BIF)",
    "Bangladesh Khilafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Khilafat Majlis": "Khelafat Majlis",
    "Liberal Democratic Party - LDP": "Bangladesh Liberal Democratic Party (LDP)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Jatiya Party - JAPA": "Jatiya Party (JaPa)",
    "Gono Odhikar Parishad": "Gono Odhikar Parishad (GOP)",
    "Gono Odhikar Porishad- GOP": "Gono Odhikar Parishad (GOP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Bangladesh Development Party - BDP": "Bangladesh Development Party (BDP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Jamiat Ulama-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Gono Forum": "Gono Forum (GF)",
    "Gano Forum": "Gono Forum (GF)",
    "Bangladesh Supreme Party - BSP": "Bangladesh Supreme Party (BSP)",
    "Zaker Party": "Zaker Party (ZP)",
    "Bangladesh Jasod": "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)",
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Jatiya Samajtantrik Dal (JSD Rab)": "Jatiya Samajtantrik Dal-JASAD",
    "Ganosamhati Andolon": "Ganosanhati Andolan (GSA)",
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League (BML)",
    "Bangladesh Nezam e Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Bangladesh Nezam Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Nagorik Oikya": "Nagorik Oikya (NO)",
    "Nagorik Oikko": "Nagorik Oikya (NO)",
    "Bangladesh Republican Party - BRP": "Bangladesh Republican Party (BRP)",
    "Communist Party of Bangladesh": "Communist Party of Bangladesh (CPB)",
    "Bangladesh Samajtantrik Dal": "Bangladesh Samajtantrik Dal (Basad)",
    "Insaniat Biplob Bangladesh - Insaniat Biplob": "Insaniyat Biplob Bangladesh (IBB)",
    "Nationalist Democratic Movement - NDM": "Nationalist Democratic Movement (NDM)",
    "Ganatantri Party": "Ganatantri Party (GP)",
    "Janatar Dal": "Janotar Dol",
    "Amjanatar Dal": "Amjanatar Dol",
    "Islamic Front Bangladesh - IFB": "Islamic Front Bangladesh (IFB)",
    "Bangladesher Biplobi Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Revolutionary Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Khelafat Andolon": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Sangskritik Muktijote": "Bangladesh Sangskritik Muktijote (BSM)",
    "Bangladesher Samajtantrik Dal (BSD)": "Bangladesh Samajtantrik Dal (Basad)",
    "Bangladesher Samajtantrik Dal (Marxist)": "Socialist Party of Bangladesh (Marxist) (SPB-M)",
    "Bangladesh Nationalist Front - BNF": "Bangladesh Nationalist Front (BNF)",
    "Bangladesh Kalyan Party": "Bangladesh Kallyan Party (BKP)",
    "Bangladesh Labor Party": "Bangladesh Labour Party",
    "Bangladesh Minority Janata Party - BMJP": "Bangladesh Minority Janata Party (BMJP)",
    "Bangladesh Nap": "Bangladesh National Awami Party–Bangladesh NAP (BNAP)",
    "Bangladesh Gonofront": "Gono Front (GF)",
    "Bangladesh Equal Rights Party": "Bangladesh Somo Odhikar Party (BEP)",
    "Islamic Oikkojot": "Islami Oikya Jote (IOJ)",
    "National People's Party - NPP": "National People's Party (NPP)",
    "National Democratic Party - JDP": "Jatiya Ganatantrik Party (JAGPA)",
    "Islamic Front Bangladesh": "Islamic Front Bangladesh (IFB)",
}


def normalize_party(name: str) -> str:
    """Normalize a DS party name to match TBS convention."""
    return PARTY_NAME_MAP.get(name, name)


def load_coalitions(config_path: str) -> dict[str, dict[str, Any]]:
    with open(config_path, "r", encoding="utf-8") as f:
        coalitions = json.load(f)
    for meta in coalitions.values():
        meta["keywords"] = [kw.lower() for kw in meta.get("keywords", [])]
    return coalitions


def party_in_coalition(party_name: str, keywords: list[str]) -> bool:
    if not party_name:
        return False
    name_lc = party_name.lower()
    return any(kw in name_lc for kw in keywords)


def parse_district_page(html_path: str) -> list[dict]:
    """Parse a single district HTML page and return a list of seat records.

    Each record contains:
      - seat_name, division, district
      - total_voters, male_voters, female_voters
      - candidates: list of {name, party, votes}
    """
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all(class_="election-constitution-card-container")
    seats = []

    for card in cards:
        record = extract_seat_from_card(card)
        if record:
            seats.append(record)

    return seats


def extract_seat_from_card(card) -> dict | None:
    """Extract structured data from one constituency card."""

    # --- Seat name from the winner banner or metadata ---
    seat_span = card.find("span", class_="text-green-600")
    if seat_span:
        seat_name = seat_span.get_text(strip=True)
    else:
        # No winner (postponed election) — get seat name from metadata
        card_text = card.get_text("\n", strip=True)
        seat_match = re.search(r"Seat\n(.+)", card_text)
        if not seat_match:
            return None
        seat_name = seat_match.group(1).strip()

    # --- Winner info from the banner ---
    winner_h3 = card.find("h3", class_=lambda c: c and "text-2xl" in c)
    winner_name = winner_h3.get_text(strip=True) if winner_h3 else ""

    winner_party_span = card.find(
        "span", class_=lambda c: c and "text-gray-700" in c and "bg-white" in c
    )
    winner_party = normalize_party(winner_party_span.get_text(strip=True)) if winner_party_span else ""

    # Winner votes from banner
    winner_votes_span = card.find(
        "span", class_=lambda c: c and "text-green-700" in c
    )
    winner_votes = None
    if winner_votes_span:
        vote_text = winner_votes_span.get_text(strip=True)
        m = re.search(r"([\d,]+)", vote_text)
        if m:
            winner_votes = int(m.group(1).replace(",", ""))

    # --- Candidate grid ---
    grid = card.find("div", class_="grid")
    candidates = []
    seen_winner = False

    if grid:
        cand_divs = grid.find_all("div", recursive=False)
        for cdiv in cand_divs:
            text_parts = cdiv.get_text(" | ", strip=True)
            cand = _parse_candidate_card(cdiv, text_parts)
            if cand:
                # Check if this is the winner (marked with WIN label)
                if "WIN" in text_parts and not seen_winner:
                    seen_winner = True
                candidates.append(cand)

    # If winner wasn't found in grid, add from banner
    if not seen_winner and winner_name:
        candidates.insert(0, {
            "name": winner_name,
            "party": winner_party,
            "votes": winner_votes,
        })

    # --- Voter statistics ---
    total_voters = 0
    male_voters = 0
    female_voters = 0

    card_text = card.get_text(" ", strip=True)
    tv_match = re.search(r"Total Voters\s*:?\s*([\d,]+)", card_text)
    if tv_match:
        total_voters = int(tv_match.group(1).replace(",", ""))

    male_match = re.search(r"Male\s*:?\s*([\d,]+)", card_text)
    if male_match:
        male_voters = int(male_match.group(1).replace(",", ""))

    female_match = re.search(r"Female\s*:?\s*([\d,]+)", card_text)
    if female_match:
        female_voters = int(female_match.group(1).replace(",", ""))

    # --- Division / District from card metadata ---
    division = ""
    district = ""
    div_match = re.search(r"Division\s+(\w[\w\s]*?)(?=\s+District)", card_text)
    if div_match:
        division = div_match.group(1).strip()
    dist_match = re.search(r"District\s+(\w[\w\s]*?)(?=\s+Seat)", card_text)
    if dist_match:
        district = dist_match.group(1).strip()

    return {
        "seat_name": seat_name,
        "division": division,
        "district": district,
        "total_voters": total_voters,
        "male_voters": male_voters,
        "female_voters": female_voters,
        "candidates": candidates,
    }


def _parse_candidate_card(cdiv, text_parts: str) -> dict | None:
    """Parse a single candidate card from the grid."""
    # Find candidate name (h3 tag)
    h3 = cdiv.find("h3")
    if not h3:
        return None
    name = h3.get_text(strip=True)

    # Find party (p tag with party info)
    party_p = cdiv.find("p")
    party = normalize_party(party_p.get_text(strip=True)) if party_p else ""

    # Find votes if present (None means data not available)
    votes = None
    if "Votes" in text_parts:
        m = re.search(r"Votes\s*\|?\s*([\d,]+)", text_parts)
        if m:
            votes = int(m.group(1).replace(",", ""))
        else:
            # Try different pattern
            m = re.search(r"([\d,]+)\s*$", text_parts)
            if m:
                votes = int(m.group(1).replace(",", ""))

    return {"name": name, "party": party, "votes": votes}


def compute_results(
    all_seats: list[dict],
    coalitions: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute seat results, party totals, and party-by-seat DataFrames."""

    seat_records = []
    party_vote_totals: dict[str, int] = {}
    party_by_seat_records = []
    seat_party_votes: dict[str, dict[str, int]] = {}

    for seat in all_seats:
        seat_name = seat["seat_name"]
        candidates = seat["candidates"]

        # Separate known votes (int) from unknown (None)
        known_votes = [c["votes"] for c in candidates if c["votes"] is not None]
        total_votes = sum(known_votes) if known_votes else None
        coalition_counts = {code: 0 for code in coalitions}
        votes_by_party: dict[str, Any] = {}
        candidate_rankings = []
        has_any_votes = total_votes is not None and total_votes > 0

        for cand in candidates:
            party = cand["party"] or "UNKNOWN"
            votes = cand["votes"]  # int or None
            name = cand["name"]

            if votes is not None:
                party_vote_totals[party] = party_vote_totals.get(party, 0) + votes
            # Store None to distinguish "no data" from 0
            votes_by_party[party] = votes if votes is not None else votes_by_party.get(party)

            party_by_seat_records.append({
                "seat_name": seat_name,
                "division": seat["division"],
                "district": seat["district"],
                "party": party,
                "candidate": name,
                "votes": votes,
            })

            if votes is not None and votes > 0:
                candidate_rankings.append((votes, name, party))

            if votes is not None:
                for code, meta in coalitions.items():
                    if party_in_coalition(party, meta.get("keywords", [])):
                        coalition_counts[code] += votes

        # Ratios
        if has_any_votes:
            ratios = {code: coalition_counts[code] / total_votes for code in coalitions}
        else:
            ratios = {code: None for code in coalitions}

        # Top candidates
        candidate_rankings.sort(key=lambda r: r[0], reverse=True)
        top_three_candidates = ""
        top_three_parties = ""
        if candidate_rankings and has_any_votes:
            top_entries = candidate_rankings[:3]
            top_three_candidates = ", ".join(
                f"{name} ({party}) {votes / total_votes * 100:.1f}%"
                for votes, name, party in top_entries
            )
            top_three_parties = ", ".join(
                f"{party} ({votes / total_votes * 100:.1f}%)"
                for votes, _, party in top_entries
            )

        record = {
            "seat_name": seat_name,
            "division": seat["division"],
            "district": seat["district"],
            "total_voters": seat["total_voters"] or None,
            "male_voters": seat["male_voters"] or None,
            "female_voters": seat["female_voters"] or None,
            "total_votes": total_votes,
            "top_three_candidates": top_three_candidates,
            "top_three": top_three_parties,
        }

        for code in coalitions:
            record[f"{code}_votes"] = coalition_counts[code] if has_any_votes else None
            record[f"{code}_ratio"] = ratios[code]

        seat_records.append(record)
        seat_party_votes[seat_name] = votes_by_party

    # Add per-party columns to seat records
    # None = party not present or votes unknown; int = actual votes
    all_parties = sorted(party_vote_totals.keys())
    for record in seat_records:
        pv = seat_party_votes.get(record["seat_name"], {})
        for party in all_parties:
            record[party] = pv.get(party)  # None if party not in this seat

    seat_df = pd.DataFrame(seat_records)
    party_totals_df = pd.DataFrame(
        sorted(party_vote_totals.items(), key=lambda x: x[1], reverse=True),
        columns=["party", "votes"],
    )
    party_by_seat_df = pd.DataFrame(party_by_seat_records)

    return seat_df, party_totals_df, party_by_seat_df


def main():
    parser = argparse.ArgumentParser(
        description="Scrape election data from downloaded Daily Star HTML pages."
    )
    parser.add_argument(
        "--pages_dir", default="data/dailystar_pages",
        help="Directory containing downloaded district HTML files.",
    )
    parser.add_argument(
        "--config", default="config/coalitions.json",
        help="Path to the coalition configuration JSON file.",
    )
    parser.add_argument(
        "--output_seat_results", default="result_from_source/result_from_dailystar.csv",
        help="CSV path for seat-level results.",
    )
    parser.add_argument(
        "--output_party_votes", default="result_from_source/dailystar_party_totals.csv",
        help="CSV path for aggregated party vote totals.",
    )
    parser.add_argument(
        "--output_party_by_seat", default="result_from_source/dailystar_party_by_seat.csv",
        help="CSV path for party votes by constituency.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Ensure output directories exist
    for path in [args.output_seat_results, args.output_party_votes, args.output_party_by_seat]:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)

    # Load coalition definitions
    coalitions = load_coalitions(args.config)

    # Parse all downloaded district pages
    html_files = sorted(glob.glob(os.path.join(args.pages_dir, "*.html")))
    if not html_files:
        raise FileNotFoundError(
            f"No HTML files found in {args.pages_dir}. "
            "Run download_dailystar.py first."
        )

    logging.info(f"Found {len(html_files)} district pages to parse")

    all_seats = []
    for html_path in html_files:
        seats = parse_district_page(html_path)
        logging.info(f"  {os.path.basename(html_path)}: {len(seats)} seats")
        all_seats.extend(seats)

    logging.info(f"Total seats parsed: {len(all_seats)}")

    # Compute results
    seat_df, party_totals_df, party_by_seat_df = compute_results(all_seats, coalitions)

    # Write CSVs (use '-' for missing/unavailable data)
    seat_df.to_csv(args.output_seat_results, index=False, na_rep="-")
    party_totals_df.to_csv(args.output_party_votes, index=False, na_rep="-")
    party_by_seat_df.to_csv(args.output_party_by_seat, index=False, na_rep="-")

    logging.info(f"Wrote seat results to {args.output_seat_results}")
    logging.info(f"Wrote party totals to {args.output_party_votes}")
    logging.info(f"Wrote party-by-seat to {args.output_party_by_seat}")

    logging.info("\nTop parties by votes:")
    for _, row in party_totals_df.head(15).iterrows():
        logging.info(f"  {row['party']}: {row['votes']:,}")

    logging.info(f"\nNote: Daily Star only shows votes for top 2 candidates per seat.")
    logging.info(f"Other candidates are listed with '-' (data not available).")


if __name__ == "__main__":
    main()
