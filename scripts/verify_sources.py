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


# Mapping of Daily Star party names to TBS party names.
PARTY_NAME_MAP = {
    "BNP": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "Independent": "Independent Candidate (Independent)",
    "National Citizens Party - NCP": "National Citizen Party (NCP)",
    "Bangladesh Khilafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Khilafat Majlis": "Khelafat Majlis",
    "Islamic Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Liberal Democratic Party - LDP": "Bangladesh Liberal Democratic Party (LDP)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Bangladesh Islamic Front": "Bangladesh Islami Front (BIF)",
    "Gono Odhikar Parishad": "Gono Odhikar Parishad (GOP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Bangladesh Development Party - BDP": "Bangladesh Development Party (BDP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Jamiat Ulama-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Gono Forum": "Gono Forum (GF)",
    "Bangladesh Supreme Party - BSP": "Bangladesh Supreme Party (BSP)",
    "Zaker Party": "Zaker Party (ZP)",
    "Bangladesh Jasod": "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)",
    "Bangladesh Congress": "Bangladesh Congress",
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Ganosamhati Andolon": "Ganosanhati Andolan (GSA)",
    "Bangladesh Muslim League": "Bangladesh Muslim League (BML)",
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League (BML)",
    "Bangladesh Nezam e Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Nagorik Oikya": "Nagorik Oikya (NO)",
    "Bangladesh Republican Party - BRP": "Bangladesh Republican Party (BRP)",
    "Communist Party of Bangladesh": "Communist Party of Bangladesh (CPB)",
    "Bangladesh Samajtantrik Dal": "Bangladesh Samajtantrik Dal (Basad)",
    "Insaniat Biplob Bangladesh - Insaniat Biplob": "Insaniyat Biplob Bangladesh (IBB)",
    "Nationalist Democratic Movement - NDM": "Bangladesh Nationalist Front (BNF)",
    "Ganatantri Party": "Ganatantri Party (GP)",
    "Janotar Dol": "Janotar Dol",
    "Amjanatar Dal": "Amjanatar Dol",
    "Islamic Front Bangladesh - IFB": "Islamic Front Bangladesh (IFB)",
    "Bangladesher Biplobi Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Khelafat Andolon": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Sangskritik Muktijote": "Bangladesh Sangskritik Muktijote (BSM)",
    "Bangladesher Samajtantrik Dal (BSD)": "Bangladesh Samajtantrik Dal (Basad)",
    "Bangladesh Nationalist Front - BNF": "Bangladesh Nationalist Front (BNF)",
}

# Known alternative spellings between TBS and Daily Star
SEAT_NAME_ALIASES = {
    "bogra": "bogura",
    "comilla": "cumilla",
    "jessore": "jashore",
    "jhalakathi": "jhalokathi",
    "netrokona": "netrakona",
    "chapai nawabganj": "chapainawabganj",
    "cox's bazar": "coxs bazar",
}


def normalize_seat_name(name: str) -> str:
    """Normalize seat name for matching between sources."""
    name = name.strip().lower()
    name = re.sub(r"[-–—]", " ", name)
    name = re.sub(r"[''']s\b", "s", name)
    name = re.sub(r"\s+", " ", name)
    for old, new in SEAT_NAME_ALIASES.items():
        if name.startswith(old + " "):
            name = new + name[len(old):]
            break
    return name


def map_ds_party(ds_party: str) -> str:
    """Map a Daily Star party name to TBS equivalent."""
    return PARTY_NAME_MAP.get(ds_party, ds_party)


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
            mismatches.append({
                "seat_name": seat,
                "field": "total_votes",
                "tbs_value": int(t_total),
                "ds_value": int(d_total),
                "diff": int(d_total - t_total),
                "issue": "DS partial total exceeds TBS full total",
            })

        # Coalition vote columns: DS partial <= TBS full
        for col in coalition_cols:
            tv = t.get(col)
            dv = d.get(col)
            if pd.notna(tv) and pd.notna(dv) and dv > tv:
                mismatches.append({
                    "seat_name": seat,
                    "field": col,
                    "tbs_value": int(tv),
                    "ds_value": int(dv),
                    "diff": int(dv - tv),
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
    ds["_mapped"] = ds["party"].apply(map_ds_party)

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
            mismatches.append({
                "party_tbs": tbs_party,
                "party_ds": ds_party,
                "tbs_votes": int(tbs_votes),
                "ds_votes": int(ds_votes),
                "diff": diff,
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
    ds["_party_mapped"] = ds["party"].apply(map_ds_party)

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
        ds_votes = int(ds_row["votes"])

        tbs_match = tbs[
            (tbs["_norm_seat"] == norm_seat) & (tbs["party"] == mapped_party)
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
                "issue": "Party not found in TBS (mapping needed?)",
            })
            continue

        tbs_votes = int(tbs_match.iloc[0]["votes"])
        matched += 1

        if tbs_votes != ds_votes:
            diff = ds_votes - tbs_votes
            all_mismatches.append({
                "seat_name": ds_row["seat_name"],
                "candidate_ds": ds_row.get("candidate", ""),
                "party_ds": ds_row["party"],
                "party_tbs": mapped_party,
                "tbs_votes": tbs_votes,
                "ds_votes": ds_votes,
                "diff": diff,
                "issue": "Vote count mismatch",
            })

    vote_mismatches = [m for m in all_mismatches if m["issue"] == "Vote count mismatch"]
    mapping_issues = [m for m in all_mismatches if "mapping" in m["issue"]]

    logging.info(f"Successfully matched: {matched}")
    logging.info(f"Vote count matches: {matched - len(vote_mismatches)}")
    logging.info(f"Vote count mismatches: {len(vote_mismatches)}")
    logging.info(f"Unmapped parties: {unmapped}")

    if vote_mismatches:
        logging.info(f"\nVote count mismatches (sorted by |diff|):")
        for m in sorted(vote_mismatches, key=lambda x: abs(x["diff"]), reverse=True)[:30]:
            logging.info(
                f"  {m['seat_name']} | {m['candidate_ds']} ({m['party_ds']}): "
                f"TBS={m['tbs_votes']:,} vs DS={m['ds_votes']:,} (diff={m['diff']:+,})"
            )
        if len(vote_mismatches) > 30:
            logging.info(f"  ... and {len(vote_mismatches) - 30} more")

    if mapping_issues:
        logging.info(f"\nUnmapped DS parties ({len(mapping_issues)}):")
        seen = set()
        for m in mapping_issues:
            if m["party_ds"] not in seen:
                seen.add(m["party_ds"])
                logging.info(f"  DS: \"{m['party_ds']}\" -> tried: \"{m['party_tbs']}\"")

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
        "unmapped": unmapped,
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
    logging.info(f"Unmapped party names:          {vote_stats['unmapped']}")

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
        "unmapped_parties": vote_stats["unmapped"],
    }
    summary_path = os.path.join(args.output_dir, "verification_summary.csv")
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    logging.info(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
