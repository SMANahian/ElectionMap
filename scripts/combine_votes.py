import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from normalize import normalize_seat_name

def combine_vote_counts(file1, file2, output_file):
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    df1['seat_name_normalized'] = df1['seat_name'].apply(normalize_seat_name)
    df2['seat_name_normalized'] = df2['seat_name'].apply(normalize_seat_name)

    merged_df = pd.merge(df1, df2, on='seat_name_normalized', suffixes=('_source1', '_source2'), how='outer')

    combined_df = merged_df[['seat_name_normalized']].copy()
    combined_df.rename(columns={'seat_name_normalized': 'seat_name'}, inplace=True)

    # Re-apply vital columns 
    for col in ['total_votes', 'total_voters', 'bnp_ratio', 'jamaat_ratio', 'eleven_party_alliance_ratio']:
        c1, c2 = f"{col}_source1", f"{col}_source2"
        if c1 in merged_df.columns and c2 in merged_df.columns:
            combined_df[col] = merged_df[c2].fillna(merged_df[c1])
        elif c1 in merged_df.columns: combined_df[col] = merged_df[c1]
        elif c2 in merged_df.columns: combined_df[col] = merged_df[c2]

    # Parties
    p1 = df1.columns.get_loc('bnp_ratio') + 1 if 'bnp_ratio' in df1.columns else -1
    cols1 = set(df1.columns[p1:]) if p1 >= 0 else set()
    cols1.discard('seat_name')
    # Build per-party columns and track discrepancies
    discrepancy_comments = []
    party_values = {}

    for p_col in cols1:
        c1, c2 = f"{p_col}_source1", f"{p_col}_source2"
        v1 = pd.to_numeric(merged_df[c1], errors='coerce').fillna(0) if c1 in merged_df.columns else pd.Series(0, index=merged_df.index)
        v2 = pd.to_numeric(merged_df[c2], errors='coerce').fillna(0) if c2 in merged_df.columns else pd.Series(0, index=merged_df.index)
        party_values[p_col] = (v1, v2)
        combined_df[p_col] = pd.concat([v1, v2], axis=1).max(axis=1)

    # Only flag discrepancies for actual vote count columns (not ratios/metadata)
    skip_suffixes = ('_ratio', '_votes', '_voters')
    vote_cols = [c for c in cols1 if not any(c.endswith(s) for s in skip_suffixes)
                 and c not in ('total_votes', 'total_voters', 'male_voters', 'female_voters',
                               'hijra_voters', 'top_three_candidates', 'top_three',
                               'seat_name_normalized', 'comments', 'division', 'district')]

    for idx in merged_df.index:
        comments = []
        for p_col in vote_cols:
            v1_val, v2_val = party_values[p_col][0].loc[idx], party_values[p_col][1].loc[idx]
            if v1_val != v2_val and v1_val > 0 and v2_val > 0:
                comments.append(f"Discrepancy in {p_col}: source1 has {int(v1_val)}, source2 has {int(v2_val)}. Took the max.")
        discrepancy_comments.append("; ".join(comments))

    combined_df['comments'] = discrepancy_comments

    dirname = os.path.dirname(output_file)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    combined_df.to_csv(output_file, index=False)
    print(f'Saved {len(combined_df)} seats to {output_file}')

if __name__ == '__main__':
    combine_vote_counts('result_from_source/result_from_dailystar.csv', 'result_from_source/result_from_tbsnews.csv', 'vote_count_combined/combined_vote_counts.csv')
