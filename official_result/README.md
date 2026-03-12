# Election Commission Official Results (District-Level Aggregate)

This README documents the district-level columns in `ec_district_wide.csv`.

Source: District aggregate built from official_result/ec_constituency_wide.csv.

## Files

- `ec_district_wide.csv`: District-level dataset.
- `district_columns.py`: Importable column description dict and ordered key list.

## How to regenerate

```bash
python scripts/build_ec_wide.py
python scripts/build_ec_district_wide.py
python scripts/generate_district_metadata.py
```

## Columns

| Column | Description |
|--------|-------------|
| `district` | Standardized English district name derived from the seat names. |
| `district_bn` | Bangla district name from the Election Commission source data. |
| `seat_count` | Number of parliamentary constituencies in the district. |
| `total_voters` | Total registered voters across all constituencies in the district. |
| `total_votes_cast` | Total ballots cast across all constituencies in the district. |
| `valid_votes` | Total valid votes across all constituencies in the district. |
| `rejected_votes` | Total rejected ballots across all constituencies in the district. |
| `absent_voters` | Registered voters who did not cast a ballot. |
| `turnout_pct` | Votes cast as a share of total registered voters. |
| `rejection_pct` | Rejected ballots as a share of all ballots cast. |
| `absence_pct` | Absent voters as a share of total registered voters. |
| `total_centers` | Total polling centers across the district. |
| `total_candidates` | Total candidate entries across all district constituencies. |
| `avg_voters_per_center` | Average registered voters per polling center. |
| `avg_candidates_per_seat` | Average number of candidates per constituency in the district. |
| `safe_seats` | Number of constituencies in the district classified as safe. |
| `competitive_seats` | Number of constituencies in the district classified as competitive. |
| `marginal_seats` | Number of constituencies in the district classified as marginal. |
| `very_close_seats` | Number of constituencies in the district classified as very close. |
| `bnp_plus_votes` | Total valid votes for the BNP-led alliance bloc. |
| `bnp_plus_pct` | BNP-led alliance votes as a share of district valid votes. |
| `eleven_parties_votes` | Total valid votes for the eleven-party bloc. |
| `eleven_parties_pct` | Eleven-party bloc votes as a share of district valid votes. |
| `duf_votes` | Total valid votes for DUF-aligned candidates. |
| `duf_pct` | DUF votes as a share of district valid votes. |
| `ndf_votes` | Total valid votes for NDF-aligned candidates. |
| `ndf_pct` | NDF votes as a share of district valid votes. |
| `greater_sunni_votes` | Total valid votes for Greater Sunni-aligned candidates. |
| `greater_sunni_pct` | Greater Sunni votes as a share of district valid votes. |
| `independent_votes` | Total valid votes for independent candidates. |
| `independent_pct` | Independent votes as a share of district valid votes. |
| `other_party_votes` | Total valid votes for parties outside the named blocs and top tracked parties. |
| `other_party_pct` | Other-party votes as a share of district valid votes. |
| `bnp_votes` | Total valid votes for Bangladesh Nationalist Party - BNP candidates. |
| `bnp_pct` | BNP votes as a share of district valid votes. |
| `jamaat_votes` | Total valid votes for Bangladesh Jamaat-e-Islami candidates. |
| `jamaat_pct` | Jamaat votes as a share of district valid votes. |
| `ncp_votes` | Total valid votes for Jatiyo Nagorik Party - NCP candidates. |
| `ncp_pct` | NCP votes as a share of district valid votes. |
| `leading_party` | Party with the highest aggregate vote total in the district. |
| `leading_party_votes` | Aggregate votes won by the district-level leading party. |
| `leading_party_pct` | Leading party votes as a share of district valid votes. |
| `runner_up_party` | Party with the second-highest aggregate vote total in the district. |
| `runner_up_votes` | Aggregate votes won by the district-level runner-up party. |
| `runner_up_pct` | Runner-up party votes as a share of district valid votes. |
| `vote_margin` | Vote difference between the district-level leading party and runner-up party. |
| `vote_margin_pct` | Vote margin as a share of district valid votes. |
| `most_winning_seats_party` | Party that won the most constituencies in the district. |
| `most_winning_seats_count` | Number of constituencies won by the district seat leader. |
| `bnp_won_seats` | Number of district constituencies won by BNP. |
| `jamaat_won_seats` | Number of district constituencies won by Jamaat. |
| `ncp_won_seats` | Number of district constituencies won by NCP. |
| `independent_won_seats` | Number of district constituencies won by independents. |
| `other_party_won_seats` | Number of district constituencies won by all other parties combined. |
| `effective_num_parties` | Laakso-Taagepera effective number of parties based on district vote shares. |

## Notes

- This README documents only the district-level aggregate file.
- The district aggregate is derived from constituency-level official results rather than scraped directly at district level.
