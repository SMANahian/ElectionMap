import pandas as pd
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Find mismatches between BNP Alliance and 11 Party Alliance votes")
    parser.add_argument("--tbs_seats", default="result_from_source/result_from_tbsnews.csv")
    parser.add_argument("--ds_seats", default="result_from_source/result_from_dailystar.csv")
    parser.add_argument("--output", default="result_from_source/alliance_mismatch_report.csv")
    
    args = parser.parse_args()
    
    # Load TBS and replace - and NaN with 0
    tbs = pd.read_csv(args.tbs_seats)
    tbs['bnp_alliance_votes'] = pd.to_numeric(tbs['bnp_alliance_votes'].replace('-', '0').fillna(0))
    tbs['eleven_party_alliance_votes'] = pd.to_numeric(tbs['eleven_party_alliance_votes'].replace('-', '0').fillna(0))
    
    # Load DS and replace - and NaN with 0
    ds = pd.read_csv(args.ds_seats)
    ds['bnp_alliance_votes'] = pd.to_numeric(ds['bnp_alliance_votes'].replace('-', '0').fillna(0))
    ds['eleven_party_alliance_votes'] = pd.to_numeric(ds['eleven_party_alliance_votes'].replace('-', '0').fillna(0))
    
    # Normalize seat names just in case, though they should be matched by now
    from normalize import normalize_seat_name
    tbs['seat_name_norm'] = tbs['seat_name'].apply(normalize_seat_name)
    ds['seat_name_norm'] = ds['seat_name'].apply(normalize_seat_name)
    
    # Merge datasets
    merged = pd.merge(
        tbs[['seat_name', 'seat_name_norm', 'bnp_alliance_votes', 'eleven_party_alliance_votes']],
        ds[['seat_name_norm', 'bnp_alliance_votes', 'eleven_party_alliance_votes']],
        on='seat_name_norm',
        suffixes=('_tbs', '_ds'),
        indicator=True,
        how='inner'
    )
    
    mismatches = []
    
    for _, row in merged.iterrows():
        seat = row['seat_name']
        bnp_tbs = row['bnp_alliance_votes_tbs']
        bnp_ds = row['bnp_alliance_votes_ds']
        
        eleven_tbs = row['eleven_party_alliance_votes_tbs']
        eleven_ds = row['eleven_party_alliance_votes_ds']
        
        bnp_diff = bnp_tbs - bnp_ds
        eleven_diff = eleven_tbs - eleven_ds
        
        # Output if there's any mismatch in either alliance total
        if bnp_diff != 0 or eleven_diff != 0:
            mismatches.append({
                "seat_name": seat,
                "BNP_Alliance_TBS": bnp_tbs,
                "BNP_Alliance_DS": bnp_ds,
                "BNP_Diff_TBS_minus_DS": bnp_diff,
                "11_Party_TBS": eleven_tbs,
                "11_Party_DS": eleven_ds,
                "11_Party_Diff_TBS_minus_DS": eleven_diff
            })
            
    mismatch_df = pd.DataFrame(mismatches)
    
    print(f"Total processed seats: {len(merged)}")
    print(f"Total mismatches found: {len(mismatches)}")
    
    if len(mismatches) > 0:
        # Sort by maximum absolute discrepancy 
        mismatch_df['max_abs_diff'] = mismatch_df[['BNP_Diff_TBS_minus_DS', '11_Party_Diff_TBS_minus_DS']].abs().max(axis=1)
        mismatch_df = mismatch_df.sort_values(by='max_abs_diff', ascending=False).drop(columns=['max_abs_diff'])
        
        mismatch_df.to_csv(args.output, index=False)
        print(f"Mismatch report saved to: {args.output}")
        print("\nTop Mismatches (by highest discrepancy):")
        print(mismatch_df.head(20).to_string(index=False))

if __name__ == "__main__":
    main()
