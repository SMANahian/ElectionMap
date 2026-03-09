import pandas as pd
import re
from difflib import SequenceMatcher
from normalize import normalize_seat_name

def main():
    tbs = pd.read_csv('result_from_source/tbsnews_party_by_seat.csv')
    ds = pd.read_csv('result_from_source/dailystar_party_by_seat.csv')

    # Ensure seat names are fully normalized for inner join
    tbs['seat_name'] = tbs['seat_name'].apply(normalize_seat_name)
    ds['seat_name'] = ds['seat_name'].apply(normalize_seat_name)

    # Exclude Independents
    tbs = tbs[~tbs['party'].str.contains('Independent Candidate', na=False)]
    ds = ds[~ds['party'].str.contains('Independent Candidate', na=False)]

    merged = pd.merge(tbs, ds, on=['seat_name', 'party'], suffixes=('_tbs', '_ds'))

    completely_different = []
    spelling_differences = []

    def phonetic_rough(n):
        n = n.replace('v', 'b').replace('w', 'o').replace('z', 'j').replace('q', 'k').replace('ph', 'f').replace('y', 'i')
        n = n.replace('sh', 's').replace('ee', 'i').replace('oo', 'u').replace('ou', 'u').replace('ah', 'a')
        n = re.sub(r'[aeiou]', '', n) # Strip vowels for rough consonant match
        n = re.sub(r'([a-z])\1+', r'\1', n) # Remove double consonants
        return n

    for _, row in merged.iterrows():
        c_tbs = str(row['candidate_tbs']).strip()
        c_ds = str(row['candidate_ds']).strip()
        
        # Skip if one is missing
        if c_tbs.lower() in ['nan', '-'] or c_ds.lower() in ['nan', '-']:
            continue
            
        if c_tbs.lower() != c_ds.lower():
            # 1. Remove common titles
            titles = r'\b(md|mr|dr|al-haj|al|haj|hazi|mohammad|muhammad|muhammed|abu|abdul|miah|chowdhury|advocate|khandaker|syed|akm|moulana|begum|mst|engr|barrister|sheikh|khan|sardar|kazi|mia|haque)\b\.?'
            
            n1 = re.sub(titles, '', c_tbs.lower())
            n2 = re.sub(titles, '', c_ds.lower())
            
            # 2. Strip non-alphabetic, remove all spaces to handle splitting differences
            n1 = re.sub(r'[^a-z]', '', n1)
            n2 = re.sub(r'[^a-z]', '', n2)
            
            if not n1 or not n2:
                spelling_differences.append(row) 
                continue
                
            n1_p = phonetic_rough(n1)
            n2_p = phonetic_rough(n2)
            
            ratio = SequenceMatcher(None, n1, n2).ratio()
            ratio_p = SequenceMatcher(None, n1_p, n2_p).ratio()
            
            # If the consonant match is strong, or string similarity is high
            if max(ratio, ratio_p) > 0.65:
                spelling_differences.append(row)
            # Or if one is fully contained in another (e.g., matching missing last names)
            elif n1_p in n2_p or n2_p in n1_p:
                spelling_differences.append(row)
            else:
                completely_different.append(row)

    print("=== COMPLETELY DIFFERENT CANDIDATES ===")
    print(f"Found {len(completely_different)} cases where sources list totally different people:")
    for r in completely_different:
        print(f"\n{r['seat_name']} | {r['party']}")
        print(f"  TBS: {r['candidate_tbs']}")
        print(f"  DS : {r['candidate_ds']}")

if __name__ == "__main__":
    main()