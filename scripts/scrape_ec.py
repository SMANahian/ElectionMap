"""
scrape_ec.py — Scrape official Election Commission results from http://103.183.38.66:81/

Uses asyncio + aiohttp for parallel downloads. Skips files that already exist.

API endpoints:
  GET /api/zillas?electionID=178
  GET /api/constituencies?electionID=178&zillaID={zilla_id}
  GET /api/center-wise-results?election_type_id=1&election_id=178&candidate_type=1
      &zilla_id={zilla_id}&constituency_id={const_id}&page=1&limit=99999
  GET /api/center-result-details?id={center_id}

Output: official_result/raw_data/  (JSON cache)
        official_result/ec_candidates.csv  (per-candidate aggregated)
"""

import asyncio, aiohttp, csv, json, os, sys, time
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "official_result", "raw_data")
OUTPUT = os.path.join(BASE, "official_result", "ec_candidates.csv")
os.makedirs(RAW_DIR, exist_ok=True)

API_BASE = "http://103.183.38.66:81/api"
ELECTION_ID = 178
ELECTION_TYPE_ID = 1
CANDIDATE_TYPE = 1

HEADERS = {
    "Accept": "*/*",
    "Referer": "http://103.183.38.66:81/election-result",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
}

# Concurrency settings
MAX_CONCURRENT = 20  # parallel requests
TIMEOUT = 60
MAX_RETRIES = 3


async def fetch_json(session, url, cache_path, sem):
    """Fetch JSON with cache check, semaphore, and retry."""
    # Skip if already cached (but re-fetch if it's an error response)
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                cached = json.load(f)
            if isinstance(cached, dict) and "error" in cached:
                pass  # Re-fetch error responses
            else:
                return cached
        except (json.JSONDecodeError, IOError):
            pass  # Re-fetch if corrupt

    async with sem:
        for attempt in range(MAX_RETRIES):
            try:
                timeout = aiohttp.ClientTimeout(total=TIMEOUT)
                async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                    text = await resp.text()
                    data = json.loads(text)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    return data
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    print(f"  FAILED: {cache_path}: {e}")
                    return None


