"""
Aggregate constituency-wide Election Commission results to district level.

Reads:
  - official_result/ec_constituency_wide.csv
  - config/district_name_map.csv

Writes:
  - official_result/ec_district_wide.csv
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pandas as pd


BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / "official_result" / "ec_constituency_wide.csv"
DISTRICT_MAP = BASE / "config" / "district_name_map.csv"
OUTPUT = BASE / "official_result" / "ec_district_wide.csv"

PARTY_COLUMNS_START = "Bangladesh Nationalist Party - BNP"
WINNER_BNP = "Bangladesh Nationalist Party - BNP"
WINNER_JAMAAT = "Bangladesh Jamaat-e-Islami"
WINNER_NCP = "Jatiyo Nagorik Party - NCP"
WINNER_INDEPENDENT = "Independent"


def load_district_map() -> dict[str, str]:
    mapping_df = pd.read_csv(DISTRICT_MAP)
    return dict(zip(mapping_df["election"], mapping_df["standard_name"]))


def pct(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, 2)


def derive_district_names(df: pd.DataFrame) -> pd.DataFrame:
    election_to_standard = load_district_map()
    result = df.copy()
    result["district_raw"] = result["seat_name"].str.replace(r"\s+\d+$", "", regex=True)
    result["district"] = result["district_raw"].map(election_to_standard)

    missing = sorted(result.loc[result["district"].isna(), "district_raw"].dropna().unique())
    if missing:
        raise ValueError(f"Missing district mappings for election names: {missing}")

    return result


def choose_seat_leader(winner_counts: Counter[str], party_vote_totals: dict[str, int]) -> tuple[str, int]:
    if not winner_counts:
        return "", 0

    max_seats = max(winner_counts.values())
    contenders = [party for party, seats in winner_counts.items() if seats == max_seats]
    if len(contenders) == 1:
        leader = contenders[0]
    else:
        leader = sorted(
            contenders,
            key=lambda party: (-party_vote_totals.get(party, 0), party),
        )[0]
    return leader, max_seats


def main() -> None:
    df = pd.read_csv(INPUT)
    party_columns = list(df.columns[df.columns.get_loc(PARTY_COLUMNS_START):])
    df = derive_district_names(df)
    numeric_columns = [
        "total_voters",
        "total_votes_cast",
        "valid_votes",
        "rejected_votes",
        "absent_voters",
        "total_centers",
        "total_candidates",
        "bnp_plus_votes",
        "eleven_parties_votes",
        "duf_votes",
        "ndf_votes",
        "greater_sunni_votes",
        "independent_votes",
        "other_party_votes",
        "bnp_votes",
        "jamaat_votes",
        "ncp_votes",
        *party_columns,
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    rows = []
    grouped = df.groupby(["district", "district_bn"], sort=True, dropna=False)
    for (district, district_bn), group in grouped:
        seat_count = int(len(group))
        total_voters = int(group["total_voters"].sum())
        total_votes_cast = int(group["total_votes_cast"].sum())
        valid_votes = int(group["valid_votes"].sum())
        rejected_votes = int(group["rejected_votes"].sum())
        absent_voters = int(group["absent_voters"].sum())
        total_centers = int(group["total_centers"].sum())
        total_candidates = int(group["total_candidates"].sum())

        full_party_totals = {
            party: int(group[party].sum())
            for party in party_columns
            if int(group[party].sum()) > 0
        }
        independent_votes = int(group["independent_votes"].sum())
        if independent_votes > 0:
            full_party_totals[WINNER_INDEPENDENT] = independent_votes

        ranked_parties = sorted(full_party_totals.items(), key=lambda item: (-item[1], item[0]))
        if ranked_parties:
            leading_party, leading_party_votes = ranked_parties[0]
        else:
            leading_party, leading_party_votes = "", 0

        if len(ranked_parties) > 1:
            runner_up_party, runner_up_votes = ranked_parties[1]
        else:
            runner_up_party, runner_up_votes = "", 0

        winner_counts = Counter(group["winner_party"].fillna(""))
        seat_leader, seat_leader_count = choose_seat_leader(winner_counts, full_party_totals)

        shares_sq = sum((votes / valid_votes) ** 2 for votes in full_party_totals.values() if valid_votes and votes > 0)
        effective_num_parties = round(1 / shares_sq, 2) if shares_sq else 0.0

        row = {
            "district": district,
            "district_bn": district_bn,
            "seat_count": seat_count,
            "total_voters": total_voters,
            "total_votes_cast": total_votes_cast,
            "valid_votes": valid_votes,
            "rejected_votes": rejected_votes,
            "absent_voters": absent_voters,
            "turnout_pct": pct(total_votes_cast, total_voters),
            "rejection_pct": pct(rejected_votes, total_votes_cast),
            "absence_pct": pct(absent_voters, total_voters),
            "total_centers": total_centers,
            "total_candidates": total_candidates,
            "avg_voters_per_center": round(total_voters / total_centers, 2) if total_centers else 0.0,
            "avg_candidates_per_seat": round(total_candidates / seat_count, 2) if seat_count else 0.0,
            "safe_seats": int((group["competitiveness"] == "safe").sum()),
            "competitive_seats": int((group["competitiveness"] == "competitive").sum()),
            "marginal_seats": int((group["competitiveness"] == "marginal").sum()),
            "very_close_seats": int((group["competitiveness"] == "very_close").sum()),
            "bnp_plus_votes": int(group["bnp_plus_votes"].sum()),
            "bnp_plus_pct": pct(group["bnp_plus_votes"].sum(), valid_votes),
            "eleven_parties_votes": int(group["eleven_parties_votes"].sum()),
            "eleven_parties_pct": pct(group["eleven_parties_votes"].sum(), valid_votes),
            "duf_votes": int(group["duf_votes"].sum()),
            "duf_pct": pct(group["duf_votes"].sum(), valid_votes),
            "ndf_votes": int(group["ndf_votes"].sum()),
            "ndf_pct": pct(group["ndf_votes"].sum(), valid_votes),
            "greater_sunni_votes": int(group["greater_sunni_votes"].sum()),
            "greater_sunni_pct": pct(group["greater_sunni_votes"].sum(), valid_votes),
            "independent_votes": independent_votes,
            "independent_pct": pct(independent_votes, valid_votes),
            "other_party_votes": int(group["other_party_votes"].sum()),
            "other_party_pct": pct(group["other_party_votes"].sum(), valid_votes),
            "bnp_votes": int(group["bnp_votes"].sum()),
            "bnp_pct": pct(group["bnp_votes"].sum(), valid_votes),
            "jamaat_votes": int(group["jamaat_votes"].sum()),
            "jamaat_pct": pct(group["jamaat_votes"].sum(), valid_votes),
            "ncp_votes": int(group["ncp_votes"].sum()),
            "ncp_pct": pct(group["ncp_votes"].sum(), valid_votes),
            "leading_party": leading_party,
            "leading_party_votes": leading_party_votes,
            "leading_party_pct": pct(leading_party_votes, valid_votes),
            "runner_up_party": runner_up_party,
            "runner_up_votes": runner_up_votes,
            "runner_up_pct": pct(runner_up_votes, valid_votes),
            "vote_margin": leading_party_votes - runner_up_votes,
            "vote_margin_pct": pct(leading_party_votes - runner_up_votes, valid_votes),
            "most_winning_seats_party": seat_leader,
            "most_winning_seats_count": seat_leader_count,
            "bnp_won_seats": int(winner_counts.get(WINNER_BNP, 0)),
            "jamaat_won_seats": int(winner_counts.get(WINNER_JAMAAT, 0)),
            "ncp_won_seats": int(winner_counts.get(WINNER_NCP, 0)),
            "independent_won_seats": int(winner_counts.get(WINNER_INDEPENDENT, 0)),
            "other_party_won_seats": int(
                seat_count
                - winner_counts.get(WINNER_BNP, 0)
                - winner_counts.get(WINNER_JAMAAT, 0)
                - winner_counts.get(WINNER_NCP, 0)
                - winner_counts.get(WINNER_INDEPENDENT, 0)
            ),
            "effective_num_parties": effective_num_parties,
        }
        rows.append(row)

    output_df = pd.DataFrame(rows)
    output_df = output_df.sort_values("district").reset_index(drop=True)
    output_df.to_csv(OUTPUT, index=False)

    print(f"Wrote {len(output_df)} districts to {OUTPUT}")
    print(f"Total voters:     {int(output_df['total_voters'].sum()):,}")
    print(f"Total valid votes:{int(output_df['valid_votes'].sum()):,}")
    print(f"Mean turnout:     {output_df['turnout_pct'].mean():.2f}%")


if __name__ == "__main__":
    main()
