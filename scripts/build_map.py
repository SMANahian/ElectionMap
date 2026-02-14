"""
build_map.py
============

Generate interactive choropleth maps for Bangladeshi parliamentary
constituencies using pre‑computed election statistics.  This script
reads a constituency‑level results CSV (produced by
``scrape_votes.py``), a GeoJSON file describing constituency
boundaries, and a coalition configuration file.  For each coalition
specified in the config it creates an HTML map where constituencies
are coloured according to the ratio of votes won by that coalition
relative to the total votes cast in the constituency.

Each output map is saved into the ``output_dir`` and named
``<coalition_code>.html``.  The maps include hover tooltips
showing the constituency name, total votes and coalition vote share.

Example usage::

    python3 scripts/build_map.py \
        --config config/coalitions.json \
        --results_csv results/seat_results.csv \
        --geojson data/constituencies.geojson \
        --output_dir site/maps

This script depends on ``pandas`` and ``folium`` but does not
require geopandas; it uses ``json`` to parse the GeoJSON file.
"""

import argparse
import json
import os
from typing import Dict, Any, Tuple

import pandas as pd
import folium
from folium.features import GeoJson, GeoJsonTooltip
from jinja2 import Template


def load_coalitions(config_path: str) -> Dict[str, Dict[str, Any]]:
    """Load coalition metadata from a JSON config file.

    Returns a dictionary mapping coalition codes to metadata, including
    the display name and colour scale used for the map.
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        coalitions = json.load(f)
    # Ensure each coalition has colour scale defined
    for code, meta in coalitions.items():
        if 'color_scale' not in meta or len(meta['color_scale']) != 2:
            # Fallback to a default blue gradient
            meta['color_scale'] = ["#f0f9e8", "#0868ac"]
    return coalitions


def interpolate_color(hex_start: str, hex_end: str, t: float) -> str:
    """Linearly interpolate between two hex colours.

    Parameters
    ----------
    hex_start : str
        The start colour (e.g. ``"#FFFFCC"``).
    hex_end : str
        The end colour (e.g. ``"#0060C9"``).
    t : float
        A value between 0 and 1 indicating the interpolation
        fraction.  Values outside this range will be clamped.

    Returns
    -------
    str
        An interpolated colour in ``#RRGGBB`` format.
    """
    t = max(0.0, min(1.0, t))
    s = hex_start.lstrip('#')
    e = hex_end.lstrip('#')
    sr, sg, sb = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    er, eg, eb = int(e[0:2], 16), int(e[2:4], 16), int(e[4:6], 16)
    r = int(sr + (er - sr) * t)
    g = int(sg + (eg - sg) * t)
    b = int(sb + (eb - sb) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def build_map(geojson: Dict[str, Any], results_df: pd.DataFrame, coalition_code: str, coalition_meta: Dict[str, Any], output_path: str) -> None:
    """Create a Folium map for a single coalition and save it to HTML.

    Parameters
    ----------
    geojson : dict
        Parsed GeoJSON of constituency boundaries.
    results_df : pandas.DataFrame
        Seat‑level results.  Must contain columns ``seat_number`` and
        ``<coalition_code>_ratio``.
    coalition_code : str
        Code identifying the coalition (e.g. ``"bnp"``).
    coalition_meta : dict
        Metadata for the coalition, including ``display_name`` and
        ``color_scale``.
    output_path : str
        Destination HTML file.
    """
    start_color, end_color = coalition_meta['color_scale']
    # Create base map centred roughly on Bangladesh
    m = folium.Map(location=[23.7, 90.35], zoom_start=7, tiles='cartodbpositron')

    # Build dictionary of seat number to ratio and additional info
    ratio_col = f"{coalition_code}_ratio"
    votes_col = f"{coalition_code}_votes"
    seat_data = {}
    for _, row in results_df.iterrows():
        seat_num = row['seat_number']
        seat_data[str(int(seat_num))] = {
            'ratio': row[ratio_col] if ratio_col in row else 0.0,
            'votes': row[votes_col] if votes_col in row else 0,
            'total_votes': row['total_votes'],
            'seat_name': row['seat_name'],
        }

    def style_function(feature):
        """Return style dict for each polygon based on the coalition ratio.

        The shapefile stores the seat number in the ``cst`` property
        (not ``cst_n``).  We convert it to an integer and look up the
        ratio for that seat.  Seats with no data are coloured
        according to the lowest value in the gradient.
        """
        # Use 'cst' property (numeric seat number) to index seat_data
        seat_number = feature['properties'].get('cst')
        try:
            seat_key = str(int(seat_number))
        except (TypeError, ValueError):
            seat_key = None
        data = seat_data.get(seat_key, None)
        ratio = data['ratio'] if data else 0.0
        color = interpolate_color(start_color, end_color, ratio)
        return {
            'fillOpacity': 0.7,
            'weight': 0.5,
            'color': 'black',
            'fillColor': color,
        }

    def tooltip_function(feature):
        """Return HTML for tooltip for a constituency.

        The tooltip includes the seat name, total votes and coalition
        vote share.  It uses the numeric seat number stored in
        ``cst`` to look up the corresponding row in ``seat_data``.
        """
        seat_number = feature['properties'].get('cst')
        try:
            seat_key = str(int(seat_number))
        except (TypeError, ValueError):
            seat_key = None
        data = seat_data.get(seat_key, None)
        if data:
            ratio_percent = f"{data['ratio'] * 100:.1f}%"
            return (
                f"{data['seat_name']}<br>"
                f"Total votes: {data['total_votes']:,}<br>"
                f"{coalition_meta['display_name']} votes: {data['votes']:,} ({ratio_percent})"
            )
        else:
            return "No data"

    geo_json = GeoJson(
        geojson,
        name=coalition_meta['display_name'],
        style_function=style_function,
        tooltip=GeoJsonTooltip(fields=[], aliases=[], labels=False, sticky=False, parse_html=True,
                               toLocaleString=True, script=False, localize=True, style=""),
        highlight_function=lambda feat: {'weight': 2, 'color': 'black'},
    )
    # We use a custom on_hover script to show dynamic tooltips because
    # Folium's built‑in tooltip cannot be parameterised per feature easily
    # after creation.  Instead, we attach a piece of JavaScript to the
    # GeoJson layer that listens for mouse events.
    # Build JavaScript mapping of seat numbers to tooltip HTML
    # Build a lookup of seat number (cst) to tooltip HTML
    tooltip_map = {}
    for f in geojson['features']:
        seat_number = f['properties'].get('cst')
        try:
            seat_key = str(int(seat_number))
        except (TypeError, ValueError):
            continue
        tooltip_map[seat_key] = tooltip_function(f)
    tooltip_json = json.dumps(tooltip_map)
    # Add the layer to the map
    geo_json.add_to(m)
    # Add legend
    legend_html = Template('''
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000; background-color: white; padding: 10px; border: 1px solid #ccc; font-size: 14px;">
      <b>{{ title }}</b><br>
      <svg width="150" height="10">
        <defs>
          <linearGradient id="grad" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stop-color="{{ start_color }}" />
            <stop offset="100%" stop-color="{{ end_color }}" />
          </linearGradient>
        </defs>
        <rect width="150" height="10" fill="url(#grad)" />
      </svg><br>
      <span style="float: left;">0%</span><span style="float: right;">100%</span>
      <div style="clear: both;"></div>
    </div>
    ''').render(title=coalition_meta['display_name'] + ' vote share', start_color=start_color, end_color=end_color)
    m.get_root().html.add_child(folium.Element(legend_html))
    # Attach custom JS for tooltips
    tooltip_script = Template('''
    <script>
    const tooltipData = {{ tooltip_json | safe }};
    function showTooltip(e) {
      const seat = e.target.feature.properties.cst_n.toString();
      const tooltip = tooltipData[seat] || '';
      const div = document.getElementById('hoverTooltip');
      if (div) {
        div.innerHTML = tooltip;
        div.style.display = 'block';
        div.style.left = (e.originalEvent.clientX + 15) + 'px';
        div.style.top = (e.originalEvent.clientY + 15) + 'px';
      }
    }
    function hideTooltip(e) {
      const div = document.getElementById('hoverTooltip');
      if (div) {
        div.style.display = 'none';
      }
    }
    var geoJsonLayer = {{ layer_name }};
    geoJsonLayer.eachLayer(function (layer) {
      layer.on({
        mouseover: showTooltip,
        mouseout: hideTooltip
      });
    });
    </script>
    <div id="hoverTooltip" style="position: fixed; display: none; pointer-events: none; z-index: 1001; background-color: rgba(255,255,255,0.9); padding: 5px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px;"></div>
    ''').render(tooltip_json=tooltip_json, layer_name='geo_json_{}'.format(id(geo_json)))
    m.get_root().html.add_child(folium.Element(tooltip_script))
    # Save map
    m.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate election maps coloured by coalition vote share.')
    parser.add_argument('--config', default='config/coalitions.json', help='Path to coalition config JSON.')
    parser.add_argument('--results_csv', default='results/seat_results.csv', help='CSV file of seat-level results.')
    parser.add_argument('--geojson', default='data/constituencies.geojson', help='GeoJSON file of constituency boundaries.')
    parser.add_argument('--output_dir', default='site/maps', help='Directory in which to write map HTML files.')
    args = parser.parse_args()

    # Load coalition definitions
    coalitions = load_coalitions(args.config)
    # Load seat results
    results_df = pd.read_csv(args.results_csv)
    # Load GeoJSON
    with open(args.geojson, 'r', encoding='utf-8') as f:
        geojson = json.load(f)
    # Ensure output directory exists
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir, exist_ok=True)
    # Build maps
    for code, meta in coalitions.items():
        if f'{code}_ratio' not in results_df.columns:
            # Skip coalitions that are not present
            continue
        output_path = os.path.join(args.output_dir, f'{code}.html')
        print(f'Creating map for {code} at {output_path} ...')
        build_map(geojson, results_df, code, meta, output_path)
    print('Map generation complete.')


if __name__ == '__main__':
    main()