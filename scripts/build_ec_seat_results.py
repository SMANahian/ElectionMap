"""
build_ec_seat_results.py — Build seat_results.csv from official EC data.

Reads:  official_result/raw_data/ (cached JSON from scrape_ec.py)
        official_result/ecs_party_symbols.csv
        config/coalitions.json
Output: results/seat_results.csv (same format as scrape_votes.py)

This replaces scrape_votes.py (TBS-sourced) with official Election
Commission data while producing an identical CSV schema so that
build_map.py works without changes.
"""

import argparse
import csv
import json
import os
import unicodedata
from collections import defaultdict

from normalize import (
    normalize_party,
    normalize_seat_name,
    normalize_location_name,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "official_result", "raw_data")
SYMBOLS_CSV = os.path.join(BASE, "official_result", "ecs_party_symbols.csv")

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bangla district -> English
DISTRICT_MAP = {
    "পঞ্চগড়": "Panchagarh", "ঠাকুরগাঁও": "Thakurgaon", "দিনাজপুর": "Dinajpur",
    "নীলফামারী": "Nilphamari", "লালমনিরহাট": "Lalmonirhat", "রংপুর": "Rangpur",
    "গাইবান্ধা": "Gaibandha", "কুড়িগ্রাম": "Kurigram", "শেরপুর": "Sherpur",
    "জামালপুর": "Jamalpur", "ময়মনসিংহ": "Mymensingh", "নেত্রকোণা": "Netrakona",
    "নেত্রকোনা": "Netrakona",
    "কিশোরগঞ্জ": "Kishoreganj", "বগুড়া": "Bogura", "জয়পুরহাট": "Joypurhat",
    "নওগাঁ": "Naogaon", "চাঁপাইনবাবগঞ্জ": "Chapainawabganj", "রাজশাহী": "Rajshahi",
    "নাটোর": "Natore", "পাবনা": "Pabna", "সিরাজগঞ্জ": "Sirajganj",
    "টাঙ্গাইল": "Tangail", "টাংগাইল": "Tangail",
    "গাজীপুর": "Gazipur", "ঢাকা": "Dhaka",
    "মানিকগঞ্জ": "Manikganj", "মুন্সীগঞ্জ": "Munshiganj", "মুন্সিগঞ্জ": "Munshiganj",
    "নারায়ণগঞ্জ": "Narayanganj",
    "ফরিদপুর": "Faridpur", "গোপালগঞ্জ": "Gopalganj",
    "মাদারীপুর": "Madaripur", "মাদারিপুর": "Madaripur",
    "শরীয়তপুর": "Shariatpur", "শরিয়তপুর": "Shariatpur", "রাজবাড়ী": "Rajbari",
    "কুষ্টিয়া": "Kushtia", "মেহেরপুর": "Meherpur", "চুয়াডাঙ্গা": "Chuadanga",
    "ঝিনাইদহ": "Jhenaidah", "মাগুরা": "Magura", "মাগুড়া": "Magura",
    "নড়াইল": "Narail",
    "যশোর": "Jashore", "সাতক্ষীরা": "Satkhira", "খুলনা": "Khulna",
    "বাগেরহাট": "Bagerhat",
    "বরিশাল": "Barishal", "পিরোজপুর": "Pirojpur", "ঝালকাঠি": "Jhalokathi",
    "পটুয়াখালী": "Patuakhali", "বরগুনা": "Barguna", "ভোলা": "Bhola",
    "সিলেট": "Sylhet", "মৌলভীবাজার": "Moulvibazar", "হবিগঞ্জ": "Habiganj",
    "সুনামগঞ্জ": "Sunamganj",
    "কুমিল্লা": "Cumilla", "চাঁদপুর": "Chandpur",
    "ব্রাহ্মণবাড়িয়া": "Brahmanbaria", "ব্রাক্ষণবাড়িয়া": "Brahmanbaria",
    "নরসিংদী": "Narsingdi",
    "চট্টগ্রাম": "Chattogram", "চট্রগ্রাম": "Chattogram",
    "কক্সবাজার": "Cox's Bazar", "ফেনী": "Feni",
    "নোয়াখালী": "Noakhali",
    "লক্ষ্মীপুর": "Lakshmipur", "লক্ষীপুর": "Lakshmipur",
    "রাঙ্গামাটি": "Rangamati", "খাগড়াছড়ি": "Khagrachhari",
    "বান্দরবান": "Bandarban", "বান্দারবান": "Bandarban",
}

