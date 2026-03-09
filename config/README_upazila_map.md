# Upazila-to-Constituency Mapping

## Overview

`upazila_constituency_map.csv` maps Bangladesh upazilas to their parliamentary constituencies, cross-verified against multiple sources.

## Columns

| Column | Description |
|--------|-------------|
| `upazila` | Upazila name (cleaned, without "Upazila" suffix) |
| `district` | District name |
| `constituency` | Constituency name (e.g., "Panchagarh-1") |
| `constituency_number` | Seat number |
| `source` | Which sources confirmed this mapping (semicolon-separated) |

## Sources

1. **seat_results** - `results/seat_results.csv` election results (primary source, 298 constituencies)
2. **geocode** - [nuhil/bangladesh-geocode](https://github.com/nuhil/bangladesh-geocode) GitHub repository (494 canonical upazilas)
3. **pop_stats** - `humdata_pop_stats/pop_upazila.csv` HumData population statistics (527 upazilas including city corporation thanas)

## Known Limitations

- **City corporation wards**: Dhaka, Chattogram, Khulna, and other city corporations are divided by ward numbers in seat_results, not by upazila. These appear as numeric ward entries and are tagged as `city_corp_area`.
- **Partial upazilas**: Some constituencies share an upazila (marked "(partial)" in source data). Both constituencies list the upazila.
- **Spelling variants**: Some upazilas have alternate spellings across sources (e.g., Cumilla/Comilla, Laxmipur/Lakshmipur). The fuzzy matching handles most cases; remaining mismatches are in `upazila_mismatch_report.txt`.

## Regenerating

```bash
python3 config/build_upazila_constituency_map.py
```

Requires the geocode JSON files in `/tmp/` (downloaded by the script's first run). To re-download, fetch from:
- https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/upazilas/upazilas.json
- https://raw.githubusercontent.com/nuhil/bangladesh-geocode/master/districts/districts.json
