# Scripts

Pipeline scripts for scraping, processing, verifying, and visualizing Bangladesh Election 2026 data.

## Data Scraping

### `scrape_votes.py`
Scrapes constituency-level vote data from **The Business Standard (TBS)** election portal. Extracts the embedded `election2026` JSON object from the page source, which contains per-candidate vote counts for all 300 seats. Falls back to a locally saved HTML copy if the live download fails.

**Outputs** (to `result_from_source/`):
- `result_from_tbsnews.csv` — seat-level results with total votes, coalition votes and ratios
- `tbsnews_party_totals.csv` — national vote aggregates per party
- `tbsnews_party_by_seat.csv` — party-level votes broken down by constituency

Uses coalition definitions from `config/coalitions.json` to group parties into alliances.

### `download_dailystar.py`
Downloads all district-level election pages from **The Daily Star** API. Queries the API to enumerate divisions, districts, and seats, then saves individual district HTML pages to `data/dailystar_pages/` and creates a seat index JSON (`data/dailystar_seats.json`).

### `scrape_dailystar.py`
Parses locally downloaded Daily Star HTML pages. Extracts candidate names, party affiliations, vote counts (top 2 candidates per seat), and voter statistics (total, male, female, hijra). Maps Daily Star party symbols to standardized party names.

**Outputs** (to `result_from_source/`):
- `result_from_dailystar.csv`, `dailystar_party_totals.csv`, `dailystar_party_by_seat.csv`

## Data Processing & Verification

### `combine_votes.py`
Merges TBS and Daily Star results into a single comprehensive dataset. Normalizes seat names for matching, takes the max votes for each party when sources disagree, recalculates coalition ratios, and flags discrepancies.

**Output:** `vote_count_combined/combined_vote_counts.csv`

### `run_combine_top_alliances.py`
Specialized merger focusing on BNP Alliance vs Eleven-Party Alliance comparison. Merges both sources, handles party columns dynamically, and recalculates alliance ratios from max votes.

**Output:** `vote_count_combined/top_alliances_overview.csv`

### `verify_sources.py`
Cross-verifies data between TBS News and Daily Star at multiple levels:
- **Seat coverage** — which seats appear in each source
- **Seat-level results** — total votes, coalition votes/ratios, winner agreement
- **Candidate-level** — exact vote counts with fuzzy name matching
- **Party totals** — national-level aggregates per party

**Outputs** (to `result_from_source/`):
- `verification_summary.csv` — overall comparison statistics
- `verification_seat_mismatches.csv` — seat-level discrepancies
- `verification_vote_mismatches.csv` — candidate-level vote differences
- `verification_party_total_mismatches.csv` — national party total differences

### `verify_alliances.py`
Compares BNP Alliance and Eleven-Party Alliance vote totals between TBS and Daily Star, sorted by maximum absolute discrepancy.

**Output:** `result_from_source/alliance_mismatch_report.csv`

### `check_candidate_names.py`
Uses fuzzy string matching and phonetic analysis to identify candidate name variations between sources. Separates spelling differences from genuinely different candidates.

## Map Generation

### `build_map.py`
Generates interactive choropleth maps using Folium. Reads constituency-level results and GeoJSON boundaries, creates color-coded maps for each coalition defined in config. Includes hover tooltips showing top 3 candidates, supports a special BNP vs Eleven-Party Alliance relative strength map.

**Output:** `site/maps/*.html`

## Utilities

### `normalize.py`
Centralized normalization functions used across all scripts:
- `normalize_party()` — maps ~150 party name variations to standard forms
- `normalize_seat_name()` — standardizes constituency names
- `normalize_location_name()` — normalizes division/district names (handles aliases like "Bogra" → "Bogura")
- `normalize_candidate_name()` — removes titles, fixes common spelling variations

### `serve.py`
Simple HTTP server for local preview of the `site/` directory.
