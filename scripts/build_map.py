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
import re
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


def normalize_seat_name(name: str) -> str:
    """Normalize seat names to a common form for matching."""
    if not name:
        return ''
    norm = str(name).strip().lower()
    norm = norm.replace('chattogram', 'chittagong')
    norm = norm.replace('barishal', 'barisal')
    norm = norm.replace('chapai nawabganj', 'chapai nababganj')
    norm = norm.replace('jhalakathi', 'jhalokathi')
    norm = norm.replace('moulvibazar', 'maulvibazar')
    norm = norm.replace('netrokona', 'netrakona')
    norm = norm.replace('khagrachhari', 'khagrachari')
    if norm.startswith('parbatya '):
        norm = norm.replace('parbatya ', '', 1)
        if '-' not in norm:
            norm = f"{norm}-1"
    norm = re.sub(r"[^a-z0-9\- ]", '', norm)
    norm = re.sub(r"\s+", ' ', norm)
    return norm


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

    # Build dictionary of seat name to ratio and additional info
    ratio_col = f"{coalition_code}_ratio"
    votes_col = f"{coalition_code}_votes"
    seat_data = {}
    for _, row in results_df.iterrows():
        seat_name = str(row['seat_name'])
        seat_key = normalize_seat_name(seat_name)
        top_three_candidates = row.get('top_three_candidates')
        if pd.isna(top_three_candidates):
            top_three_candidates = ''
        top_three_parties = row.get('top_three')
        if pd.isna(top_three_parties):
            top_three_parties = ''
        if not seat_key:
            continue
        seat_data[seat_key] = {
            'ratio': row[ratio_col] if ratio_col in row else 0.0,
            'votes': row[votes_col] if votes_col in row else 0,
            'total_votes': row['total_votes'],
            'seat_name': row['seat_name'],
            'top_three': top_three_candidates or top_three_parties or '',
        }

    for feature in geojson.get('features', []):
        seat_name = str(feature.get('properties', {}).get('cst_n', '')).strip()
        seat_key = normalize_seat_name(seat_name)
        if not seat_key:
            continue
        feature['properties']['seat_key'] = seat_key
        data = seat_data.get(seat_key)
        if data:
            feature['properties']['ratio'] = data['ratio']
            feature['properties']['top_three'] = data['top_three']
            feature['properties']['seat_name'] = data['seat_name']
        else:
            feature['properties']['ratio'] = 0.0
            feature['properties']['top_three'] = ''

    def style_function(feature):
        """Return style dict for each polygon based on the coalition ratio.

        The shapefile stores the seat number in the ``cst`` property
        (not ``cst_n``).  We convert it to an integer and look up the
        ratio for that seat.  Seats with no data are coloured
        according to the lowest value in the gradient.
        """
        # Use normalized seat name to index seat_data
        seat_key = feature['properties'].get('seat_key')
        data = seat_data.get(seat_key, None)
        ratio = data['ratio'] if data else 0.0
        color = '#000000' if ratio <= 0 else interpolate_color(start_color, end_color, ratio)
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
        seat_key = feature['properties'].get('seat_key')
        data = seat_data.get(seat_key, None)
        if not data:
            return "No data"
        top_three = data.get('top_three')
        top_items = [item.strip() for item in top_three.split(',')] if top_three else []
        if top_items:
            items_html = ''.join(f"<li>{item}</li>" for item in top_items)
            body_html = f"<ol class=\"tooltip-list\">{items_html}</ol>"
        else:
            body_html = "<div class=\"tooltip-empty\">No candidate data</div>"
        return (
            f"<div class=\"tooltip-title\">{data['seat_name']}</div>"
            f"<div class=\"tooltip-subtitle\">Top three candidates</div>"
            f"{body_html}"
        )

    geo_json = GeoJson(
        geojson,
        name=coalition_meta['display_name'],
        style_function=style_function,
        tooltip=GeoJsonTooltip(fields=[], aliases=[], labels=False, sticky=False, parse_html=True,
                               toLocaleString=True, script=False, localize=True, style=""),
    )
    # We use a custom on_hover script to show dynamic tooltips because
    # Folium's built-in tooltip cannot be parameterised per feature easily
    # after creation. Instead, we attach a piece of JavaScript to the
    # GeoJson layer that listens for mouse events.
    # Build JavaScript mapping of seat numbers to tooltip HTML
    # Build a lookup of seat number (cst) to tooltip HTML
    tooltip_map = {}
    for f in geojson['features']:
        seat_key = f['properties'].get('seat_key')
        if not seat_key:
            continue
        tooltip_map[seat_key] = tooltip_function(f)

    tooltip_json = json.dumps(tooltip_map)
    # Add the layer to the map
    geo_json.add_to(m)
    # Add legend
    legend_html = Template('''
    <div style="position: fixed; bottom: 24px; left: 24px; z-index: 1000; background-color: white; padding: 10px 12px; border: 1px solid #ccc; font-size: 13px; max-width: 260px;">
        <div style="font-weight: 600; line-height: 1.25; margin-bottom: 6px;">{{ title }}</div>
        <div style="margin: 2px 0 8px 0; display: flex; gap: 6px; align-items: center;">
            <span style="display: inline-block; width: 12px; height: 12px; background: #000000; border: 1px solid #222;"></span>
            <span>No nomination (0%)</span>
        </div>
        <svg width="200" height="10" aria-hidden="true">
            <defs>
                <linearGradient id="grad" x1="0" x2="1" y1="0" y2="0">
                    <stop id="legendStart" offset="0%" stop-color="{{ start_color }}" />
                    <stop id="legendEnd" offset="100%" stop-color="{{ end_color }}" />
                </linearGradient>
            </defs>
            <rect width="200" height="10" fill="url(#grad)" />
        </svg>
        <div style="display: flex; justify-content: space-between; width: 200px; margin-top: 2px;">
            <span>0%+</span><span>100%</span>
        </div>
    </div>
    ''').render(title=coalition_meta['display_name'] + ' vote share', start_color=start_color, end_color=end_color)
    m.get_root().html.add_child(folium.Element(legend_html))
    # Attach custom JS for tooltips
    tooltip_script = Template('''
    <script>
    const tooltipData = {{ tooltip_json | safe }};
        const paletteMap = {
            default: ['{{ start_color }}', '{{ end_color }}'],
            yellow_blue: ['#FFF7BC', '#2C7FB8'],
            green_red: ['#4CAF50', '#B71C1C'],
            orange_purple: ['#FDB863', '#5E3C99'],
            teal_orange: ['#2A9D8F', '#E76F51'],
            gray_red: ['#E0E0E0', '#B71C1C']
        };

        function hexToRgb(hex) {
            const clean = hex.replace('#', '');
            return [
                parseInt(clean.slice(0, 2), 16),
                parseInt(clean.slice(2, 4), 16),
                parseInt(clean.slice(4, 6), 16)
            ];
        }

        function interpolateColor(start, end, t) {
            const clamped = Math.max(0, Math.min(1, t));
            const [sr, sg, sb] = hexToRgb(start);
            const [er, eg, eb] = hexToRgb(end);
            const r = Math.round(sr + (er - sr) * clamped);
            const g = Math.round(sg + (eg - sg) * clamped);
            const b = Math.round(sb + (eb - sb) * clamped);
            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        }

        function getPaletteName() {
            const params = new URLSearchParams(window.location.search);
            return params.get('palette') || 'default';
        }

                function applyPalette(paletteName) {
                        const palette = paletteMap[paletteName] || paletteMap.default;
                        const start = palette[0];
                        const end = palette[1];
                        const layer = {{ layer_name }};
                        layer.eachLayer(function (leafletLayer) {
                                const ratio = leafletLayer.feature?.properties?.ratio ?? 0;
                        const scaled = ratio <= 0 ? 0 : scaleRatio(ratio);
                        const fillColor = ratio <= 0 ? '#000000' : interpolateColor(start, end, scaled);
                                leafletLayer.setStyle({ fillColor });
                        });
                        const startStop = document.getElementById('legendStart');
                        const endStop = document.getElementById('legendEnd');
                        if (startStop) startStop.setAttribute('stop-color', start);
                        if (endStop) endStop.setAttribute('stop-color', end);
                }

                function scaleRatio(ratio) {
                    const clamped = Math.max(0, Math.min(1, ratio));
                    const k = 8;
                    const sigmoid = (x) => 1 / (1 + Math.exp(-k * (x - 0.5)));
                    const lo = sigmoid(0);
                    const hi = sigmoid(1);
                    return (sigmoid(clamped) - lo) / (hi - lo);
                }

        function showTooltip(e) {
                const seat = e.target.feature.properties.seat_key.toString();
            const tooltip = tooltipData[seat] || '';
            const div = document.getElementById('hoverTooltip');
            if (div) {
                div.innerHTML = tooltip;
                div.style.display = 'block';
                div.style.left = (e.originalEvent.clientX + 15) + 'px';
                div.style.top = (e.originalEvent.clientY + 15) + 'px';
            }
            e.target.setStyle({ weight: 2, color: 'black' });
        }
        function hideTooltip(e) {
            const div = document.getElementById('hoverTooltip');
            if (div) {
                div.style.display = 'none';
            }
            e.target.setStyle({ weight: 0.5, color: 'black' });
        }
                window.addEventListener('load', function () {
                        var geoJsonLayer = {{ layer_name }};
                        geoJsonLayer.eachLayer(function (layer) {
                                layer.on({
                                        mouseover: showTooltip,
                                        mouseout: hideTooltip
                                });
                        });
                        applyPalette(getPaletteName());
                });
    </script>
            <div id="hoverTooltip" style="position: fixed; display: none; pointer-events: none; z-index: 1001; background-color: rgba(255,255,255,0.95); padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 12px; max-width: 260px; box-shadow: 0 2px 10px rgba(0,0,0,0.12);">
              <style>
            #hoverTooltip .tooltip-title { font-weight: 700; margin-bottom: 2px; }
            #hoverTooltip .tooltip-subtitle { color: #555; margin-bottom: 4px; }
            #hoverTooltip .tooltip-list { margin: 0; padding-left: 18px; }
            #hoverTooltip .tooltip-list li { margin: 0 0 2px 0; }
            #hoverTooltip .tooltip-empty { color: #666; font-style: italic; }
              </style>
            </div>
        ''').render(tooltip_json=tooltip_json, layer_name=geo_json.get_name())
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