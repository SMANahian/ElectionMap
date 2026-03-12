"""
scrape_ec.py — Scrape official Election Commission results.

Source: http://103.183.38.66:81/ (geo-restricted to Bangladesh)
Uses asyncio + aiohttp for parallel downloads. Caches all responses as JSON.

Output: official_result/raw_data/  (JSON cache)
        official_result/ec_candidates.csv
"""

import asyncio, aiohttp, csv, json, os, sys
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "official_result", "raw_data")
OUTPUT = os.path.join(BASE, "official_result", "ec_candidates.csv")
os.makedirs(RAW, exist_ok=True)

API = "http://103.183.38.66:81/api"
HEADERS = {
    "Accept": "*/*",
    "Referer": "http://103.183.38.66:81/election-result",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}
CONCURRENT = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_cache(path):
    """Read cached JSON, return None if missing/corrupt/error."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "error" in data:
            return None  # re-fetch error responses
        return data
    except (json.JSONDecodeError, IOError):
        return None


async def fetch(session, url, path, sem):
    """Fetch JSON with caching, semaphore, and retry."""
    cached = read_cache(path)
    if cached is not None:
        return cached

    async with sem:
        for attempt in range(3):
            try:
                async with session.get(url, headers=HEADERS,
                                       timeout=aiohttp.ClientTimeout(total=60)) as r:
                    text = await r.text()
                    data = json.loads(text)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    return data
            except Exception as e:
                if attempt == 2:
                    print(f"  FAILED {path}: {e}")
                    return None
                await asyncio.sleep(2 * (attempt + 1))


def safe_int(val):
    return int(val or 0)


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

async def download():
    """Download all data from EC API into RAW directory."""
    sem = asyncio.Semaphore(CONCURRENT)
    conn = aiohttp.TCPConnector(limit=CONCURRENT, limit_per_host=CONCURRENT)

    async with aiohttp.ClientSession(connector=conn) as s:
        # 1. Zillas
        print("Fetching zillas...")
        zillas = await fetch(s, f"{API}/zillas?electionID=178",
                             f"{RAW}/zillas.json", sem)
        if not zillas:
            sys.exit("Failed to fetch zillas")
        print(f"  {len(zillas)} zillas")

        # 2. Constituencies per zilla
        print("Fetching constituencies...")
        tasks = {z["zillaID"]: fetch(s,
            f"{API}/constituencies?electionID=178&zillaID={z['zillaID']}",
            f"{RAW}/constituencies_{z['zillaID']}.json", sem)
            for z in zillas}

        constituencies = []  # [{zilla_id, zilla_name, const_id, const_name}]
        zilla_names = {z["zillaID"]: z["zilla_name"] for z in zillas}
        for zid, task in tasks.items():
            for c in (await task) or []:
                constituencies.append({
                    "zilla_id": zid, "zilla_name": zilla_names[zid],
                    "const_id": c["constituencyID"], "const_name": c["constituency_name"],
                })
        print(f"  {len(constituencies)} constituencies")

        with open(f"{RAW}/all_constituencies.json", "w", encoding="utf-8") as f:
            json.dump(constituencies, f, ensure_ascii=False, indent=2)

        # 3. Center lists per constituency
        print("Fetching center lists...")
        center_tasks = {
            c["const_id"]: fetch(s,
                f"{API}/center-wise-results?election_type_id=1&election_id=178"
                f"&candidate_type=1&zilla_id={c['zilla_id']}"
                f"&constituency_id={c['const_id']}&page=1&limit=99999",
                f"{RAW}/centers_{c['const_id']}.json", sem)
            for c in constituencies
        }

        # Collect v_c_ids for detail fetching
        details_needed = []  # [(const_info, v_c_id)]
        for c in constituencies:
            data = await center_tasks[c["const_id"]]
            if not data:
                continue
            centers = data.get("data", []) if isinstance(data, dict) else data
            for center in centers:
                vid = center.get("v_c_id")
                if vid:
                    details_needed.append((c, vid))
        print(f"  {len(details_needed)} center details to fetch")

        # 4. Center details (the big one)
        print(f"Fetching center details ({CONCURRENT} parallel)...")
        detail_tasks = [
            (c, vid, fetch(s, f"{API}/center-result-details?id={vid}",
                           f"{RAW}/detail_{vid}.json", sem))
            for c, vid in details_needed
        ]

        detail_results = []
        for i, (c, vid, task) in enumerate(detail_tasks, 1):
            detail_results.append((c, await task))
            if i % 500 == 0 or i == len(detail_tasks):
                print(f"  {i}/{len(detail_tasks)} ({i/len(detail_tasks)*100:.0f}%)")

    return constituencies, detail_results


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

def aggregate(constituencies, detail_results):
    """Aggregate per-center results into per-candidate CSV."""
    print("\nAggregating...")

    # Center metadata (voters, valid, rejected, absent)
    meta = {}
    for c in constituencies:
        cid = c["const_id"]
        data = read_cache(f"{RAW}/centers_{cid}.json")
        if not data:
            continue
        centers = data.get("data", []) if isinstance(data, dict) else data
        meta[cid] = {
            "total_centers": len(centers),
            "total_voters": sum(safe_int(x.get("total_voter")) for x in centers),
            "valid_votes": sum(safe_int(x.get("clear_total_vote")) for x in centers),
            "rejected_votes": sum(safe_int(x.get("cancel_total_vote")) for x in centers),
            "absent_voters": sum(safe_int(x.get("absent_voter")) for x in centers),
        }

    # Candidate votes
    results = defaultdict(lambda: {"const_name": "", "zilla_name": "",
                                   "candidates": defaultdict(lambda: {"symbol": "", "votes": 0})})
    for c, detail in detail_results:
        if not detail:
            continue
        cid = c["const_id"]
        res = results[cid]
        res["const_name"] = c["const_name"]
        res["zilla_name"] = c["zilla_name"]
        for cand in detail.get("candidates", []):
            name = cand.get("candidate_name", "")
            if name:
                res["candidates"][name]["symbol"] = cand.get("candidate_symbol", "")
                res["candidates"][name]["votes"] += safe_int(cand.get("vote"))

    # Write CSV
    fields = ["constituency_id", "constituency_name", "zilla_name",
              "candidate_name", "candidate_symbol", "votes",
              "total_centers", "total_voters", "valid_votes",
              "rejected_votes", "absent_voters"]
    rows = []
    for cid in sorted(results, key=int):
        res = results[cid]
        m = meta.get(cid, {})
        for name, cand in sorted(res["candidates"].items(), key=lambda x: -x[1]["votes"]):
            rows.append({
                "constituency_id": cid,
                "constituency_name": res["const_name"],
                "zilla_name": res["zilla_name"],
                "candidate_name": name,
                "candidate_symbol": cand["symbol"],
                "votes": cand["votes"],
                **{k: m.get(k, 0) for k in fields[6:]},
            })

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fields).writeheader()
        csv.DictWriter(f, fieldnames=fields).writerows(rows)

    print(f"\nDone! {len(results)} constituencies, "
          f"{sum(len(r['candidates']) for r in results.values())} candidates, "
          f"{len(rows)} rows")
    print(f"Saved to {OUTPUT}")


# ---------------------------------------------------------------------------

def main():
    print("=== EC Official Results Scraper ===\n")
    constituencies, detail_results = asyncio.run(download())
    aggregate(constituencies, detail_results)


if __name__ == "__main__":
    main()
