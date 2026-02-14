"""
scrape_votes.py
================

This script scrapes constituency‑level vote data for Bangladesh's
2026 parliamentary election from **The Business Standard** (TBS)
election portal.  The TBS website embeds election results in a
large JSON object within a `<script>` tag.  The scraper first
attempts to download the live page (using a realistic browser
User‑Agent), then falls back to a locally saved snapshot if
download fails.  It parses the embedded JSON and computes vote
totals for every party and for a set of coalitions defined in
a configuration file.

The configuration file (`coalitions.json`) should define a
mapping from coalition codes (e.g. ``"bnp"``) to a dictionary
containing a human‑readable ``display_name``, a list of
``keywords`` used to recognise candidate parties, and a
``color_scale`` that determines how maps are coloured.  Each
keyword is compared case‑insensitively against the candidate's
party name; if any keyword is found, the candidate's votes are
attributed to that coalition.

The script produces three CSV files:

* **Seat‑level results** (``--output_seat_results``): one row
  per constituency with the total votes cast, vote totals and
  ratios for each coalition.
* **Aggregated party totals** (``--output_party_votes``): total
  votes received nationally by each party, sorted from most to
  least votes.
* **Party votes by constituency** (``--output_party_by_seat``):
  one row per party per constituency showing how many votes that
  party received in that seat.  This can be used to create
  additional statistics or maps.

Example usage::

    python3 scripts/scrape_votes.py \
        --config config/coalitions.json \
        --url https://www.tbsnews.net/election-2026 \
        --local_html data/tbs_election_2026.html \
        --output_seat_results results/seat_results.csv \
        --output_party_votes results/party_totals.csv \
        --output_party_by_seat results/party_by_seat.csv \
        --save_html

In this example the script will attempt to fetch live data from
the TBS site and will fall back to the local snapshot if that
fails.  It will then write the three CSV outputs into the
``results`` directory and, if ``--save_html`` is specified, it
will save the downloaded HTML into ``data/tbs_election_2026_downloaded.html``
for future inspection.

This script requires the following Python packages: ``requests``,
``beautifulsoup4``, ``pandas``.

"""

import argparse
import json
import logging
import os
import re
from typing import Dict, Any, Tuple, List, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd


def download_tbs_page(url: str) -> Optional[str]:
    """Attempt to download the TBS election page.

    This helper sends two requests: one to the ``view-source:``
    scheme, which may return a static HTML snapshot, and one to the
    regular URL.  Some network environments or TBS server
    restrictions may prevent downloading, so a local HTML file
    should be provided via ``--local_html`` as a fallback.

    Parameters
    ----------
    url : str
        The base URL of the election portal (e.g. ``"https://www.tbsnews.net/election-2026"``).

    Returns
    -------
    Optional[str]
        The HTML text of the page if the download succeeded; otherwise
        ``None``.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
    }
    # Attempt to fetch the view-source version first
    view_source_url = f"view-source:{url}"
    try:
        resp = requests.get(view_source_url, headers=headers, timeout=20)
        if resp.ok and len(resp.text) > 10000:
            logging.info("Downloaded view-source successfully")
            return resp.text
    except Exception as exc:
        logging.debug(f"View-source download failed: {exc}")
    # Fallback to the normal URL
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.ok and len(resp.text) > 10000:
            logging.info("Downloaded page successfully")
            return resp.text
    except Exception as exc:
        logging.debug(f"Normal download failed: {exc}")
    return None


def extract_election_data_from_html(html_text: str) -> Dict[str, Any]:
    """Extract the embedded ``election2026`` JSON from the TBS HTML.

    The election results are stored in a Drupal settings object
    ``"election2026"`` within a script tag.  This function locates
    that object, identifies the matching braces, and decodes the JSON
    string.

    Parameters
    ----------
    html_text : str
        Raw HTML of the TBS page.

    Returns
    -------
    dict
        A Python dictionary containing the parsed election data.
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    script_content = None
    for script in soup.find_all('script'):
        if script.string and '"election2026"' in script.string:
            script_content = script.string
            break
    if script_content is None:
        raise ValueError("Could not locate election2026 data in the HTML")
    # Find the start of the election2026 object
    start = script_content.find('"election2026"')
    if start == -1:
        raise ValueError("election2026 key not present in script")
    colon = script_content.find(':', start)
    brace_start = script_content.find('{', colon)
    depth = 1
    brace_end = None
    for idx, char in enumerate(script_content[brace_start + 1:], start=brace_start + 1):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
        if depth == 0:
            brace_end = idx
            break
    if brace_end is None:
        raise ValueError("Failed to locate the end of the election2026 JSON object")
    json_text = script_content[brace_start:brace_end + 1]
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to decode election data: {exc}")
    return data


