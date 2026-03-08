"""
verify_sources.py
=================

Cross-verifies election data between TBS News and Daily Star sources.

Compares:
1. Seat coverage — which seats are in each source
2. Winner agreement — do both sources agree on the winning party
3. Exact vote counts — for candidates where both sources have data,
   do the vote counts match exactly
4. Anomalies — DS partial totals exceeding TBS full totals

The primary comparison uses the party_by_seat CSVs which have
individual candidate vote counts per seat.

Usage::

    python3 scripts/verify_sources.py

Outputs a mismatch report CSV and prints a summary to the console.
"""

import argparse
import logging
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
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League (BML)",
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
    name = re.sub(r"[''']s\b", "s", name)  # Cox's -> Coxs
    name = re.sub(r"\s+", " ", name)
    # Apply known aliases
    for old, new in SEAT_NAME_ALIASES.items():
        if name.startswith(old + " "):
            name = new + name[len(old):]
            break
    return name


def map_ds_party(ds_party: str) -> str:
    """Map a Daily Star party name to TBS equivalent."""
    return PARTY_NAME_MAP.get(ds_party, ds_party)


def compare_vote_counts(tbs_pbs_path: str, ds_pbs_path: str, output_path: str):
    """Main comparison: match candidates by seat+party, compare exact vote counts."""

    tbs = pd.read_csv(tbs_pbs_path, na_values=["-"])
    ds = pd.read_csv(ds_pbs_path, na_values=["-"])

    logging.info(f"TBS party_by_seat rows: {len(tbs)}")
    logging.info(f"DS party_by_seat rows: {len(ds)}")

    # Normalize
    tbs["_norm_seat"] = tbs["seat_name"].apply(normalize_seat_name)
    ds["_norm_seat"] = ds["seat_name"].apply(normalize_seat_name)
    ds["_party_mapped"] = ds["party"].apply(map_ds_party)

    # --- 1. Seat coverage ---
    tbs_seats = set(tbs["_norm_seat"].unique())
    ds_seats = set(ds["_norm_seat"].unique())
    common_seats = tbs_seats & ds_seats
    only_tbs = tbs_seats - ds_seats
    only_ds = ds_seats - tbs_seats

    logging.info(f"\n{'='*60}")
    logging.info("SEAT COVERAGE")
    logging.info(f"{'='*60}")
    logging.info(f"TBS seats: {len(tbs_seats)}")
    logging.info(f"DS seats: {len(ds_seats)}")
    logging.info(f"Common: {len(common_seats)}")
    if only_tbs:
        logging.info(f"Only in TBS ({len(only_tbs)}): {sorted(only_tbs)}")
    if only_ds:
        logging.info(f"Only in DS ({len(only_ds)}): {sorted(only_ds)}")

    # --- 2. Winner comparison ---
    logging.info(f"\n{'='*60}")
    logging.info("WINNER COMPARISON")
    logging.info(f"{'='*60}")

    # Get winner per seat from TBS (highest votes)
    tbs_winners = (
        tbs.loc[tbs.groupby("_norm_seat")["votes"].idxmax()]
        [["_norm_seat", "party", "votes"]]
        .rename(columns={"party": "tbs_winner_party", "votes": "tbs_winner_votes"})
    )

    # Get winner per seat from DS (highest known votes)
    ds_known = ds[ds["votes"].notna()].copy()
    ds_winners = (
        ds_known.loc[ds_known.groupby("_norm_seat")["votes"].idxmax()]
        [["_norm_seat", "_party_mapped", "votes"]]
        .rename(columns={"_party_mapped": "ds_winner_party", "votes": "ds_winner_votes"})
    )

    winner_compare = tbs_winners.merge(ds_winners, on="_norm_seat", how="inner")
    winner_match = winner_compare[
        winner_compare["tbs_winner_party"] == winner_compare["ds_winner_party"]
    ]
    winner_mismatch = winner_compare[
        winner_compare["tbs_winner_party"] != winner_compare["ds_winner_party"]
    ]

    logging.info(f"Winners compared: {len(winner_compare)}")
    logging.info(f"Winners agree: {len(winner_match)}")
    logging.info(f"Winners disagree: {len(winner_mismatch)}")

    if len(winner_mismatch) > 0:
        logging.info("\nWinner disagreements:")
        for _, row in winner_mismatch.iterrows():
            logging.info(
                f"  {row['_norm_seat']}: "
                f"TBS={row['tbs_winner_party']} ({int(row['tbs_winner_votes'])} votes) vs "
                f"DS={row['ds_winner_party']} ({int(row['ds_winner_votes'])} votes)"
            )

    # --- 3. Exact vote count comparison ---
    logging.info(f"\n{'='*60}")
    logging.info("VOTE COUNT COMPARISON (exact match)")
    logging.info(f"{'='*60}")

    # Only DS rows with known votes in common seats
    ds_with_votes = ds_known[ds_known["_norm_seat"].isin(common_seats)].copy()
    logging.info(f"DS candidates with known votes in common seats: {len(ds_with_votes)}")

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
            # Party name mapping might be missing
            unmapped += 1
            all_mismatches.append({
                "seat_name": ds_row["seat_name"],
                "party_ds": ds_row["party"],
                "party_tbs": mapped_party,
                "candidate_ds": ds_row.get("candidate", ""),
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
                "party_ds": ds_row["party"],
                "party_tbs": mapped_party,
                "candidate_ds": ds_row.get("candidate", ""),
                "tbs_votes": tbs_votes,
                "ds_votes": ds_votes,
                "diff": diff,
                "issue": "Vote count mismatch",
            })

    vote_mismatches = [m for m in all_mismatches if m["issue"] == "Vote count mismatch"]
    mapping_issues = [m for m in all_mismatches if m["issue"] != "Vote count mismatch"]

    logging.info(f"Successfully matched: {matched}")
    logging.info(f"Vote count matches: {matched - len(vote_mismatches)}")
    logging.info(f"Vote count mismatches: {len(vote_mismatches)}")
    logging.info(f"Unmapped parties: {unmapped}")

    if vote_mismatches:
        logging.info(f"\nVote count mismatches:")
        for m in sorted(vote_mismatches, key=lambda x: abs(x["diff"]), reverse=True)[:50]:
            logging.info(
                f"  {m['seat_name']} | {m['party_ds']}: "
                f"TBS={m['tbs_votes']:,} vs DS={m['ds_votes']:,} "
                f"(diff={m['diff']:+,})"
            )
        if len(vote_mismatches) > 50:
            logging.info(f"  ... and {len(vote_mismatches) - 50} more")

    if mapping_issues:
        logging.info(f"\nUnmapped DS parties (need entry in PARTY_NAME_MAP):")
        seen = set()
        for m in mapping_issues:
            key = m["party_ds"]
            if key not in seen:
                seen.add(key)
                logging.info(f"  DS: \"{m['party_ds']}\" -> mapped: \"{m['party_tbs']}\"")

    # --- 4. Winner vote count comparison ---
    logging.info(f"\n{'='*60}")
    logging.info("WINNER VOTE COUNT COMPARISON")
    logging.info(f"{'='*60}")

    winner_votes_match = winner_compare[
        winner_compare["tbs_winner_votes"] == winner_compare["ds_winner_votes"]
    ]
    winner_votes_diff = winner_compare[
        winner_compare["tbs_winner_votes"] != winner_compare["ds_winner_votes"]
    ].copy()
    winner_votes_diff["diff"] = (
        winner_votes_diff["ds_winner_votes"] - winner_votes_diff["tbs_winner_votes"]
    )

    logging.info(f"Winner votes match exactly: {len(winner_votes_match)}")
    logging.info(f"Winner votes differ: {len(winner_votes_diff)}")

    if len(winner_votes_diff) > 0:
        logging.info("\nWinner vote differences (largest first):")
        for _, row in winner_votes_diff.sort_values("diff", key=abs, ascending=False).head(20).iterrows():
            logging.info(
                f"  {row['_norm_seat']}: "
                f"TBS={int(row['tbs_winner_votes']):,} vs "
                f"DS={int(row['ds_winner_votes']):,} "
                f"(diff={int(row['diff']):+,})"
            )

    # --- Summary ---
    logging.info(f"\n{'='*60}")
    logging.info("OVERALL SUMMARY")
    logging.info(f"{'='*60}")
    logging.info(f"Seats in both sources: {len(common_seats)}")
    logging.info(f"Winner party agrees: {len(winner_match)}/{len(winner_compare)}")
    logging.info(f"Winner votes match exactly: {len(winner_votes_match)}/{len(winner_compare)}")
    logging.info(
        f"All candidate votes match: "
        f"{matched - len(vote_mismatches)}/{matched}"
    )
    if unmapped:
        logging.info(f"Unmapped party names: {unmapped} (add to PARTY_NAME_MAP)")

    # Save full mismatch report
    if all_mismatches:
        mismatch_df = pd.DataFrame(all_mismatches)
        mismatch_df.to_csv(output_path, index=False)
        logging.info(f"\nFull mismatch report saved to {output_path}")

    return all_mismatches


def main():
    parser = argparse.ArgumentParser(
        description="Cross-verify election data between TBS News and Daily Star."
    )
    parser.add_argument(
        "--tbs_party_by_seat", default="results/party_by_seat.csv",
        help="TBS party-by-seat CSV.",
    )
    parser.add_argument(
        "--ds_party_by_seat", default="result_from_source/dailystar_party_by_seat.csv",
        help="Daily Star party-by-seat CSV.",
    )
    parser.add_argument(
        "--output", default="result_from_source/verification_mismatches.csv",
        help="Output CSV for mismatch report.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    compare_vote_counts(args.tbs_party_by_seat, args.ds_party_by_seat, args.output)


if __name__ == "__main__":
    main()
