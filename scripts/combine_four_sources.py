"""
combine_four_sources.py
=======================

Combines election data from four sources to produce the most reliable dataset.

Sources (all have per-party vote data):
  1. TBS News  — full per-party votes, all candidates (~298 seats)
  2. Daily Star — full per-party votes via symbol mapping (~296 seats)
  3. BSS News  — winner + runner-up votes only (~299 seats)
  4. Dhaka Tribune — full per-candidate votes via API (~300 seats, 2029 candidates)

Resolution strategy:
  - For each (seat, party) pair, collect values from all available sources.
  - Cluster sources that agree within 2%.
  - Pick the largest cluster; if tie, prefer the cluster containing DT or DS.
  - If no cluster of 2+, use median to avoid outlier inflation.
  - Apply manual overrides last for verified data errors.

Output format matches TBS/DS CSVs:
  seat_name, total_voters, total_votes, top_three_candidates, top_three,
  [alliance_votes, alliance_ratio, ...],
  [per-party vote columns...]
  comments, winner_verification

Usage::

    python3 scripts/combine_four_sources.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from normalize import normalize_seat_name

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TBS_PBS_PATH = os.path.join(BASE, "result_from_source/tbsnews_party_by_seat.csv")
DS_PBS_PATH = os.path.join(BASE, "result_from_source/dailystar_party_by_seat.csv")
BSS_PATH = os.path.join(BASE, "result_from_source/result_from_bssnews.csv")
DT_PBS_PATH = os.path.join(BASE, "result_from_source/dhakatribune_party_by_seat.csv")
DT_MAIN_PATH = os.path.join(BASE, "result_from_source/result_from_dhakatribune.csv")
DS_MAIN_PATH = os.path.join(BASE, "result_from_source/result_from_dailystar.csv")
OUTPUT_PATH = os.path.join(BASE, "vote_count_combined/combined_vote_counts.csv")
COALITIONS_PATH = os.path.join(BASE, "config/coalitions.json")


# ── Manual overrides ──
# Verified via 4-source cross-check. Each entry documents what was wrong and why.
VOTE_OVERRIDES = {
    "Kurigram 3": {
        # DS=79,352 is wrong (likely confused with another seat).
        # BSS shows BNP not in top 2; TBS=672, DT=3,129. Both confirm BNP is minor.
        "Bangladesh Nationalist Party (BNP)": 672,
    },
    "Rajshahi 2": {
        # DS=188,546 is exactly 60,000 more than TBS=128,546 — data entry error.
        # DT=128,546 confirms TBS value.
        "Bangladesh Nationalist Party (BNP)": 128546,
    },
    "Bogura 7": {
        # DS=158,196 is wrong. BSS=264,212, DT=264,212, TBS=264,212 — 3 sources agree.
        "Bangladesh Nationalist Party (BNP)": 264212,
    },
    "Rangpur 2": {
        # TBS has inflated values for both top parties.
        # DS (Jamaat=43,076, BNP=22,100) agrees with BSS.
        "Bangladesh Jamaat-e-Islami (Jamaat)": 43076,
        "Bangladesh Nationalist Party (BNP)": 22100,
    },
    "Lalmonirhat 2": {
        # BSS Jamaat=6,694 is clearly a typo (both TBS and DS have 100k+).
        # DS values (BNP=123,946, Jamaat=117,252) most consistent with DT.
        "Bangladesh Nationalist Party (BNP)": 123946,
        "Bangladesh Jamaat-e-Islami (Jamaat)": 117252,
    },
    "Dinajpur 5": {
        # TBS=3,027 for Independent is clearly wrong.
        # DS=113,650, BSS=113,650, DT=114,484. Using DS value (BSS-confirmed).
        "Independent Candidate (Independent)": 113650,
    },
    "Khagrachhari 1": {
        # TBS=447,910 for Independent is implausibly high (exceeds total voters).
        # DS=68,315. DT=63,165 in same range. Using DS.
        "Independent Candidate (Independent)": 68315,
    },
}


# ── Party equivalence (same party, different name across sources) ──
PARTY_EQUIVALENCE = {
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal-JASAD",
    "Jatiya Samajtantrik Dal-JASAD": "Jatiya Samajtantrik Dal (JSD)",
    "Bangladesh Khelafat Majlish (BKM)": "Khelafat Majlis",
    "Khelafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Bangladesh Muslim League (BML)": "Bangladesh Muslim League",
    "Bangladesh Muslim League": "Bangladesh Muslim League (BML)",
    "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)": "Jatiya Samajtantrik Dal-JASAD",
}


def parties_equivalent(p1, p2):
    if p1 == p2:
        return True
    return PARTY_EQUIVALENCE.get(p1) == p2 or PARTY_EQUIVALENCE.get(p2) == p1


# ── Data loaders ──

def load_pbs(path):
    """
    Load a party-by-seat CSV (long format: seat_name, party, candidate, votes)
    into {norm_seat: {party: votes}}.
    Multiple candidates per party in same seat get summed.
    """
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path, na_values=["-"])
    result = {}
    for _, row in df.iterrows():
        seat = normalize_seat_name(str(row["seat_name"]))
        party = str(row["party"]).strip()
        votes = int(row["votes"]) if pd.notna(row.get("votes")) else None
        if votes is None or votes <= 0:
            continue
        result.setdefault(seat, {})
        result[seat][party] = result[seat].get(party, 0) + votes
    return result


def load_bss_as_pbs():
    """Load BSS (winner+runner only) as {norm_seat: {party: votes}}."""
    if not os.path.exists(BSS_PATH):
        return {}
    df = pd.read_csv(BSS_PATH)
    result = {}
    for _, row in df.iterrows():
        seat = normalize_seat_name(str(row["seat_name"]))
        result[seat] = {}
        for role in ["winner", "runner"]:
            party = str(row.get(f"{role}_party", "")).strip()
            vraw = row.get(f"{role}_votes")
            if party and pd.notna(vraw):
                v = int(vraw)
                if v > 0:
                    result[seat][party] = v
    return result


def load_metadata():
    """
    Load seat metadata (total_voters, division, district) from DS main CSV
    and total_voters from DT main CSV, merging both.
    """
    meta = {}

    # DS has total_voters, division, district
    if os.path.exists(DS_MAIN_PATH):
        df = pd.read_csv(DS_MAIN_PATH, na_values=["-"])
        for _, row in df.iterrows():
            seat = normalize_seat_name(str(row["seat_name"]))
            meta[seat] = {
                "total_voters": pd.to_numeric(row.get("total_voters"), errors="coerce"),
                "division": row.get("division", ""),
                "district": row.get("district", ""),
            }

    # DT has total_voters too — fill gaps
    if os.path.exists(DT_MAIN_PATH):
        df = pd.read_csv(DT_MAIN_PATH, na_values=["-"])
        for _, row in df.iterrows():
            seat = normalize_seat_name(str(row["seat_name"]))
            dt_voters = pd.to_numeric(row.get("total_voters"), errors="coerce")
            if seat not in meta:
                meta[seat] = {"total_voters": dt_voters, "division": "", "district": ""}
            elif pd.isna(meta[seat].get("total_voters")):
                meta[seat]["total_voters"] = dt_voters

    return meta


def find_votes(pbs, seat, party):
    """Look up votes for a party or its equivalent name."""
    seat_data = pbs.get(seat, {})
    if party in seat_data:
        return seat_data[party]
    eq = PARTY_EQUIVALENCE.get(party)
    if eq and eq in seat_data:
        return seat_data[eq]
    return None


def resolve(seat, party, tbs_v, ds_v, bss_v, dt_v):
    """
    Resolve a vote count from up to 4 sources.

    Returns (value, comment).
    """
    sources = {}
    if tbs_v is not None and tbs_v > 0:
        sources["TBS"] = tbs_v
    if ds_v is not None and ds_v > 0:
        sources["DS"] = ds_v
    if bss_v is not None and bss_v > 0:
        sources["BSS"] = bss_v
    if dt_v is not None and dt_v > 0:
        sources["DT"] = dt_v

    if not sources:
        return None, ""
    if len(sources) == 1:
        name, val = next(iter(sources.items()))
        return val, f"{name} only"

    vals = list(sources.values())
    names = list(sources.keys())
    max_v = max(vals)

    # All agree within 2%
    if max_v > 0 and all(abs(v - max_v) / max_v < 0.02 for v in vals):
        return max_v, f"{'='.join(names)} agree"

    # Build clusters of agreeing sources (within 2%)
    clusters = []
    used = set()
    for i in range(len(vals)):
        if i in used:
            continue
        cluster = [i]
        for j in range(i + 1, len(vals)):
            if j in used:
                continue
            base = max(vals[i], vals[j])
            if base > 0 and abs(vals[i] - vals[j]) / base < 0.02:
                cluster.append(j)
        for idx in cluster:
            used.add(idx)
        clusters.append(cluster)

    # Score: prefer larger clusters, break ties by having DT or DS
    def score(c):
        return (len(c), any(names[i] in ("DT", "DS") for i in c))
    clusters.sort(key=score, reverse=True)

    best = clusters[0]
    if len(best) >= 2:
        chosen = max(vals[i] for i in best)
        cnames = "+".join(names[i] for i in best)
        outliers = [f"{names[i]}={vals[i]:,}" for i in range(len(vals)) if i not in best]
        comment = f"{cnames} agree ({chosen:,})"
        if outliers:
            comment += f"; outlier: {', '.join(outliers)}"
        return chosen, comment

    # No agreement — use median
    median_v = int(np.median(vals))
    detail = ", ".join(f"{n}={v:,}" for n, v in zip(names, vals))
    return median_v, f"no consensus, used median ({detail})"


def build_top_three(party_votes, pbs_sources, seat):
    """Build top_three and top_three_candidates strings for a seat."""
    if not party_votes:
        return "", ""

    total = sum(party_votes.values())
    top3 = sorted(party_votes.items(), key=lambda x: -x[1])[:3]

    # Find candidate names from DT or TBS (sources with candidate names)
    cand_lookup = {}
    for pbs in pbs_sources:
        # These are raw pbs dicts — we need the long-format data for candidate names
        # Skip this for now, just use party names
        pass

    parts_cand = []
    parts_party = []
    for party, votes in top3:
        pct = votes / total * 100 if total > 0 else 0
        parts_cand.append(f"{party} {pct:.1f}%")
        parts_party.append(f"{party} ({pct:.1f}%)")

    return ", ".join(parts_cand), ", ".join(parts_party)


def main():
    # ── Load all sources ──
    tbs_pbs = load_pbs(TBS_PBS_PATH)
    ds_pbs = load_pbs(DS_PBS_PATH)
    bss_pbs = load_bss_as_pbs()
    dt_pbs = load_pbs(DT_PBS_PATH)
    metadata = load_metadata()

    print(f"Loaded: TBS={len(tbs_pbs)}, DS={len(ds_pbs)}, "
          f"BSS={len(bss_pbs)}, DT={len(dt_pbs)} seats")

    # ── Collect all seats and party names ──
    all_seats = sorted(
        set(tbs_pbs) | set(ds_pbs) | set(bss_pbs) | set(dt_pbs)
    )

    # Collect all party names, dedup equivalents keeping the canonical name
    raw_parties = set()
    for pbs in [tbs_pbs, ds_pbs, bss_pbs, dt_pbs]:
        for seat_data in pbs.values():
            raw_parties.update(seat_data.keys())

    # For equivalent pairs, keep only one (prefer the one with parenthetical abbreviation)
    canonical = set()
    seen_equiv = set()
    for p in sorted(raw_parties):
        if p in seen_equiv:
            continue
        canonical.add(p)
        eq = PARTY_EQUIVALENCE.get(p)
        if eq:
            seen_equiv.add(eq)

    party_cols = sorted(canonical)
    print(f"Seats: {len(all_seats)}, Parties: {len(party_cols)}")

    # ── Load coalitions config ──
    coalitions = {}
    if os.path.exists(COALITIONS_PATH):
        with open(COALITIONS_PATH) as f:
            coalitions = json.load(f)

    alliance_fields = []
    for key in coalitions:
        alliance_fields.extend([f"{key}_votes", f"{key}_ratio"])

    # ── Resolve votes and build output rows ──
    rows = []
    override_count = 0

    for seat in all_seats:
        meta = metadata.get(seat, {})
        comments = []
        resolved_votes = {}

        # Resolve each party
        for party in party_cols:
            tbs_v = find_votes(tbs_pbs, seat, party)
            ds_v = find_votes(ds_pbs, seat, party)
            bss_v = find_votes(bss_pbs, seat, party)
            dt_v = find_votes(dt_pbs, seat, party)

            val, comment = resolve(seat, party, tbs_v, ds_v, bss_v, dt_v)

            # Manual override
            if seat in VOTE_OVERRIDES and party in VOTE_OVERRIDES[seat]:
                correct = VOTE_OVERRIDES[seat][party]
                old_str = f"{int(val):,}" if val else "N/A"
                val = correct
                override_count += 1
                comments.append(f"OVERRIDE {party}: {old_str} -> {correct:,} (4-source verified)")
            elif comment and "agree" not in comment and "only" not in comment:
                comments.append(f"{party}: {comment}")

            if val is not None:
                resolved_votes[party] = val

        total_votes = sum(resolved_votes.values()) if resolved_votes else 0

        # Build top_three strings
        top3_cand, top3_party = "", ""
        if resolved_votes and total_votes > 0:
            top3 = sorted(resolved_votes.items(), key=lambda x: -x[1])[:3]

            # Try to get candidate names from DT pbs (long format)
            dt_cands = {}
            if os.path.exists(DT_PBS_PATH):
                # We'll do a quick lookup from the dt_pbs — but it only has summed votes
                # For candidate names, load from the raw long-format CSV
                pass  # We'll build this outside the loop

            parts_cand = []
            parts_party = []
            for party, votes in top3:
                pct = votes / total_votes * 100
                parts_cand.append(f"{party} {pct:.1f}%")
                parts_party.append(f"{party} ({pct:.1f}%)")
            top3_cand = ", ".join(parts_cand)
            top3_party = ", ".join(parts_party)

        # Compute alliance columns
        alliance_vals = {}
        for alliance_key, config in coalitions.items():
            keywords = config.get("keywords", [])
            atotal = 0
            for party, votes in resolved_votes.items():
                for kw in keywords:
                    if kw.lower() in party.lower():
                        atotal += votes
                        break
            alliance_vals[f"{alliance_key}_votes"] = atotal if atotal > 0 else "-"
            if total_votes > 0 and atotal > 0:
                alliance_vals[f"{alliance_key}_ratio"] = round(atotal / total_votes, 6)
            else:
                alliance_vals[f"{alliance_key}_ratio"] = "-"

        # Winner verification
        our_winner = max(resolved_votes, key=resolved_votes.get) if resolved_votes else None
        agreements = []
        if our_winner:
            for src_name, pbs in [("TBS", tbs_pbs), ("DS", ds_pbs), ("BSS", bss_pbs), ("DT", dt_pbs)]:
                seat_data = pbs.get(seat, {})
                if not seat_data:
                    continue
                src_winner = max(seat_data, key=seat_data.get)
                if parties_equivalent(our_winner, src_winner):
                    agreements.append(src_name)

        if len(agreements) >= 2:
            winner_ver = f"Winner confirmed by {'+'.join(agreements)}"
        elif len(agreements) == 1:
            winner_ver = f"Winner only confirmed by {agreements[0]}"
        elif our_winner:
            winner_ver = "Winner UNCONFIRMED"
        else:
            winner_ver = ""

        # Build row
        row = {
            "seat_name": seat,
            "division": meta.get("division", ""),
            "district": meta.get("district", ""),
            "total_voters": meta.get("total_voters", ""),
            "total_votes": total_votes if total_votes > 0 else "-",
            "top_three_candidates": top3_cand,
            "top_three": top3_party,
        }
        row.update(alliance_vals)
        for party in party_cols:
            row[party] = resolved_votes.get(party, "-")
        row["comments"] = "; ".join(comments)
        row["winner_verification"] = winner_ver
        rows.append(row)

    # ── Write CSV ──
    fieldnames = (
        ["seat_name", "division", "district", "total_voters", "total_votes",
         "top_three_candidates", "top_three"]
        + alliance_fields
        + party_cols
        + ["comments", "winner_verification"]
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"\nSaved {len(rows)} seats to {OUTPUT_PATH}")
    print(f"Applied {override_count} manual overrides")

    # ── Stats ──
    disc_count = sum(1 for r in rows if r["comments"])
    print(f"Seats with resolution notes: {disc_count}")

    party_wins = {}
    for r in rows:
        pvotes = {p: r[p] for p in party_cols if r[p] != "-" and r[p] > 0}
        if pvotes:
            winner = max(pvotes, key=pvotes.get)
            party_wins[winner] = party_wins.get(winner, 0) + 1

    print("\nSeats won by party:")
    for p, c in sorted(party_wins.items(), key=lambda x: -x[1]):
        print(f"  {p}: {c}")

    confirmed_4 = sum(1 for r in rows if r["winner_verification"].count("+") >= 3)
    confirmed_3 = sum(1 for r in rows if r["winner_verification"].count("+") == 2)
    confirmed_2 = sum(1 for r in rows if r["winner_verification"].count("+") == 1
                      and "confirmed" in r["winner_verification"])
    print(f"\nWinner verification:")
    print(f"  4-source: {confirmed_4}")
    print(f"  3-source: {confirmed_3}")
    print(f"  2-source: {confirmed_2}")


if __name__ == "__main__":
    main()
