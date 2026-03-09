"""
verify_sources.py
=================

Cross-verifies election data between TBS News and Daily Star sources.

Compares ALL data:
1. Seat coverage — which seats are in each source
2. Seat-level results — total votes, coalition votes/ratios
3. Winner agreement — do both sources agree on the winning party
4. Exact vote counts — candidate-level vote comparison via party_by_seat
5. Party totals — national-level vote totals per party

Outputs:
- verification_seat_mismatches.csv — seat-level discrepancies
- verification_vote_mismatches.csv — candidate vote count differences
- verification_party_total_mismatches.csv — national party total differences
- verification_summary.csv — one-row summary of all checks

Usage::

    python3 scripts/verify_sources.py
"""

import argparse
import logging
import os
import re

import pandas as pd

from normalize import normalize_party, normalize_seat_name


# Mapping of Daily Star party names to TBS party names.
# Known alternative spellings between TBS and Daily Star
def normalize_candidate_name(name: str) -> str:
    """Normalize candidate name for fuzzy matching."""
    name = str(name).strip().lower()
    # Remove honorifics and common prefixes
    name = re.sub(r"^(mr\.?|ms\.?|md\.?|dr\.?|prof\.?|eng\.?|advocate|alhaj|maolana|sheikh)\s+", "", name)
    name = re.sub(r"\bmd\.?\b", "", name)
    # Remove punctuation and extra spaces
    name = re.sub(r"[.\-,'()]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def candidate_name_similarity(name1: str, name2: str) -> float:
    """Simple word-overlap similarity between two candidate names."""
    n1 = normalize_candidate_name(name1)
    n2 = normalize_candidate_name(name2)
    if n1 == n2:
        return 1.0
    words1 = set(n1.split())
    words2 = set(n2.split())
    if not words1 or not words2:
        return 0.0
    overlap = words1 & words2
    return len(overlap) / max(len(words1), len(words2))


def find_best_tbs_match(ds_candidate: str, tbs_matches: pd.DataFrame) -> pd.Series:
    """Given multiple TBS rows for the same party in a seat, pick the best candidate name match."""
    if len(tbs_matches) == 1:
        return tbs_matches.iloc[0]
    best_score = -1
    best_row = tbs_matches.iloc[0]
    for _, row in tbs_matches.iterrows():
        score = candidate_name_similarity(ds_candidate, row.get("candidate", ""))
        if score > best_score:
            best_score = score
            best_row = row
    return best_row


def compare_seat_results(tbs_path: str, ds_path: str, output_dir: str):
    """Compare seat-level results: total votes, coalition votes."""

    tbs = pd.read_csv(tbs_path, na_values=["-"])
    ds = pd.read_csv(ds_path, na_values=["-"])

    tbs["_norm"] = tbs["seat_name"].apply(normalize_seat_name)
    ds["_norm"] = ds["seat_name"].apply(normalize_seat_name)

    common = set(tbs["_norm"]) & set(ds["_norm"])
    tbs_idx = tbs.set_index("_norm")
    ds_idx = ds.set_index("_norm")

    logging.info(f"\n{'='*60}")
    logging.info("SEAT-LEVEL RESULT COMPARISON")
    logging.info(f"{'='*60}")
    logging.info(f"TBS seats: {len(tbs)}, DS seats: {len(ds)}, Common: {len(common)}")

    only_tbs = set(tbs["_norm"]) - set(ds["_norm"])
    only_ds = set(ds["_norm"]) - set(tbs["_norm"])
    if only_tbs:
        logging.info(f"Only in TBS ({len(only_tbs)}): {sorted(only_tbs)}")
    if only_ds:
        logging.info(f"Only in DS ({len(only_ds)}): {sorted(only_ds)}")

    # Coalition columns present in both
    coalition_cols = []
    for col in tbs.columns:
        if col.endswith("_votes") and col != "total_votes" and col in ds.columns:
            coalition_cols.append(col)

    mismatches = []

    for norm in sorted(common):
        t = tbs_idx.loc[norm]
        d = ds_idx.loc[norm]
        seat = t["seat_name"]

        # Total votes: DS is partial (top 2), so DS <= TBS expected
        t_total = t.get("total_votes")
        d_total = d.get("total_votes")
        if pd.notna(t_total) and pd.notna(d_total) and d_total > t_total:
            diff = int(d_total - t_total)
            diff_pct = (diff / float(t_total) * 100) if t_total > 0 else 100.0
            mismatches.append({
                "seat_name": seat,
                "field": "total_votes",
                "tbs_value": int(t_total),
                "ds_value": int(d_total),
                "diff": diff,
                "diff_pct": f"{diff_pct:.2f}%",
                "is_significant": diff_pct > 1.0,
                "issue": "DS partial total exceeds TBS full total",
            })

        # Coalition vote columns: DS partial <= TBS full
        for col in coalition_cols:
            tv = t.get(col)
            dv = d.get(col)
            if pd.notna(tv) and pd.notna(dv) and dv > tv:
                diff = int(dv - tv)
                diff_pct = (diff / float(tv) * 100) if tv > 0 else 100.0
                mismatches.append({
                    "seat_name": seat,
                    "field": col,
                    "tbs_value": int(tv),
                    "ds_value": int(dv),
                    "diff": diff,
                    "diff_pct": f"{diff_pct:.2f}%",
                    "is_significant": diff_pct > 1.0,
                    "issue": f"DS {col} exceeds TBS",
                })

    logging.info(f"Seat-level anomalies (DS exceeds TBS): {len(mismatches)}")
    if mismatches:
        for m in mismatches[:20]:
            logging.info(
                f"  {m['seat_name']} | {m['field']}: "
                f"TBS={m['tbs_value']:,} vs DS={m['ds_value']:,} (diff={m['diff']:+,})"
            )
        if len(mismatches) > 20:
            logging.info(f"  ... and {len(mismatches) - 20} more")

    out_path = os.path.join(output_dir, "verification_seat_mismatches.csv")
    if mismatches:
        pd.DataFrame(mismatches).to_csv(out_path, index=False)
        logging.info(f"Saved to {out_path}")
    else:
        logging.info("No seat-level anomalies found.")

    return mismatches, len(common), only_tbs, only_ds


def compare_party_totals(tbs_path: str, ds_path: str, output_dir: str):
    """Compare national party vote totals between sources."""

    tbs = pd.read_csv(tbs_path, na_values=["-"])
    ds = pd.read_csv(ds_path, na_values=["-"])

    logging.info(f"\n{'='*60}")
    logging.info("PARTY TOTALS COMPARISON")
    logging.info(f"{'='*60}")
    logging.info(f"TBS parties: {len(tbs)}, DS parties: {len(ds)}")

    # Map DS party names
    ds["_mapped"] = ds["party"].apply(normalize_party)

    # Merge on mapped party name
    merged = tbs.merge(ds, left_on="party", right_on="_mapped", how="outer",
                       suffixes=("_tbs", "_ds"))

    mismatches = []
    matched_count = 0

    for _, row in merged.iterrows():
        tbs_party = row.get("party_tbs") or row.get("party")
        ds_party = row.get("party_ds", "")
        tbs_votes = row.get("votes_tbs")
        ds_votes = row.get("votes_ds")

        if pd.notna(tbs_votes) and pd.notna(ds_votes):
            matched_count += 1
            # DS totals are partial (top 2 only), so DS <= TBS expected
            diff = int(ds_votes - tbs_votes)
            diff_pct = (abs(diff) / float(tbs_votes) * 100) if tbs_votes > 0 else 100.0
            mismatches.append({
                "party_tbs": tbs_party,
                "party_ds": ds_party,
                "tbs_votes": int(tbs_votes),
                "ds_votes": int(ds_votes),
                "diff": diff,
                "diff_pct": f"{diff_pct:.2f}%",
                "is_significant": diff > 0 and diff_pct > 1.0,
                "ds_pct_of_tbs": f"{ds_votes / tbs_votes * 100:.1f}%" if tbs_votes > 0 else "-",
                "issue": "DS exceeds TBS" if diff > 0 else "Expected (DS partial)",
            })
        elif pd.notna(tbs_votes):
            mismatches.append({
                "party_tbs": tbs_party,
                "party_ds": "-",
                "tbs_votes": int(tbs_votes),
                "ds_votes": "-",
                "diff": "-",
                "diff_pct": "-",
                "is_significant": True,
                "ds_pct_of_tbs": "-",
                "issue": "Only in TBS",
            })
        elif pd.notna(ds_votes):
            mismatches.append({
                "party_tbs": "-",
                "party_ds": ds_party,
                "tbs_votes": "-",
                "ds_votes": int(ds_votes),
                "diff": "-",
                "diff_pct": "-",
                "is_significant": True,
                "ds_pct_of_tbs": "-",
                "issue": "Only in DS (mapping needed?)",
            })

    # Show top parties comparison
    both = [m for m in mismatches if m["tbs_votes"] != "-" and m["ds_votes"] != "-"]
    both_sorted = sorted(both, key=lambda x: x["tbs_votes"], reverse=True)

    logging.info(f"\nTop parties comparison (TBS vs DS partial):")
    for m in both_sorted[:15]:
        logging.info(
            f"  {m['party_tbs']}: TBS={m['tbs_votes']:,} vs DS={m['ds_votes']:,} "
            f"({m['ds_pct_of_tbs']} of TBS, diff={m['diff']:+,})"
        )

    anomalies = [m for m in both if m["issue"] == "DS exceeds TBS"]
    if anomalies:
        logging.info(f"\nAnomalies (DS total > TBS total):")
        for m in anomalies:
            logging.info(
                f"  {m['party_tbs']}: TBS={m['tbs_votes']:,} vs DS={m['ds_votes']:,} "
                f"(diff={m['diff']:+,})"
            )

    only_tbs = [m for m in mismatches if m["issue"] == "Only in TBS"]
    only_ds = [m for m in mismatches if m["issue"] == "Only in DS (mapping needed?)"]
    if only_ds:
        logging.info(f"\nDS parties not found in TBS ({len(only_ds)}):")
        for m in only_ds:
            logging.info(f"  \"{m['party_ds']}\" ({m['ds_votes']:,} votes)")

    out_path = os.path.join(output_dir, "verification_party_total_mismatches.csv")
    pd.DataFrame(mismatches).to_csv(out_path, index=False)
    logging.info(f"Saved to {out_path}")

    return mismatches, matched_count


def compare_vote_counts(tbs_pbs_path: str, ds_pbs_path: str, output_dir: str):
    """Compare candidate-level vote counts via party_by_seat data."""

    tbs = pd.read_csv(tbs_pbs_path, na_values=["-"])
    ds = pd.read_csv(ds_pbs_path, na_values=["-"])

    logging.info(f"\n{'='*60}")
    logging.info("CANDIDATE VOTE COUNT COMPARISON")
    logging.info(f"{'='*60}")
    logging.info(f"TBS candidates: {len(tbs)}, DS candidates: {len(ds)}")

    tbs["_norm_seat"] = tbs["seat_name"].apply(normalize_seat_name)
    ds["_norm_seat"] = ds["seat_name"].apply(normalize_seat_name)
    ds["_party_mapped"] = ds["party"].apply(normalize_party)

    common_seats = set(tbs["_norm_seat"]) & set(ds["_norm_seat"])

    # Winner comparison
    tbs_winners = (
        tbs.loc[tbs.groupby("_norm_seat")["votes"].idxmax()]
        [["_norm_seat", "party", "votes", "candidate"]]
        .rename(columns={"party": "tbs_party", "votes": "tbs_votes", "candidate": "tbs_candidate"})
    )
    ds_known = ds[ds["votes"].notna()].copy()
    ds_winners = (
        ds_known.loc[ds_known.groupby("_norm_seat")["votes"].idxmax()]
        [["_norm_seat", "_party_mapped", "votes", "candidate"]]
        .rename(columns={"_party_mapped": "ds_party", "votes": "ds_votes", "candidate": "ds_candidate"})
    )
    winner_compare = tbs_winners.merge(ds_winners, on="_norm_seat", how="inner")
    winner_match = winner_compare[winner_compare["tbs_party"] == winner_compare["ds_party"]]
    winner_mismatch = winner_compare[winner_compare["tbs_party"] != winner_compare["ds_party"]]

    logging.info(f"\nWinners compared: {len(winner_compare)}")
    logging.info(f"Winners agree: {len(winner_match)}")
    logging.info(f"Winners disagree: {len(winner_mismatch)}")

    if len(winner_mismatch) > 0:
        logging.info("\nWinner disagreements:")
        for _, row in winner_mismatch.iterrows():
            logging.info(
                f"  {row['_norm_seat']}: "
                f"TBS={row['tbs_candidate']} ({row['tbs_party']}, {int(row['tbs_votes']):,}) vs "
                f"DS={row['ds_candidate']} ({row['ds_party']}, {int(row['ds_votes']):,})"
            )

    # Winner vote count comparison
    winner_votes_match = winner_compare[winner_compare["tbs_votes"] == winner_compare["ds_votes"]]
    winner_votes_diff = winner_compare[winner_compare["tbs_votes"] != winner_compare["ds_votes"]].copy()
    winner_votes_diff["diff"] = winner_votes_diff["ds_votes"] - winner_votes_diff["tbs_votes"]

    logging.info(f"\nWinner votes match exactly: {len(winner_votes_match)}/{len(winner_compare)}")
    logging.info(f"Winner votes differ: {len(winner_votes_diff)}/{len(winner_compare)}")

    if len(winner_votes_diff) > 0:
        logging.info("\nWinner vote differences (largest first):")
        for _, row in winner_votes_diff.sort_values("diff", key=abs, ascending=False).head(20).iterrows():
            logging.info(
                f"  {row['_norm_seat']}: "
                f"TBS={int(row['tbs_votes']):,} vs DS={int(row['ds_votes']):,} "
                f"(diff={int(row['diff']):+,})"
            )
        if len(winner_votes_diff) > 20:
            logging.info(f"  ... and {len(winner_votes_diff) - 20} more")

    # All candidate vote comparison
    ds_with_votes = ds_known[ds_known["_norm_seat"].isin(common_seats)].copy()
    logging.info(f"\nDS candidates with known votes in common seats: {len(ds_with_votes)}")

    all_mismatches = []
    matched = 0
    unmapped = 0

    for _, ds_row in ds_with_votes.iterrows():
        norm_seat = ds_row["_norm_seat"]
        mapped_party = ds_row["_party_mapped"]
        if 'Independent' in mapped_party:
            continue
        if 'Independent' in mapped_party:
            continue
        ds_votes = int(ds_row["votes"])

        tbs_match = tbs[
            (tbs["_norm_seat"] == norm_seat) & (tbs["party"] == mapped_party)
        ]

        # Fallback: try partial match (party name without abbreviation suffix)
        if len(tbs_match) == 0:
            base_party = re.sub(r"\s*\([^)]*\)\s*$", "", mapped_party).strip()
            seat_parties = tbs[tbs["_norm_seat"] == norm_seat]
            if base_party != mapped_party:
                tbs_match = seat_parties[
                    seat_parties["party"].str.startswith(base_party)
                ]
            # Fallback: check if any TBS party contains the mapped name as substring
            if len(tbs_match) == 0:
                tbs_match = seat_parties[
                    seat_parties["party"].str.contains(
                        re.escape(base_party), case=False, na=False
                    )
                ]

        if len(tbs_match) == 0:
            unmapped += 1
            all_mismatches.append({
                "seat_name": ds_row["seat_name"],
                "candidate_ds": ds_row.get("candidate", ""),
                "party_ds": ds_row["party"],
                "party_tbs": mapped_party,
                "tbs_votes": "-",
                "ds_votes": ds_votes,
                "diff": "-",
                "diff_pct": "-",
                "is_significant": True,
                "issue": "Party not found in TBS for this seat",
            })
            continue

        ds_candidate = ds_row.get("candidate", "")
        best = find_best_tbs_match(ds_candidate, tbs_match)
        tbs_votes = int(best["votes"])
        matched += 1

        if tbs_votes != ds_votes:
            diff = ds_votes - tbs_votes
            diff_pct = (abs(diff) / float(tbs_votes) * 100) if tbs_votes > 0 else 100.0
            all_mismatches.append({
                "seat_name": ds_row["seat_name"],
                "candidate_ds": ds_row.get("candidate", ""),
                "party_ds": ds_row["party"],
                "party_tbs": mapped_party,
                "tbs_votes": tbs_votes,
                "ds_votes": ds_votes,
                "diff": diff,
                "diff_pct": f"{diff_pct:.2f}%",
                "is_significant": diff_pct > 1.0,
                "issue": "Vote count mismatch",
            })

    vote_mismatches = [m for m in all_mismatches if m["issue"] == "Vote count mismatch"]
    not_in_tbs = [m for m in all_mismatches if "not found" in m["issue"]]

    logging.info(f"Successfully matched: {matched}")
    logging.info(f"Vote count matches: {matched - len(vote_mismatches)}")
    logging.info(f"Vote count mismatches: {len(vote_mismatches)}")
    logging.info(f"DS parties not in TBS for seat: {unmapped}")

    if vote_mismatches:
        logging.info(f"\nVote count mismatches (sorted by |diff|):")
        for m in sorted(vote_mismatches, key=lambda x: abs(x["diff"]), reverse=True)[:30]:
            logging.info(
                f"  {m['seat_name']} | {m['candidate_ds']} ({m['party_ds']}): "
                f"TBS={m['tbs_votes']:,} vs DS={m['ds_votes']:,} (diff={m['diff']:+,})"
            )
        if len(vote_mismatches) > 30:
            logging.info(f"  ... and {len(vote_mismatches) - 30} more")

    if not_in_tbs:
        logging.info(f"\nDS parties not found in TBS for their seat ({len(not_in_tbs)}):")
        for m in not_in_tbs:
            logging.info(
                f"  {m['seat_name']} | DS: \"{m['party_ds']}\" ({m['ds_votes']:,} votes) "
                f"-> mapped: \"{m['party_tbs']}\" — TBS has no such party for this seat"
            )

    out_path = os.path.join(output_dir, "verification_vote_mismatches.csv")
    if all_mismatches:
        pd.DataFrame(all_mismatches).to_csv(out_path, index=False)
        logging.info(f"Saved to {out_path}")

    return {
        "common_seats": len(common_seats),
        "winner_agree": len(winner_match),
        "winner_total": len(winner_compare),
        "winner_votes_match": len(winner_votes_match),
        "candidate_matched": matched,
        "candidate_votes_match": matched - len(vote_mismatches),
        "candidate_vote_mismatches": len(vote_mismatches),
        "ds_only_parties": unmapped,
        "all_mismatches": all_mismatches,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Cross-verify election data between TBS News and Daily Star."
    )
    parser.add_argument("--tbs_seats", default="result_from_source/result_from_tbsnews.csv")
    parser.add_argument("--ds_seats", default="result_from_source/result_from_dailystar.csv")
    parser.add_argument("--tbs_party_totals", default="result_from_source/tbsnews_party_totals.csv")
    parser.add_argument("--ds_party_totals", default="result_from_source/dailystar_party_totals.csv")
    parser.add_argument("--tbs_party_by_seat", default="result_from_source/tbsnews_party_by_seat.csv")
    parser.add_argument("--ds_party_by_seat", default="result_from_source/dailystar_party_by_seat.csv")
    parser.add_argument("--output_dir", default="result_from_source")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. Seat-level comparison
    seat_mismatches, common_count, only_tbs, only_ds = compare_seat_results(
        args.tbs_seats, args.ds_seats, args.output_dir
    )

    # 2. Party totals comparison
    party_mismatches, party_matched = compare_party_totals(
        args.tbs_party_totals, args.ds_party_totals, args.output_dir
    )

    # 3. Candidate vote count comparison
    vote_stats = compare_vote_counts(
        args.tbs_party_by_seat, args.ds_party_by_seat, args.output_dir
    )

    # Overall summary
    logging.info(f"\n{'='*60}")
    logging.info("OVERALL VERIFICATION SUMMARY")
    logging.info(f"{'='*60}")
    logging.info(f"Seats in both sources:         {vote_stats['common_seats']}")
    logging.info(f"Only in TBS:                   {len(only_tbs)}")
    logging.info(f"Only in DS:                    {len(only_ds)}")
    logging.info(f"Winner party agrees:           {vote_stats['winner_agree']}/{vote_stats['winner_total']}")
    logging.info(f"Winner votes match exactly:    {vote_stats['winner_votes_match']}/{vote_stats['winner_total']}")
    logging.info(f"Candidate votes matched:       {vote_stats['candidate_matched']}")
    logging.info(f"Candidate votes agree:         {vote_stats['candidate_votes_match']}/{vote_stats['candidate_matched']}")
    logging.info(f"Candidate vote mismatches:     {vote_stats['candidate_vote_mismatches']}")
    logging.info(f"Seat-level anomalies:          {len(seat_mismatches)}")
    logging.info(f"Party totals compared:         {party_matched}")
    logging.info(f"DS parties not in TBS seat:     {vote_stats['ds_only_parties']}")

    # Save summary CSV
    summary = {
        "common_seats": vote_stats["common_seats"],
        "only_in_tbs": len(only_tbs),
        "only_in_ds": len(only_ds),
        "winner_agree": vote_stats["winner_agree"],
        "winner_total": vote_stats["winner_total"],
        "winner_votes_match": vote_stats["winner_votes_match"],
        "candidate_votes_matched": vote_stats["candidate_matched"],
        "candidate_votes_agree": vote_stats["candidate_votes_match"],
        "candidate_vote_mismatches": vote_stats["candidate_vote_mismatches"],
        "seat_level_anomalies": len(seat_mismatches),
        "party_totals_compared": party_matched,
        "ds_only_parties": vote_stats["ds_only_parties"],
    }
    summary_path = os.path.join(args.output_dir, "verification_summary.csv")
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    logging.info(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
