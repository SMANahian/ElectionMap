#!/usr/bin/env python3
"""Build the district view and neighbour data that the website loads.

Reads data/constituencies.geojson and site/data/seat_data.json (so run it
after build_site_data.py) and writes to site/data/:

  neighbors.json      seat -> seats that border it
  districts.geojson   one shape per district (union of its constituencies)
  district_data.json  per-district stats (mean of the seat ratios) and totals
"""

import collections
import json
import os
import statistics
import sys

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.strtree import STRtree

# Add parent dir so we can import normalize
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from normalize import normalize_seat_name

# Seats closer than this many degrees (~110 m) count as neighbours, so seats
# split only by a thin gap in the boundary file (e.g. a river) still match.
NEIGHBOR_TOLERANCE = 0.001

# Neighbouring constituencies don't always touch exactly in the boundary
# file, which leaves hairline gaps inside a merged district. Growing each
# shape by this much (~5 m) before merging and shrinking it back closes them.
DISTRICT_GAP = 5e-5

# Stats the district view can show (the stat buttons in site_src/index.html)
DISTRICT_STATS = [
    "bnp", "jamaat", "eleven_party_alliance", "bnp_alliance",
    "bnp_vs_eleven_party_alliance", "turnout", "victory_margin",
]


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(base, "site", "data")

    with open(os.path.join(base, "data", "constituencies.geojson"), encoding="utf-8") as f:
        features = json.load(f)["features"]
    with open(os.path.join(out_dir, "seat_data.json"), encoding="utf-8") as f:
        seats = json.load(f)

    names = [ft["properties"].get("cst_n") for ft in features]
    if not all(names):
        sys.exit("constituencies.geojson has features without a seat name (cst_n)")
    keys = [normalize_seat_name(n) for n in names]
    geoms = [shape(ft["geometry"]) for ft in features]
    dupes = sorted(k for k, n in collections.Counter(keys).items() if n > 1)
    if dupes:
        sys.exit(f"Duplicate seat names in constituencies.geojson: {dupes}")
    unmatched = sorted(set(seats) - set(keys))
    if unmatched:
        sys.exit(f"Seats with no shape in constituencies.geojson: {unmatched}")
    # Shapes are grouped by seat name and stats by each seat's district, so
    # the two have to agree
    misfiled = sorted(k for k, s in seats.items() if s["district"] != k.rsplit(" ", 1)[0])
    if misfiled:
        sys.exit(f"Seats whose district doesn't match their name: {misfiled}")

    # Neighbours, listed in boundary-file order
    tree = STRtree(geoms)
    neighbors = {}
    for i, g in enumerate(geoms):
        near = sorted(int(j) for j in tree.query(g.buffer(NEIGHBOR_TOLERANCE)))
        neighbors[keys[i]] = [keys[j] for j in near
                              if j != i and g.distance(geoms[j]) <= NEIGHBOR_TOLERANCE]

    # District shapes: merge each district's constituencies ("Dhaka 4" -> "Dhaka")
    shapes_by_district = collections.defaultdict(list)
    for k, g in zip(keys, geoms):
        shapes_by_district[k.rsplit(" ", 1)[0]].append(g)

    def merge(parts):
        grown = [g.buffer(DISTRICT_GAP, join_style="mitre") for g in parts]
        return unary_union(grown).buffer(-DISTRICT_GAP, join_style="mitre")

    districts = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"district": d},
         "geometry": mapping(merge(shapes_by_district[d]))}
        for d in sorted(shapes_by_district)
    ]}

    # District stats from the seats that have results
    seats_by_district = collections.defaultdict(list)
    for s in seats.values():
        seats_by_district[s["district"]].append(s)

    district_data = {}
    for d in sorted(seats_by_district):
        ds = seats_by_district[d]
        wins = collections.Counter(s["winner"] for s in ds)
        district_data[d] = {
            "district": d,
            "division": ds[0]["division"],
            "seat_count": len(ds),
            "stats": {k: statistics.fmean(s["stats"][k] for s in ds) for k in DISTRICT_STATS},
            "total_votes": sum(s["total_votes"] for s in ds),
            "total_voters": sum(s["total_voters"] for s in ds),
            "top_winner": wins.most_common(1)[0][0],
            "winner_counts": dict(wins),
        }

    for name, obj in (("neighbors.json", neighbors),
                      ("districts.geojson", districts),
                      ("district_data.json", district_data)):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)

    print(f"Wrote {len(neighbors)} neighbour lists, {len(districts['features'])} district "
          f"shapes and {len(district_data)} district summaries to {out_dir}")


if __name__ == "__main__":
    main()
