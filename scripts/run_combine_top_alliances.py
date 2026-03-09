import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
from normalize import normalize_seat_name

def combine_top_alliances(file1, file2, output_file):
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    df1['seat_name_normalized'] = df1['seat_name'].apply(normalize_seat_name)
    df2['seat_name_normalized'] = df2['seat_name'].apply(normalize_seat_name)

    merged_df = pd.merge(df1, df2, on='seat_name_normalized', suffixes=('_source1', '_source2'), how='outer')

    combined_df = merged_df[['seat_name_normalized']].copy()
    combined_df.rename(columns={'seat_name_normalized': 'seat_name'}, inplace=True)

    # Identify all party columns by excluding metadata/alliance columns
    exclude_cols = {
        'seat_name', 'division', 'district', 'total_voters', 'male_voters', 'female_voters', 
        'hijra_voters', 'total_votes', 'top_three_candidates', 'top_three', 
        'bnp_votes', 'bnp_ratio', 'jamaat_votes', 'jamaat_ratio', 
        'democracy_platform_votes', 'democracy_platform_ratio', 
        'eleven_party_alliance_votes', 'eleven_party_alliance_ratio', 
        'bnp_alliance_votes', 'bnp_alliance_ratio', 
        'bnp_vs_eleven_party_alliance_votes', 'bnp_vs_eleven_party_alliance_ratio', 
        'seat_name_normalized', 'comments'
    }

    party_cols = set(df1.columns).union(set(df2.columns)) - exclude_cols
    party_cols = sorted(list(party_cols))

    discrepancy_comments = []

    for idx, row in merged_df.iterrows():
        comments = []
        for p_col in party_cols:
            raw_val1 = row.get(f"{p_col}_source1")
            raw_val2 = row.get(f"{p_col}_source2")
            
            # coerce to float to handle '-' and other strings safely
            try:
                val1 = float(raw_val1) if pd.notna(raw_val1) else np.nan
            except ValueError:
                val1 = np.nan
                
            try:
                val2 = float(raw_val2) if pd.notna(raw_val2) else np.nan
            except ValueError:
                val2 = np.nan

            if pd.notna(val1) and pd.notna(val2):
                if val1 != val2:
                    comments.append(f"Discrepancy in {p_col}: source1 has {val1}, source2 has {val2}. Took the max.")
                
        discrepancy_comments.append(" ".join(comments))

    # Compute sum of max votes per candidate/party for each seat
    candidate_max_sums = pd.Series(0.0, index=merged_df.index)
    for p_col in party_cols:
        c1, c2 = f"{p_col}_source1", f"{p_col}_source2"
        v1 = pd.to_numeric(merged_df[c1], errors='coerce').fillna(0) if c1 in merged_df.columns else pd.Series(0.0, index=merged_df.index)
        v2 = pd.to_numeric(merged_df[c2], errors='coerce').fillna(0) if c2 in merged_df.columns else pd.Series(0.0, index=merged_df.index)
        candidate_max_sums += pd.concat([v1, v2], axis=1).max(axis=1)

    # Compute vote columns (not ratios) using max between sources
    vote_target_cols = ['total_votes', 'bnp_alliance_votes', 'eleven_party_alliance_votes']
    for col in vote_target_cols:
        c1, c2 = f"{col}_source1", f"{col}_source2"
        if c1 in merged_df.columns and c2 in merged_df.columns:
            s1 = pd.to_numeric(merged_df[c1], errors='coerce')
            s2 = pd.to_numeric(merged_df[c2], errors='coerce')
            if col == 'total_votes':
                combined_df[col] = pd.concat([s1, s2, candidate_max_sums], axis=1).max(axis=1)
            else:
                combined_df[col] = pd.concat([s1, s2], axis=1).max(axis=1)
        elif c1 in merged_df.columns: combined_df[col] = pd.to_numeric(merged_df[c1], errors='coerce')
        elif c2 in merged_df.columns: combined_df[col] = pd.to_numeric(merged_df[c2], errors='coerce')

    # Recalculate ratios from combined votes instead of taking max from sources
    combined_df['bnp_alliance_ratio'] = combined_df['bnp_alliance_votes'] / combined_df['total_votes']
    combined_df['eleven_party_alliance_ratio'] = combined_df['eleven_party_alliance_votes'] / combined_df['total_votes']

    combined_df['comments'] = discrepancy_comments

    # No filtering - keeping all constituencies

    dirname = os.path.dirname(output_file)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    combined_df.to_csv(output_file, index=False)
    print(f'Combined vote counts saved to {output_file}')

if __name__ == '__main__':
    combine_top_alliances('result_from_source/result_from_dailystar.csv', 'result_from_source/result_from_tbsnews.csv', 'vote_count_combined/top_alliances_overview.csv')
