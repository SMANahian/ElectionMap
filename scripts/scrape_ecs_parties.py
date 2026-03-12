"""
scrape_ecs_parties.py — Scrape registered political parties from ECS.

Source: https://ecs.gov.bd/en/political-parties
Output: official_result/ecs_party_symbols.csv
"""

import csv, json, os, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "official_result", "ecs_party_symbols.csv")

RSC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "text/x-component",
    "Rsc": "1",
}


def fetch_page(page):
    """Fetch party list from Next.js RSC endpoint."""
    url = f"https://ecs.gov.bd/en/political-parties?page={page}&_rsc=4zxs5"
    req = urllib.request.Request(url, headers=RSC_HEADERS)
    data = urllib.request.urlopen(req).read().decode("utf-8")

    idx = data.find('"data":[{"registration_number"')
    if idx < 0:
        return []

    # Bracket-match the JSON array
    start = data.index("[", idx)
    depth = 0
    for j in range(start, len(data)):
        if data[j] == "[":
            depth += 1
        elif data[j] == "]":
            depth -= 1
            if depth == 0:
                return json.loads(data[start : j + 1])
    return []


def main():
    parties = []
    seen = set()

    for page in range(1, 20):
        entries = fetch_page(page)
        if not entries:
            break

        for d in entries:
            reg = d["registration_number"]
            if reg in seen:
                continue
            seen.add(reg)

            name = d.get("name", {})
            sym = d.get("symbol", {})
            sym_name = sym.get("name", {}) if isinstance(sym, dict) else {}

            parties.append({
                "reg_no": reg,
                "name_en": name.get("en", ""),
                "name_bn": name.get("bn", ""),
                "symbol_bn": sym_name.get("bn", ""),
                "symbol_en": sym_name.get("en", ""),
                "status": d.get("status", ""),
            })

        print(f"Page {page}: {len(entries)} entries (total: {len(parties)})")

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(parties[0].keys()))
        w.writeheader()
        w.writerows(parties)

    print(f"\n{len(parties)} parties -> {OUTPUT}")
    for p in parties:
        print(f"  {p['reg_no']}  {p['symbol_bn']:<20} {p['name_en']}")


if __name__ == "__main__":
    main()