DIVISION_MAP = {
    "Barishal": "Barishal", "Pirojpur": "Barishal", "Jhalokathi": "Barishal",
    "Patuakhali": "Barishal", "Barguna": "Barishal", "Bhola": "Barishal",
    "Chattogram": "Chattogram", "Cox's Bazar": "Chattogram", "Feni": "Chattogram",
    "Noakhali": "Chattogram", "Lakshmipur": "Chattogram", "Cumilla": "Chattogram",
    "Chandpur": "Chattogram", "Brahmanbaria": "Chattogram",
    "Rangamati": "Chattogram", "Khagrachhari": "Chattogram", "Bandarban": "Chattogram",
    "Dhaka": "Dhaka", "Gazipur": "Dhaka", "Narayanganj": "Dhaka",
    "Narsingdi": "Dhaka", "Manikganj": "Dhaka", "Munshiganj": "Dhaka",
    "Tangail": "Dhaka", "Kishoreganj": "Dhaka", "Faridpur": "Dhaka",
    "Gopalganj": "Dhaka", "Madaripur": "Dhaka", "Shariatpur": "Dhaka",
    "Rajbari": "Dhaka",
    "Khulna": "Khulna", "Bagerhat": "Khulna", "Satkhira": "Khulna",
    "Jashore": "Khulna", "Narail": "Khulna", "Magura": "Khulna",
    "Jhenaidah": "Khulna", "Kushtia": "Khulna", "Meherpur": "Khulna",
    "Chuadanga": "Khulna",
    "Mymensingh": "Mymensingh", "Netrakona": "Mymensingh",
    "Sherpur": "Mymensingh", "Jamalpur": "Mymensingh",
    "Rajshahi": "Rajshahi", "Chapainawabganj": "Rajshahi", "Naogaon": "Rajshahi",
    "Natore": "Rajshahi", "Bogura": "Rajshahi", "Joypurhat": "Rajshahi",
    "Pabna": "Rajshahi", "Sirajganj": "Rajshahi",
    "Rangpur": "Rangpur", "Panchagarh": "Rangpur", "Thakurgaon": "Rangpur",
    "Dinajpur": "Rangpur", "Nilphamari": "Rangpur", "Lalmonirhat": "Rangpur",
    "Gaibandha": "Rangpur", "Kurigram": "Rangpur",
    "Sylhet": "Sylhet", "Moulvibazar": "Sylhet", "Habiganj": "Sylhet",
    "Sunamganj": "Sylhet",
}

# EC official party name → normalize.py-compatible name
# (normalize_party will then map to the final canonical form)
EC_PARTY_TO_NORMALIZED = {
    "Bangladesh Nationalist Party - BNP": "BNP",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami",
    "Jatiyo Nagorik Party - NCP": "National Citizens Party - NCP",
    "Bangladesh Khelafat Majlis": "Bangladesh Khilafat Majlis",
    "Khelafat Majlis": "Khilafat Majlis",
    "Liberal Democratic Party - LDP": "Liberal Democratic Party - LDP",
    "Amar Bangladesh Party - AB Party": "Amar Bangladesh Party (AB Party)",
    "Bangladesh Development Party": "Bangladesh Development Party",
    "Bangladesh Nezame Islam Party": "Bangladesh Nezam e Islam Party",
    "Bangladesh Khilafat Andolan": "Bangladesh Khelafat Andolon",
    "Bangladesh Labour Party": "Bangladesh Labor Party",
    "Jatiya Ganatantrik Party - JAGPA": "JAGPA",
    "Jatiya Party": "Jatiya Party",
    "National Party - JP": "Jatiya Party",
    "Gonodhikar Parishad - GOP": "Gono Odhikar Porishad- GOP",
    "Islamic Andolan Bangladesh": "Islamic Andolon Bangladesh",
    "Bangladesh Islami Front": "Bangladesh Islamic Front",
    "Islamic Front Bangladesh": "Islamic Front Bangladesh",
    "Communist Party of Bangladesh": "Communist Party of Bangladesh",
    "Jatiya Samajtantrik Dal - JSD": "Jatiya Samajtantrik Dal (JSD)",
    "Jatiya Samajtantrik Dal - JASAD": "Jatiya Samajtantrik Dal (JSD Rab)",
    "Bangladesh Jatiyo Samajtantrik Dal - Jasod": "Bangladesh Jasod",
    "Nagorik Oikko": "Nagorik Oikko",
    "Gonoshonghoti Andolon": "Ganosamhati Andolon",
    "Biplabi Workers Party": "Bangladesher Biplobi Workers Party",
    "Bangladesh Nationalist Front - BNF": "Bangladesh Nationalist Front - BNF",
    "Bangladesh Supreme Party - BSP": "Bangladesh Supreme Party - BSP",
    "Zaker Party": "Zaker Party",
    "Ganotantri Party": "Ganatantri Party",
    "Bangladesh Muslim League": "Bangladesh Muslim League",
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League - BML",
    "Bangladesh Republican Party - BRP": "Bangladesh Republican Party - BRP",
    "Bangladesh Samajtantrik Dal - BASAD": "Bangladesh Samajtantrik Dal",
    "Bangladesh Samajtantrik Dal (Marxist)": "Bangladesher Samajtantrik Dal (Marxist)",
    "Insaniyat Biplob Bangladesh": "Insaniyat Biplob Bangladesh",
    "Jatiyatabadi Ganotantrik Andolon - NDM": "Nationalist Democratic Movement - NDM",
    "Bangladesh Minority Janta Party - BMJP": "Bangladesh Minority Janata Party - BMJP",
    "Bangladesh National Awami Party": "Bangladesh Nap",
    "Bangladesh National Awami Party - Bangladesh NAP": "Bangladesh Nap",
    "Bangladesh Jatiya Party - BJP": "Bangladesh National Party - BJP",
    "Bangladesh Jatiya Party": "Bangladesh National Party - BJP",
    "Jamiate Ulama-e-Islam Bangladesh": "Jamiat Ulama-e-Islam Bangladesh",
    "National Peoples Party - NPP": "National People's Party - NPP",
    "Bangladesh Kallyan Party": "Bangladesh Kalyan Party",
    "Bangladesh Shanskritik Muktijot (Muktijot)": "Bangladesh Sangskritik Muktijote",
    "Bangladesh Samadhikar Party - BEP": "Bangladesh Equal Rights Party",
    "Islami Oikyajote": "Islamic Oikkojot",
    "Gonoforum": "Gono Forum",
    "Gonofront": "Gono Front",
    "Jonotar Dol": "Janatar Dal",
    "Amjanatar Dol": "Amjanatar Dal",
    "Independent": "Independent",
}


