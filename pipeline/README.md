# Pipeline

Combines election data from 4 news sources into a single verified dataset.

## Workflow

```
scrape_tbs.py ──→ tbs_candidates.csv ──┐
scrape_ds.py  ──→ ds_candidates.csv  ──┤
scrape_bss.py ──→ bss_candidates.csv ──├──→ combine.py ──→ combined_candidates.csv ──→ build_wide.py ──→ constituency_wide.csv
scrape_dt.py  ──→ dt_candidates.csv  ──┘       │
                                           suspicious_matches.csv
```

## Scripts

### Scrapers

| Script | Source | Candidates per seat |
|--------|--------|-------------------|
| `scrape_tbs.py` | TBS News (HTML/JSON) | All candidates with votes |
| `scrape_ds.py` | Daily Star (CSV) | All candidates, votes for top 2 only |
| `scrape_bss.py` | BSS News (CSV) | Winner + runner-up only |
| `scrape_dt.py` | Dhaka Tribune (CSV) | All candidates with votes |

Each scraper normalizes seat names and party names, then outputs a simple 4-column CSV: `seat_name, candidate, party, votes`.

### combine.py

Merges the 4 source CSVs into one `combined_candidates.csv` using fuzzy name matching:

1. **Pass 1** — Strict match (threshold 0.75): align candidates across sources by name similarity + party bonus
2. **Pass 2** — Relaxed match (threshold 0.55): merge single-source orphans into existing clusters
3. **Pass 3** — Force-merge same party: assumes one candidate per party per seat (skips independents)

Vote counts are resolved by clustering values within 2% tolerance and taking the median, or falling back to priority order: DT > TBS > DS > BSS.

Outputs `suspicious_matches.csv` for cross-party conflicts and low-similarity merges.

### build_wide.py

Pivots `combined_candidates.csv` into a wide-format table (`constituency_wide.csv`) with:

- Metadata columns: division, district, area, voter counts, referendum results
- Winner/runner-up info
- One column per party with vote counts
- Independent votes summed into `independent_total`

Metadata comes from DT seats JSON + TBS/DS CSVs.

## Running

```bash
# Run all in order:
python3 pipeline/scrape_tbs.py
python3 pipeline/scrape_ds.py
python3 pipeline/scrape_bss.py
python3 pipeline/scrape_dt.py
python3 pipeline/combine.py
python3 pipeline/build_wide.py
```