async def main():
    print("=== EC Official Results Scraper (async) ===\n")

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    conn = aiohttp.TCPConnector(limit=MAX_CONCURRENT, limit_per_host=MAX_CONCURRENT)
    async with aiohttp.ClientSession(connector=conn) as session:

        # Step 1: Get zillas
        print("Fetching zillas...")
        zillas_url = f"{API_BASE}/zillas?electionID={ELECTION_ID}"
        zillas = await fetch_json(session, zillas_url,
                                  os.path.join(RAW_DIR, "zillas.json"), sem)
        if not zillas:
            sys.exit("Failed to fetch zillas")
        print(f"  {len(zillas)} zillas\n")

        # Step 2: Get constituencies (parallel across zillas)
        print("Fetching constituencies...")
        const_tasks = []
        for z in zillas:
            zid = z["zillaID"]
            url = f"{API_BASE}/constituencies?electionID={ELECTION_ID}&zillaID={zid}"
            cache = os.path.join(RAW_DIR, f"constituencies_{zid}.json")
            const_tasks.append((zid, z["zilla_name"],
                                fetch_json(session, url, cache, sem)))

        all_constituencies = []
        for zid, zname, task in const_tasks:
            consts = await task
            if consts:
                for c in consts:
                    all_constituencies.append({
                        "zilla_id": zid,
                        "zilla_name": zname,
                        "const_id": c["constituencyID"],
                        "const_name": c["constituency_name"],
                    })
        print(f"  {len(all_constituencies)} constituencies\n")

        # Save constituency list
        with open(os.path.join(RAW_DIR, "all_constituencies.json"), "w",
                  encoding="utf-8") as f:
            json.dump(all_constituencies, f, ensure_ascii=False, indent=2)

        # Step 3: Get centers for all constituencies (parallel)
        print("Fetching center lists...")
        center_tasks = []
        for c in all_constituencies:
            cid = c["const_id"]
            zid = c["zilla_id"]
            url = (f"{API_BASE}/center-wise-results?"
                   f"election_type_id={ELECTION_TYPE_ID}&election_id={ELECTION_ID}"
                   f"&candidate_type={CANDIDATE_TYPE}"
                   f"&zilla_id={zid}&constituency_id={cid}"
                   f"&page=1&limit=99999")
            cache = os.path.join(RAW_DIR, f"centers_{cid}.json")
            center_tasks.append((c, fetch_json(session, url, cache, sem)))

        # Collect all center IDs we need details for
        all_detail_ids = []  # (const_info, center_id)
        done_centers = 0
        for c, task in center_tasks:
            data = await task
            done_centers += 1
            if done_centers % 50 == 0:
                print(f"  {done_centers}/{len(center_tasks)} constituency center lists done")

            if not data:
                continue
            center_list = data.get("data", []) if isinstance(data, dict) else data
            for center in center_list:
                detail_id = center.get("v_c_id")
                if detail_id:
                    all_detail_ids.append((c, detail_id))

        print(f"  {len(all_detail_ids)} center details to fetch\n")

        # Step 4: Fetch all center details (parallel, the big one)
        print(f"Fetching center details ({MAX_CONCURRENT} parallel)...")
        detail_tasks = []
        for c, detail_id in all_detail_ids:
            url = f"{API_BASE}/center-result-details?id={detail_id}"
            cache = os.path.join(RAW_DIR, f"detail_{detail_id}.json")
            detail_tasks.append((c, detail_id, fetch_json(session, url, cache, sem)))

        # Process in batches for progress reporting
        batch_size = 500
        done = 0
        cached = 0
        detail_results = []

        for i in range(0, len(detail_tasks), batch_size):
            batch = detail_tasks[i:i + batch_size]
            for c, did, task in batch:
                result = await task
                detail_results.append((c, did, result))
                done += 1
                # Count cached
                cache_path = os.path.join(RAW_DIR, f"detail_{did}.json")
                if os.path.exists(cache_path):
                    cached += 1
            elapsed_pct = done / len(detail_tasks) * 100
            print(f"  {done}/{len(detail_tasks)} ({elapsed_pct:.1f}%) "
                  f"center details done")

    # Step 5: Aggregate results
    print("\nAggregating results...")
    results = defaultdict(lambda: {
        "const_name": "", "zilla_name": "",
        "candidates": defaultdict(lambda: {"symbol": "", "votes": 0}),
    })

    # Also aggregate center-level metadata
    center_meta = defaultdict(lambda: {
        "total_centers": 0, "total_voters": 0,
        "valid_votes": 0, "rejected_votes": 0, "absent_voters": 0,
    })

    # Load center metadata from cached center lists
    for c in all_constituencies:
        cid = c["const_id"]
        cache = os.path.join(RAW_DIR, f"centers_{cid}.json")
        if not os.path.exists(cache):
            continue
        try:
            with open(cache) as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue
        center_list = data.get("data", []) if isinstance(data, dict) else data
        meta = center_meta[cid]
        meta["total_centers"] = len(center_list)
        for center in center_list:
            meta["total_voters"] += int(center.get("total_voter", 0) or 0)
            meta["valid_votes"] += int(center.get("clear_total_vote", 0) or 0)
            meta["rejected_votes"] += int(center.get("cancel_total_vote", 0) or 0)
            meta["absent_voters"] += int(center.get("absent_voter", 0) or 0)

    # Aggregate candidate votes from detail results
    for c, did, detail in detail_results:
        if not detail:
            continue
        cid = c["const_id"]
        res = results[cid]
        res["const_name"] = c["const_name"]
        res["zilla_name"] = c["zilla_name"]
        for cand in detail.get("candidates", []):
            name = cand.get("candidate_name", "")
            symbol = cand.get("candidate_symbol", "")
            vote = int(cand.get("vote", 0) or 0)
            if name:
                res["candidates"][name]["symbol"] = symbol
                res["candidates"][name]["votes"] += vote

    # Write CSV
    fields = [
        "constituency_id", "constituency_name", "zilla_name",
        "candidate_name", "candidate_symbol", "votes",
        "total_centers", "total_voters", "valid_votes",
        "rejected_votes", "absent_voters",
    ]
    rows = []
    for cid in sorted(results.keys(), key=lambda x: int(x)):
        res = results[cid]
        meta = center_meta[cid]
        for cand_name, cand_data in sorted(
                res["candidates"].items(), key=lambda x: -x[1]["votes"]):
            rows.append({
                "constituency_id": cid,
                "constituency_name": res["const_name"],
                "zilla_name": res["zilla_name"],
                "candidate_name": cand_name,
                "candidate_symbol": cand_data["symbol"],
                "votes": cand_data["votes"],
                "total_centers": meta["total_centers"],
                "total_voters": meta["total_voters"],
                "valid_votes": meta["valid_votes"],
                "rejected_votes": meta["rejected_votes"],
                "absent_voters": meta["absent_voters"],
            })

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    const_with_data = sum(1 for r in results.values() if r["candidates"])
    total_cands = sum(len(r["candidates"]) for r in results.values())
    print(f"\nDone! {const_with_data} constituencies, {total_cands} candidates, "
          f"{len(rows)} rows")
    print(f"Saved to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
