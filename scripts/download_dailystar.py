"""
download_dailystar.py
=====================

Downloads all district-level election pages from The Daily Star's
election 2026 portal.  Each district page contains results for every
constituency in that district.

The script first queries the Daily Star API to enumerate all divisions
and districts, then downloads one HTML page per district into the
``data/dailystar_pages/`` directory.  A seat-index JSON file
(``data/dailystar_seats.json``) is also saved for use by the scraper.

Usage::

    python3 scripts/download_dailystar.py

The script skips pages that have already been downloaded (unless
``--force`` is given).
"""

import argparse
import json
import logging
import os
import time

import requests

BASE_URL = "https://www.thedailystar.net"
API_BASE = f"{BASE_URL}/api/districts"
PAGE_URL = f"{BASE_URL}/election2026data"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

OUTPUT_DIR = "data/dailystar_pages"
SEATS_JSON = "data/dailystar_seats.json"


def fetch_json(url: str) -> list:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def build_seat_index() -> tuple[list[dict], list[dict]]:
    """Query the Daily Star API to get all divisions, districts, and seats.

    Returns a tuple of (all_seats, districts_to_download).
    """
    divisions = fetch_json(f"{API_BASE}/divisions")
    logging.info(f"Found {len(divisions)} divisions")

    all_seats = []
    districts_to_download = []

    for div in divisions:
        districts = fetch_json(f"{API_BASE}/division/{div['id']}")
        logging.info(f"  {div['name']}: {len(districts)} districts")

        for dist in districts:
            seats = fetch_json(f"{API_BASE}/district/{dist['id']}/seats")
            districts_to_download.append({
                "division_name": div["name"],
                "division_id": div["id"],
                "district_name": dist["name"],
                "district_id": dist["id"],
                "num_seats": len(seats),
            })
            for seat in seats:
                all_seats.append({
                    "division": div["name"],
                    "division_id": div["id"],
                    "district": dist["name"],
                    "district_id": dist["id"],
                    "seat_name": seat["name"],
                    "seat_id": seat["id"],
                })

    logging.info(f"Total: {len(all_seats)} seats across {len(districts_to_download)} districts")
    return all_seats, districts_to_download


def download_district_page(division_id: str, district_id: str, output_path: str) -> bool:
    """Download a single district page and save to disk."""
    url = f"{PAGE_URL}?division={division_id}&district={district_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.ok and len(resp.text) > 5000:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            return True
        else:
            logging.warning(f"Bad response for {url}: status={resp.status_code}, len={len(resp.text)}")
            return False
    except Exception as exc:
        logging.error(f"Failed to download {url}: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download Daily Star election 2026 district pages.")
    parser.add_argument("--output_dir", default=OUTPUT_DIR, help="Directory to save HTML pages.")
    parser.add_argument("--seats_json", default=SEATS_JSON, help="Path to save the seat index JSON.")
    parser.add_argument("--force", action="store_true", help="Re-download pages even if they already exist.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between downloads.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    os.makedirs(args.output_dir, exist_ok=True)

    # Build seat index from API
    logging.info("Fetching seat index from Daily Star API...")
    all_seats, districts = build_seat_index()

    # Save seat index
    with open(args.seats_json, "w", encoding="utf-8") as f:
        json.dump(all_seats, f, indent=2, ensure_ascii=False)
    logging.info(f"Saved seat index to {args.seats_json}")

    # Download each district page
    downloaded = 0
    skipped = 0
    failed = 0

    for dist in districts:
        filename = f"{dist['district_name'].lower().replace(' ', '_')}_{dist['district_id']}.html"
        output_path = os.path.join(args.output_dir, filename)

        if os.path.exists(output_path) and not args.force:
            logging.info(f"  Skipping {dist['district_name']} (already downloaded)")
            skipped += 1
            continue

        logging.info(f"  Downloading {dist['district_name']} ({dist['num_seats']} seats)...")
        ok = download_district_page(dist["division_id"], dist["district_id"], output_path)
        if ok:
            downloaded += 1
        else:
            failed += 1

        time.sleep(args.delay)

    logging.info(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
