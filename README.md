# Bangladesh Election 2026 Interactive Maps
> **Note:** If you have a better or more authoritative vote data source, you're welcome to contribute! Submit a pull request with updated data or scraping logic—I'll gladly review and merge improvements.
This project provides an open, reproducible pipeline for scraping
constituency‑level vote data from **The Business Standard** (TBS)
election portal, merging it with official boundary data, and
visualising the results as interactive maps.  The maps show the
vote share of four key blocs across Bangladesh’s 300 parliamentary
seats:

Built by S M A Nahian (<https://smanahian.com>). Vote data comes from
The Business Standard, and boundary data is based on GRED (as referenced
by the BBC Bangla election map).

* **BNP** – Bangladesh Nationalist Party
* **Jamaat** – Bangladesh Jamaat‑e‑Islami
* **Democracy Platform** – a six‑party alliance formed under the
  banner *Ganatantra Manch*【479248487050056†L181-L187】
* **Eleven-Party Alliance** – an eleven‑party coalition led by
  Jamaat‑e‑Islami【651089003901836†L170-L183】

## Repository structure

```
election_site/
├── config/             # Configuration files
│   └── coalitions.json # Defines coalition names, keywords and colour scales
├── data/               # Input datasets and fallback HTML
│   ├── constituencies.geojson        # Constituency boundaries (from GRED)
│   └── tbs_election_2026.html        # Saved TBS election page for offline scraping
├── results/            # Generated CSV results (ignored by Git)
├── scripts/            # Python scripts for scraping and map generation
│   ├── scrape_votes.py
│   ├── build_map.py
│   └── serve.py        # Simple HTTP server for local preview
├── site/               # Generated website (GitHub Pages artefact)
│   └── maps/           # Individual map HTML files
├── site_src/           # Source files for the website
│   └── index.html
├── .github/workflows/  # GitHub Actions workflow for auto‑deployment
│   └── deploy.yml
├── requirements.txt    # Python dependencies
├── .gitignore
└── README.md (this file)
```

## Quick start

1. **Install dependencies**:

   ```bash
   cd election_site
   pip install -r requirements.txt
   ```

2. **Scrape vote data**.  The `scrape_votes.py` script tries to
   download the latest TBS election page.  If that fails it falls
   back to the saved HTML in `data/tbs_election_2026.html`.

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

   This will create three CSV files in the `results/` directory:

   * **seat_results.csv** – one row per constituency with total
     votes and vote shares for each coalition.
   * **party_totals.csv** – national vote totals per party.
   * **party_by_seat.csv** – vote totals per party per seat.

3. **Build the maps**.  Use the `build_map.py` script to merge
   the seat results with the boundary GeoJSON and generate the
   interactive maps.  Each coalition defined in
   `config/coalitions.json` will produce its own HTML file.

   ```bash
   python scripts/build_map.py \
     --config config/coalitions.json \
     --results_csv results/seat_results.csv \
     --geojson data/constituencies.geojson \
     --output_dir site/maps
   ```

   If you update map styling or tooltip logic in `scripts/build_map.py`,
   you must re-run this command to regenerate the HTML files in
   `site/maps`.

4. **Preview the site locally**.  Launch the simple HTTP server:

   ```bash
   python scripts/serve.py --dir site --port 8000
   ```

   Then open [http://localhost:8000](http://localhost:8000) in
   your browser.  You can select different statistics from the
   dropdown to update the map.

5. **Deploy to GitHub Pages**.  This repository includes a
   GitHub Actions workflow that automatically scrapes the latest
   data, regenerates the maps and publishes the `site/` directory
   whenever you push changes to the `main` branch.  Simply push
   this project to a new GitHub repository and enable GitHub Pages
   (Deployment branch set to “GitHub Actions”).

## Customising coalitions

The coalition definitions live in `config/coalitions.json`.  Each
entry contains a unique key, a human‑readable display name, a list
of keywords used to match candidate party names, and a colour
gradient for the map.  You can edit this file to add new
alliances or tweak the colours.  The keywords are case‑insensitive
and can match substrings of the party name.  If you find that
additional parties (e.g. National Citizen Party, Liberal
Democratic Party) are missing from the alliances, simply append
their names (or abbreviations) to the appropriate ``keywords`` list.

## Data sources and acknowledgements

* **Election results** – scraped from
  *The Business Standard*’s election portal: <https://www.tbsnews.net/election-2026>.
  The portal embeds a JSON object containing vote counts for each
  candidate and constituency.  This project extracts that JSON
  directly from the page’s source code.
* **Constituency boundaries** – derived from the **GeoReferenced
  Electoral Districts** (GRED) dataset for Bangladesh’s 2008
  constituency boundaries.  The GRED codebook notes that the
  boundaries were georeferenced from a 2018 *Dhaka Tribune* map and
  manually corrected for several seats【672971089959022†L667-L688】.
* **Boundary source context** – the BBC Bangla election map
  (<https://www.bbc.com/bengali/resources/idt-12e6dcd9-2189-4c28-aafb-b106e6d01189>)
  indicates its boundaries are based on GRED, which this project uses.
* **Coalition membership** – based on contemporary reporting from
  multiple news sources and official party announcements.
* **Implementation and analysis** – created by S M A Nahian
  (<https://smanahian.com>) with tooling support from ChatGPT agent
  and GitHub Copilot.

## Credits

* **Project author** – S M A Nahian (<https://smanahian.com>).
* **Vote data** – The Business Standard election portal.
* **Boundary context** – BBC Bangla election map (based on GRED).
* **Tooling support** – ChatGPT agent and GitHub Copilot.

## License

This project is released under the MIT License.  Please see
`LICENSE` for details.  The GRED boundary data is © their
respective authors and distributed for non‑commercial use; see
`data/README` for further information. Data sources and attribution are
listed above; S M A Nahian (<https://smanahian.com>) compiled the
visualization with tooling support from ChatGPT agent and GitHub Copilot.