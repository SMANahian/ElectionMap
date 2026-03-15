# Bangladesh Election 2026 Interactive Maps
> **Note:** If you have a better or more authoritative vote data source, you're welcome to contribute! Submit a pull request with updated data or scraping logic—I'll gladly review and merge improvements.

An interactive choropleth map showing constituency-level results from
the 2026 Bangladesh general election across 300 parliamentary seats.
Built with Leaflet.js on a dark CARTO basemap with ColorBrewer palettes.

**Live site:** [smanahian.github.io/ElectionMap](https://smanahian.github.io/ElectionMap)

Built by S M A Nahian (<https://smanahian.com>).

### Map layers

| Layer | Description |
|-------|-------------|
| **BNP Vote Share** | Bangladesh Nationalist Party (Blues) |
| **Jamaat Vote Share** | Bangladesh Jamaat-e-Islami (Greens) |
| **11-Party Alliance** | Eleven-party Islamist coalition led by Jamaat (Purples) |
| **BNP Alliance** | BNP-led broader alliance (Oranges) |
| **BNP vs 11-Party** | Diverging red-yellow-blue map with sigmoid scaling |
| **Turnout** | Voter turnout percentage (Yellow-Green) |
| **Victory Margin** | Winner's margin of victory (Yellow-Red) |

## Repository structure

```
├── config/                 # Configuration files (coalitions.json)
├── data/                   # Input datasets (GeoJSON boundaries, saved HTML)
├── scripts/                # Python pipeline: scraping, merging, map generation
├── site_src/               # Website source (index.html)
├── site/                   # Deployed site (copied from site_src)
├── result_from_source/     # Raw scraped results from TBS News & Daily Star
├── vote_count_combined/    # Merged election results from both sources
├── official_result/        # Official Election Commission results
├── census_from_sid/        # 2022 Census data (BBS PDF extraction)
├── humdata_pop_stats/      # Subnational population statistics (HumData COD-PS)
├── unicef/                 # MICS6 district-level indicators (UNICEF)
├── poverty_data/           # District/upazila poverty statistics
├── pipeline/               # Data pipeline scripts (scraping, combining)
├── .github/workflows/      # GitHub Actions for auto-deployment
└── requirements.txt
```

## Quick start

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Scrape vote data**. The `scrape_votes.py` script downloads the latest TBS election page. If that fails it falls back to the saved HTML in `data/tbs_election_2026.html`.

   ```bash
   python scripts/scrape_votes.py \
     --config config/coalitions.json \
     --url https://www.tbsnews.net/election-2026 \
     --local_html data/tbs_election_2026.html \
     --output_seat_results results/seat_results.csv \
     --output_party_votes results/party_totals.csv \
     --output_party_by_seat results/party_by_seat.csv \
     --save_html
   ```

   This creates three CSV files in `results/`:
   * **seat_results.csv** – one row per constituency with vote shares for each coalition
   * **party_totals.csv** – national vote totals per party
   * **party_by_seat.csv** – vote totals per party per seat

3. **Preview the site locally**:

   ```bash
   python scripts/serve.py --dir site --port 8000
   ```

   Open [http://localhost:8000](http://localhost:8000) and select different statistics from the dropdown.

4. **Deploy to GitHub Pages**. Push to `main` and the GitHub Actions workflow will automatically publish the `site/` directory.

## Customising coalitions

Coalition definitions live in `config/coalitions.json`. Each entry has a unique key, display name, keyword list for matching candidate party names, and a colour gradient. Keywords are case-insensitive substring matches.

## Data sources

* **Election results** – [The Business Standard](https://www.tbsnews.net/election-2026) election portal and official Election Commission data
* **Constituency boundaries** – GeoReferenced Electoral Districts (GRED) dataset for Bangladesh's 2008 boundaries, also used by the [BBC Bangla election map](https://www.bbc.com/bengali/resources/idt-12e6dcd9-2189-4c28-aafb-b106e6d01189)
* **Coalition membership** – based on contemporary reporting and official party announcements

## Data repository

| Folder | Contents |
|--------|----------|
| [result_from_source/](result_from_source/) | Raw scraped results from TBS News and Daily Star |
| [vote_count_combined/](vote_count_combined/) | Merged results from both sources |
| [official_result/](official_result/) | Official Election Commission results |
| [census_from_sid/](census_from_sid/) | 2022 Census data (64 districts, 8 divisions) |
| [humdata_pop_stats/](humdata_pop_stats/) | Subnational population statistics (HumData) |
| [unicef/](unicef/) | MICS6 district-level indicators |
| [poverty_data/](poverty_data/) | Poverty statistics by district/upazila |

Each folder contains its own README with column descriptions.

## Credits

* **Project author** – S M A Nahian (<https://smanahian.com>)
* **Vote data** – The Business Standard election portal
* **Boundary data** – GRED / BBC Bangla
* **Tooling support** – Claude Code, ChatGPT agent, and GitHub Copilot

## License

This project is released under the MIT License. See `LICENSE` for details.