def load_coalitions(config_path: str) -> Dict[str, Dict[str, Any]]:
    """Load coalition definitions from a JSON config file.

    Parameters
    ----------
    config_path : str
        Path to a JSON file defining coalition metadata.

    Returns
    -------
    dict
        Mapping from coalition code to a dictionary containing
        ``display_name``, ``keywords`` and ``color_scale``.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        coalitions = json.load(f)
    # Normalise keyword lists to lower case for easier matching
    for meta in coalitions.values():
        meta['keywords'] = [kw.lower() for kw in meta.get('keywords', [])]
    return coalitions


def party_in_coalition(party_name: str, keywords: List[str]) -> bool:
    """Check whether a party name matches any keyword in a coalition.

    Parameters
    ----------
    party_name : str
        The party name from the TBS dataset.
    keywords : list of str
        Lower‑case substrings that identify coalition membership.

    Returns
    -------
    bool
        ``True`` if ``party_name`` contains any keyword; ``False`` otherwise.
    """
    if not party_name:
        return False
    name_lc = party_name.lower()
    return any(kw in name_lc for kw in keywords)


def _extract_candidate_name(candidate: Dict[str, Any]) -> str:
    for key in ('candidate_name', 'name', 'candidate', 'full_name', 'candidateName'):
        value = candidate.get(key)
        if value:
            return str(value).strip()
    return 'Unknown'


def compute_results(data: Dict[str, Any], coalitions: Dict[str, Dict[str, Any]]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute constituency and party vote totals and coalition metrics.

    Parameters
    ----------
    data : dict
        Parsed election data with ``constituencies`` and ``candidates`` keys.
    coalitions : dict
        Coalition definitions loaded from the config file.

    Returns
    -------
    tuple
        A tuple of three DataFrames:

        1. **seat_results_df** – one row per constituency.  Columns include
           ``seat_id``, ``seat_number``, ``seat_name``, ``total_votes`` and
           for each coalition ``<code>_votes`` and ``<code>_ratio``.

        2. **party_totals_df** – one row per party showing the total
           number of votes received across all constituencies.

        3. **party_by_seat_df** – one row per combination of seat and
           party showing the votes that party received in that seat.
    """
    constituencies: Dict[str, Any] = data.get('constituencies', {})
    candidates_by_seat: Dict[str, List[Dict[str, Any]]] = data.get('candidates', {})
    seat_records: List[Dict[str, Any]] = []
    party_vote_totals: Dict[str, int] = {}
    party_by_seat_records: List[Dict[str, Any]] = []
    seat_party_votes: Dict[str, Dict[str, int]] = {}
    for seat_id, seat_info in constituencies.items():
        seat_number = seat_info.get('seat_number')
        seat_name = seat_info.get('seat_name')
        results = seat_info.get('election_results', {})
        # Normalise results to dict: keys are candidate diids
        if isinstance(results, list):
            result_dict = {}
        else:
            result_dict = results
        total_votes = 0
        coalition_counts = {code: 0 for code in coalitions}
        seat_votes_by_party: Dict[str, int] = {}
        candidate_rankings: List[Tuple[int, str, str]] = []
        # Build lookup for candidate definitions keyed by diid
        candidate_list = candidates_by_seat.get(seat_id, [])
        candidates_by_diid = {str(cand.get('diid')): cand for cand in candidate_list}
        for diid, result in result_dict.items():
            votes = result.get('votes')
            if votes is None:
                continue
            total_votes += votes
            candidate = candidates_by_diid.get(str(diid), {})
            party_name = candidate.get('party') or 'UNKNOWN'
            # Accumulate per party totals
            party_vote_totals[party_name] = party_vote_totals.get(party_name, 0) + votes
            seat_votes_by_party[party_name] = seat_votes_by_party.get(party_name, 0) + votes
            # Record this party in this seat
            party_by_seat_records.append({
                'seat_id': seat_id,
                'seat_number': seat_number,
                'seat_name': seat_name,
                'party': party_name,
                'votes': votes,
            })
            candidate_name = _extract_candidate_name(candidate)
            candidate_rankings.append((votes, candidate_name, party_name))
            # Update coalition counters
            for code, meta in coalitions.items():
                keywords = meta.get('keywords', [])
                if party_in_coalition(party_name, keywords):
                    coalition_counts[code] += votes
        # Compute ratios
        if total_votes == 0:
            ratios = {code: 0.0 for code in coalitions}
        else:
            ratios = {code: (coalition_counts[code] / total_votes) for code in coalitions}
        # Build seat record
        top_three_candidates = ''
        top_three_parties = ''
        if candidate_rankings and total_votes > 0:
            candidate_rankings.sort(key=lambda row: row[0], reverse=True)
            top_entries = candidate_rankings[:3]
            top_three_candidates = ', '.join(
                f"{name} ({party}) {votes / total_votes * 100:.1f}%"
                for votes, name, party in top_entries
            )
            top_three_parties = ', '.join(
                f"{party} ({votes / total_votes * 100:.1f}%)"
                for votes, _, party in top_entries
            )

        record = {
            'seat_id': seat_id,
            'seat_number': seat_number,
            'seat_name': seat_name,
            'total_votes': total_votes,
            'top_three_candidates': top_three_candidates,
            'top_three': top_three_parties,
        }
        for code in coalitions:
            record[f'{code}_votes'] = coalition_counts[code]
            record[f'{code}_ratio'] = ratios[code]
        seat_records.append(record)
        seat_party_votes[seat_id] = seat_votes_by_party
    # Convert to DataFrames
    all_parties = sorted(party_vote_totals.keys())
    for record in seat_records:
        party_votes = seat_party_votes.get(record['seat_id'], {})
        for party_name in all_parties:
            record[party_name] = party_votes.get(party_name, 0)
    seat_results_df = pd.DataFrame(seat_records)
    # Aggregate party totals
    party_totals_df = pd.DataFrame(sorted(party_vote_totals.items(), key=lambda x: x[1], reverse=True), columns=['party', 'votes'])
    # Party by seat DataFrame
    party_by_seat_df = pd.DataFrame(party_by_seat_records)
    return seat_results_df, party_totals_df, party_by_seat_df