def norm(s):
    return unicodedata.normalize("NFC", s.strip())


def safe_int(val):
    return int(val or 0)


def bn_to_en_seat(name_bn):
    parts = name_bn.rsplit("-", 1)
    if len(parts) == 2:
        district, num = norm(parts[0]), parts[1].translate(BN_DIGITS)
    else:
        district, num = norm(name_bn), "1"
    return f"{DISTRICT_MAP.get(district, district)} {num}"


def load_symbol_map():
    smap = {}
    with open(SYMBOLS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sym = norm(r["symbol_bn"])
            name = r["name_en"]
            if sym and sym not in ("-", "--", "---") and name and name != "-":
                smap[sym] = name
    if norm("গরুর গাড়ি") in smap:
        smap[norm("গরুর গাড়ী")] = smap[norm("গরুর গাড়ি")]
    if norm("রিকশা") in smap:
        smap[norm("রিক্সা")] = smap[norm("রিকশা")]
    return smap


def ec_to_normalized_party(ec_name):
    """Convert EC party name to normalize.py input, then normalize."""
    intermediate = EC_PARTY_TO_NORMALIZED.get(ec_name, ec_name)
    return normalize_party(intermediate)


def party_in_coalition(party_name, keywords):
    if not party_name:
        return False
    name_lc = party_name.lower()
    return any(kw in name_lc for kw in keywords)


def main():
    parser = argparse.ArgumentParser(description="Build seat_results.csv from official EC data.")
    parser.add_argument("--config", default="config/coalitions.json")
    parser.add_argument("--output", default="results/seat_results.csv")
    args = parser.parse_args()

    # Load coalitions
    with open(args.config, "r", encoding="utf-8") as f:
        coalitions = json.load(f)
    for meta in coalitions.values():
        meta["keywords"] = [kw.lower() for kw in meta.get("keywords", [])]

    symbol_map = load_symbol_map()
    constituencies = json.load(open(f"{RAW}/all_constituencies.json", encoding="utf-8"))

    all_party_names = set()
    seat_records = []

    for c in constituencies:
        cid = c["const_id"]
        seat_en = bn_to_en_seat(c["const_name"])
        seat_name = normalize_seat_name(seat_en)
        district = DISTRICT_MAP.get(norm(c["zilla_name"]), c["zilla_name"])
        division = DIVISION_MAP.get(district, "")

        center_file = f"{RAW}/centers_{cid}.json"
        if not os.path.exists(center_file):
            continue
        try:
            raw = json.load(open(center_file, encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            continue
        centers = raw.get("data", []) if isinstance(raw, dict) else raw

        total_voters = sum(safe_int(x.get("total_voter")) for x in centers)
        valid_votes = sum(safe_int(x.get("clear_total_vote")) for x in centers)
        rejected_votes = sum(safe_int(x.get("cancel_total_vote")) for x in centers)
        total_votes = valid_votes + rejected_votes

        # Aggregate candidate votes by symbol
        cand_symbols = defaultdict(int)
        for center in centers:
            vid = center.get("v_c_id")
            if not vid:
                continue
            detail_file = f"{RAW}/detail_{vid}.json"
            if not os.path.exists(detail_file):
                continue
            try:
                detail = json.load(open(detail_file, encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                continue
            if isinstance(detail, dict) and "error" in detail:
                continue
            for cand in detail.get("candidates", []):
                sym = cand.get("candidate_symbol", "")
                if sym:
                    cand_symbols[norm(sym)] += safe_int(cand.get("vote"))

        # Map symbols → EC party names → normalized party names
        party_votes = defaultdict(int)
        for sym, votes in cand_symbols.items():
            ec_party = symbol_map.get(sym, "Independent")
            party_name = ec_to_normalized_party(ec_party)
            party_votes[party_name] += votes
            all_party_names.add(party_name)

        # Coalition counts using keyword matching (same as scrape_votes.py)
        coalition_counts = {}
        ratios = {}
        for code, meta in coalitions.items():
            if meta.get("skip_coalition"):
                continue
            coalition_counts[code] = 0
            for party_name, votes in party_votes.items():
                if party_in_coalition(party_name, meta["keywords"]):
                    coalition_counts[code] += votes
            ratios[code] = (coalition_counts[code] / total_votes) if total_votes > 0 else 0.0

        # Top 3 candidates by votes
        sorted_parties = sorted(party_votes.items(), key=lambda x: -x[1])
        top3 = sorted_parties[:3]
        top_three_candidates = ", ".join(
            f"{p} ({v / total_votes * 100:.1f}%)" for p, v in top3 if v > 0 and total_votes > 0
        )
        top_three_parties = ", ".join(
            f"{p} ({v / total_votes * 100:.1f}%)" for p, v in top3 if v > 0 and total_votes > 0
        )

        seat_number = seat_name.rsplit(" ", 1)[-1] if " " in seat_name else "1"

        # Turnout
        turnout_ratio = (total_votes / total_voters) if total_voters > 0 else 0.0

        # Victory margin (top1 - top2) / total_votes
        sorted_vote_counts = sorted(party_votes.values(), reverse=True)
        top1_v = sorted_vote_counts[0] if len(sorted_vote_counts) > 0 else 0
        top2_v = sorted_vote_counts[1] if len(sorted_vote_counts) > 1 else 0
        margin = top1_v - top2_v
        margin_ratio = (margin / total_votes) if total_votes > 0 else 0.0

        # Winner party
        winner_party = sorted_parties[0][0] if sorted_parties else ""

        record = {
            "seat_id": cid,
            "seat_number": seat_number,
            "seat_name": seat_name,
            "division": division,
            "district": district,
            "upazila": "",
            "voting_finalized": None,
            "total_votes": total_votes,
            "total_voters": total_voters,
            "top_three_candidates": top_three_candidates,
            "top_three": top_three_parties,
            "turnout_votes": total_votes,
            "turnout_ratio": turnout_ratio,
            "victory_margin_votes": margin,
            "victory_margin_ratio": margin_ratio,
            "winner_party": winner_party,
        }
        for code in coalitions:
            if coalitions[code].get("skip_coalition"):
                continue
            record[f"{code}_votes"] = coalition_counts[code]
            record[f"{code}_ratio"] = ratios[code]
        record["_party_votes"] = dict(party_votes)
        seat_records.append(record)

    # Collect all party columns sorted alphabetically
    all_party_names = sorted(all_party_names)

    # Add per-party columns and remove internal field
    for record in seat_records:
        pv = record.pop("_party_votes")
        for p in all_party_names:
            record[p] = pv.get(p)  # None if party not present in this seat

    # Sort by seat name
    seat_records.sort(key=lambda r: r["seat_name"])

    # Write CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fields = list(seat_records[0].keys())
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(seat_records)

    print(f"Wrote {len(seat_records)} seats to {args.output}")

    # Summary
    total = sum(r["total_votes"] for r in seat_records)
    for code in coalitions:
        cv = sum(r[f"{code}_votes"] for r in seat_records)
        print(f"  {code}: {cv:,} ({cv/total*100:.1f}%)")


if __name__ == "__main__":
    main()
