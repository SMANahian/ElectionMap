"""
Extract per-district indicators from MICS6 SPSS datasets for correlation with election data.

Produces: unicef/mics6_district_indicators.csv
"""
import pyreadstat
import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "Bangladesh MICS6 SPSS Datasets")

def read_sav(filename, usecols=None):
    path = os.path.join(DATA_DIR, filename)
    df, meta = pyreadstat.read_sav(path, usecols=usecols)
    return df, meta

def pct(series, condition):
    """Percentage where condition is True, ignoring NaN."""
    valid = series.dropna()
    if len(valid) == 0:
        return np.nan
    return (condition[valid.index].sum() / len(valid)) * 100

def main():
    # ---- Household-level indicators (hh.sav) ----
    hh, hh_meta = read_sav("hh.sav", usecols=[
        "HH1", "HH7", "HH7A", "HH6",
        "windex5", "wscore",
        "HC8",   # electricity
        "HC12",  # mobile phone
        "HC13",  # internet
        "WS1",   # drinking water source
        "WS11",  # sanitation facility
    ])

    # District labels from metadata
    dist_labels = hh_meta.variable_value_labels.get("HH7A", {})

    hh_agg = hh.groupby("HH7A").agg(
        n_households=("HH1", "count"),
        wealth_score_mean=("wscore", "mean"),
        wealth_score_median=("wscore", "median"),
        pct_poorest=("windex5", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_richest=("windex5", lambda x: (x == 5).sum() / x.notna().sum() * 100),
        pct_electricity=("HC8", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_mobile=("HC12", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_internet=("HC13", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_urban=("HH6", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_improved_water=("WS1", lambda x: x.isin([11,12,13,14,21,31,41,51,61,71,91]).sum() / x.notna().sum() * 100),
        pct_improved_sanitation=("WS11", lambda x: x.isin([11,12,13,14,15,21,22,31]).sum() / x.notna().sum() * 100),
    ).reset_index()

    # ---- Education indicators (hl.sav) ----
    hl, _ = read_sav("hl.sav", usecols=["HH7A", "ED4", "ED5A", "ED5B", "HL4"])

    # ED4: ever attended school (1=yes, 2=no)
    # ED5A: highest level attended
    # ED5B: highest grade at that level
    # HL4: sex (1=male, 2=female)

    hl_agg = hl.groupby("HH7A").agg(
        pct_ever_school=("ED4", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_secondary_plus=("ED5A", lambda x: x.isin([2,3,4]).sum() / x.notna().sum() * 100),
    ).reset_index()

    # Female education
    hl_f = hl[hl["HL4"] == 2]
    hl_f_agg = hl_f.groupby("HH7A").agg(
        pct_female_ever_school=("ED4", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_female_secondary_plus=("ED5A", lambda x: x.isin([2,3,4]).sum() / x.notna().sum() * 100),
    ).reset_index()

    # ---- Women's indicators (wm.sav) ----
    wm, _ = read_sav("wm.sav", usecols=["HH7A", "welevel", "WAGEM", "MT1", "MT2", "MT9"])

    # welevel: education level (0=none,1=primary,2=lower sec,3=upper sec,4=higher)
    # WAGEM: age at first marriage
    # MT1: reads newspaper (1=almost daily,2=at least once a week,3=less,4=not at all)
    # MT2: listens to radio
    # MT9: uses internet

    wm_agg = wm.groupby("HH7A").agg(
        pct_women_no_education=("welevel", lambda x: (x == 0).sum() / x.notna().sum() * 100),
        pct_women_secondary_plus=("welevel", lambda x: x.isin([2,3,4]).sum() / x.notna().sum() * 100),
        median_marriage_age=("WAGEM", "median"),
        pct_women_internet=("MT9", lambda x: (x.isin([1,2,3])).sum() / x.notna().sum() * 100),
        pct_women_newspaper=("MT1", lambda x: (x.isin([1,2,3])).sum() / x.notna().sum() * 100),
    ).reset_index()

    # ---- Child health (ch.sav) ----
    ch, _ = read_sav("ch.sav", usecols=["HH7A", "BR1", "HAZ2", "WAZ2"])

    # BR1: birth registered (1=yes, 2=no)
    # HAZ2: height-for-age z-score WHO (stunted < -2, flag 99.99=missing)
    # WAZ2: weight-for-age z-score WHO (underweight < -2, flag 99.99=missing)
    ch.loc[ch["HAZ2"] > 90, "HAZ2"] = np.nan
    ch.loc[ch["WAZ2"] > 90, "WAZ2"] = np.nan

    ch_agg = ch.groupby("HH7A").agg(
        pct_birth_registered=("BR1", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_stunted=("HAZ2", lambda x: (x < -2).sum() / x.notna().sum() * 100),
        pct_underweight=("WAZ2", lambda x: (x < -2).sum() / x.notna().sum() * 100),
    ).reset_index()

    # ---- Birth history / fertility (bh.sav) ----
    bh, _ = read_sav("bh.sav", usecols=["HH7A", "BH5", "BH9C", "WM3", "HH1", "HH2"])

    # BH5: child still alive (1=yes, 2=no)
    # BH9C: age at death in months (imputed)
    # Under-5 mortality proxy: % of births where child died before 60 months
    bh_deaths = bh[bh["BH5"] == 2].copy()
    bh_deaths["under5_death"] = bh_deaths["BH9C"].apply(lambda x: 1 if pd.notna(x) and x < 60 else 0)

    bh_agg = bh.groupby("HH7A").agg(
        total_births=("BH5", "count"),
        pct_child_mortality=("BH5", lambda x: (x == 2).sum() / x.notna().sum() * 100),
    ).reset_index()

    # Average births per woman (fertility proxy)
    bh_fertility = bh.groupby(["HH7A", "HH1", "HH2", "WM3"]).size().reset_index(name="n_births")
    bh_fert_agg = bh_fertility.groupby("HH7A").agg(
        avg_births_per_woman=("n_births", "mean"),
    ).reset_index()

    bh_agg = bh_agg.merge(bh_fert_agg, on="HH7A", how="left")

    # ---- Foundational learning skills (fs.sav) ----
    fs, _ = read_sav("fs.sav", usecols=[
        "HH7A", "CB4",
        "FL21",  # reading proficiency (1=cannot read, 2=read with difficulty, 3=fluently)
        "FL22A", "FL22B", "FL22C",  # comprehension questions (1=correct)
        "FL25A", "FL25B", "FL25C", "FL25D", "FL25E",  # addition (1=correct)
    ])

    # CB4: ever attended school (1=yes, 2=no)
    # FL21: reading level (3=fluent)
    # Numeracy: count correct additions out of 5

    fs["can_read_fluently"] = (fs["FL21"] == 3).astype(float)
    fs["can_read"] = fs["FL21"].isin([2, 3]).astype(float)
    add_cols = ["FL25A", "FL25B", "FL25C", "FL25D", "FL25E"]
    fs["additions_correct"] = fs[add_cols].apply(lambda row: (row == 1).sum(), axis=1)
    fs["numeracy_3of5"] = (fs["additions_correct"] >= 3).astype(float)

    comp_cols = ["FL22A", "FL22B", "FL22C"]
    fs["comprehension_correct"] = fs[comp_cols].apply(lambda row: (row == 1).sum(), axis=1)
    fs["comprehension_2of3"] = (fs["comprehension_correct"] >= 2).astype(float)

    fs_agg = fs.groupby("HH7A").agg(
        n_children_5_17=("CB4", "count"),
        pct_children_ever_school=("CB4", lambda x: (x == 1).sum() / x.notna().sum() * 100),
        pct_read_fluently=("can_read_fluently", lambda x: x.sum() / x.notna().sum() * 100),
        pct_can_read=("can_read", lambda x: x.sum() / x.notna().sum() * 100),
        pct_numeracy=("numeracy_3of5", lambda x: x.sum() / x.notna().sum() * 100),
        pct_comprehension=("comprehension_2of3", lambda x: x.sum() / x.notna().sum() * 100),
    ).reset_index()

    # ---- Merge all ----
    result = hh_agg
    for df in [hl_agg, hl_f_agg, wm_agg, ch_agg, bh_agg, fs_agg]:
        result = result.merge(df, on="HH7A", how="left")

    # Map district codes to names
    result["district"] = result["HH7A"].map(dist_labels).fillna(result["HH7A"].astype(str))
    result = result.drop(columns=["HH7A"])

    # Reorder: district first
    cols = ["district"] + [c for c in result.columns if c != "district"]
    result = result[cols]

    # Round numeric columns
    num_cols = result.select_dtypes(include=[np.number]).columns
    result[num_cols] = result[num_cols].round(2)

    out_path = os.path.join(os.path.dirname(__file__), "mics6_district_indicators.csv")
    result.to_csv(out_path, index=False)
    print(f"Saved {len(result)} districts to {out_path}")
    print(f"Columns: {list(result.columns)}")

if __name__ == "__main__":
    main()