def main() -> None:
    parser = argparse.ArgumentParser(description='Scrape vote data from the TBS election portal and compute coalition metrics.')
    parser.add_argument('--config', default='config/coalitions.json', help='Path to the coalition configuration JSON file.')
    parser.add_argument('--url', default='https://www.tbsnews.net/election-2026', help='Base URL of the TBS election portal.')
    parser.add_argument('--local_html', default='data/tbs_election_2026.html', help='Fallback HTML file to use if the live page cannot be downloaded.')
    parser.add_argument('--output_seat_results', default='results/seat_results.csv', help='CSV path for seat-level results.')
    parser.add_argument('--output_party_votes', default='results/party_totals.csv', help='CSV path for aggregated party vote totals.')
    parser.add_argument('--output_party_by_seat', default='results/party_by_seat.csv', help='CSV path for party votes by constituency.')
    parser.add_argument('--save_html', action='store_true', help='Save the downloaded HTML to the data directory for inspection.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Ensure results directory exists
    out_dirs = {os.path.dirname(args.output_seat_results), os.path.dirname(args.output_party_votes), os.path.dirname(args.output_party_by_seat)}
    for d in out_dirs:
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

    # Load coalition definitions
    coalitions = load_coalitions(args.config)

    # Attempt to download live data
    html_text: Optional[str] = None
    if args.url:
        logging.info(f"Attempting to download election page from {args.url} ...")
        html_text = download_tbs_page(args.url)
        if html_text and args.save_html:
            download_path = os.path.join(os.path.dirname(args.local_html), 'tbs_election_2026_downloaded.html')
            with open(download_path, 'w', encoding='utf-8') as f:
                f.write(html_text)
            logging.info(f"Saved downloaded HTML to {download_path}")
    # Fallback to local file
    if not html_text:
        if args.local_html and os.path.exists(args.local_html):
            logging.info(f"Falling back to local HTML file {args.local_html}")
            with open(args.local_html, 'r', encoding='utf-8', errors='ignore') as f:
                html_text = f.read()
        else:
            raise RuntimeError("Failed to download the election page and no local HTML file provided.")

    # Extract data
    data = extract_election_data_from_html(html_text)
    # Compute results
    seat_df, party_totals_df, party_by_seat_df = compute_results(data, coalitions)
    # Write CSVs
    seat_df.to_csv(args.output_seat_results, index=False)
    party_totals_df.to_csv(args.output_party_votes, index=False)
    party_by_seat_df.to_csv(args.output_party_by_seat, index=False)
    logging.info(f"Wrote seat results to {args.output_seat_results}")
    logging.info(f"Wrote party totals to {args.output_party_votes}")
    logging.info(f"Wrote party-by-seat results to {args.output_party_by_seat}")
    # Print a summary of top parties
    logging.info("Top parties by votes:")
    for _, row in party_totals_df.head(15).iterrows():
        logging.info(f"  {row['party']}: {row['votes']:,}")


if __name__ == '__main__':
    main()