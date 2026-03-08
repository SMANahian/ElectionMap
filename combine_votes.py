
import pandas as pd
import numpy as np

def combine_vote_counts(file1, file2, output_file):
    """
    Combines vote count data from two CSV files, takes the max vote count for each candidate,
    and adds a comments column to explain discrepancies.
    """
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)

    # Normalize seat_name column
    df1['seat_name_normalized'] = df1['seat_name'].str.strip().str.replace(r'\s+', '-', regex=True).str.lower()
    df2['seat_name_normalized'] = df2['seat_name'].str.strip().str.replace(r'\s+', '-', regex=True).str.lower()

    # Standardization mapping
    name_mapping = {
        'jessore': 'jashore',
        'comilla': 'cumilla',
        'bogra': 'bogura',
        'chapai-nawabganj': 'chapainawabganj',
        'netrokona': 'netrakona',
        'jhalakathi': 'jhalokathi',
        'chittagong': 'chattogram',
    }

    for wrong_name, right_name in name_mapping.items():
        df2['seat_name_normalized'] = df2['seat_name_normalized'].str.replace(wrong_name, right_name)

    # Use seat_name as the key for merging
    merged_df = pd.merge(df1, df2, on='seat_name_normalized', suffixes=('_source1', '_source2'), how='outer')

    # Get the party columns
    party_columns = df1.columns[df1.columns.get_loc('Amar Bangladesh Party (AB)') :]
    
    # Create a new dataframe for the combined results
    combined_df = merged_df[['seat_name_normalized']].copy()
    combined_df.rename(columns={'seat_name_normalized': 'seat_name'}, inplace=True)


    # Initialize comments column
    combined_df['comments'] = ''

    for party_col in party_columns:
        col1 = f"{party_col}_source1"
        col2 = f"{party_col}_source2"
        
        if col1 in merged_df.columns and col2 in merged_df.columns:
            # Convert columns to numeric, coercing errors to NaN
            source1_numeric = pd.to_numeric(merged_df[col1], errors='coerce')
            source2_numeric = pd.to_numeric(merged_df[col2], errors='coerce')

            # Add comments for discrepancies before filling NaN
            discrepancy_mask = (source1_numeric != source2_numeric) & (source1_numeric.notna()) & (source2_numeric.notna())
            
            for index, has_discrepancy in discrepancy_mask.items():
                if has_discrepancy:
                    source1_votes = merged_df.loc[index, col1]
                    source2_votes = merged_df.loc[index, col2]
                    comment = f"Discrepancy in {party_col}: source1 has {source1_votes}, source2 has {source2_votes}. Took the max."
                    combined_df.loc[index, 'comments'] += comment + " "

            # Fill NaN values with 0 for max calculation
            source1_filled = source1_numeric.fillna(0)
            source2_filled = source2_numeric.fillna(0)

            # Create a new column in the combined_df for the max votes
            combined_df[party_col] = pd.concat([source1_filled, source2_filled], axis=1).max(axis=1)

        elif col1 in merged_df.columns:
            combined_df[party_col] = pd.to_numeric(merged_df[col1], errors='coerce').fillna(0)
        elif col2 in merged_df.columns:
            combined_df[party_col] = pd.to_numeric(merged_df[col2], errors='coerce').fillna(0)


    combined_df.to_csv(output_file, index=False)
    print(f"Combined vote counts saved to {output_file}")

if __name__ == "__main__":
    file1 = 'result_from_source/result_from_dailystar.csv'
    file2 = 'result_from_source/result_from_tbsnews.csv'
    output_file = 'vote_count_combined/combined_vote_counts.csv'
    combine_vote_counts(file1, file2, output_file)
