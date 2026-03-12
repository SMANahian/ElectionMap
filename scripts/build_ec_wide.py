"""
build_ec_wide.py — Build constituency-wide CSV from EC official data.

Reads: official_result/raw_data/ (cached JSON from scrape_ec.py)
       official_result/ecs_party_symbols.csv (from scrape_ecs_parties.py)
Output: official_result/ec_constituency_wide.csv

Each row = one constituency with voter stats, turnout, alliance totals,
per-party votes, winner/runner-up, and margin.
"""

import csv, json, os, unicodedata
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "official_result", "raw_data")
SYMBOLS_CSV = os.path.join(BASE, "official_result", "ecs_party_symbols.csv")
OUTPUT = os.path.join(BASE, "official_result", "ec_constituency_wide.csv")

BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bangla district -> English
DISTRICT_MAP = {
    "পঞ্চগড়": "Panchagarh", "ঠাকুরগাঁও": "Thakurgaon", "দিনাজপুর": "Dinajpur",
    "নীলফামারী": "Nilphamari", "লালমনিরহাট": "Lalmonirhat", "রংপুর": "Rangpur",
    "গাইবান্ধা": "Gaibandha", "কুড়িগ্রাম": "Kurigram", "শেরপুর": "Sherpur",
    "জামালপুর": "Jamalpur", "ময়মনসিংহ": "Mymensingh", "নেত্রকোণা": "Netrakona",
    "কিশোরগঞ্জ": "Kishoreganj", "বগুড়া": "Bogura", "জয়পুরহাট": "Joypurhat",
    "নওগাঁ": "Naogaon", "চাঁপাইনবাবগঞ্জ": "Chapainawabganj", "রাজশাহী": "Rajshahi",
    "নাটোর": "Natore", "পাবনা": "Pabna", "সিরাজগঞ্জ": "Sirajganj",
    "টাঙ্গাইল": "Tangail", "টাংগাইল": "Tangail",
    "গাজীপুর": "Gazipur", "ঢাকা": "Dhaka",
    "মানিকগঞ্জ": "Manikganj", "মুন্সীগঞ্জ": "Munshiganj", "মুন্সিগঞ্জ": "Munshiganj",
    "নারায়ণগঞ্জ": "Narayanganj",
    "ফরিদপুর": "Faridpur", "গোপালগঞ্জ": "Gopalganj",
    "মাদারীপুর": "Madaripur", "মাদারিপুর": "Madaripur",
    "শরীয়তপুর": "Shariatpur", "রাজবাড়ী": "Rajbari",
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

# Alliance groupings (from Wikipedia: 2026 Bangladeshi general election)
# Using EC official party names from ecs_party_symbols.csv

BNP_PLUS = {
    "Bangladesh Nationalist Party - BNP",
    "Jamiate Ulama-e-Islam Bangladesh",        # JUIB
    "Gonodhikar Parishad - GOP",               # GOP
    "Bangladesh Jatiya Party - BJP",
    "Gonoshonghoti Andolon",                   # Ganosanhati Andolan
    "Biplabi Workers Party",                   # RWPB
    "National Peoples Party - NPP",
    "Jatiyatabadi Ganotantrik Andolon - NDM",
}

ELEVEN_PARTIES = {
    "Bangladesh Jamaat-e-Islami",
    "Jatiyo Nagorik Party - NCP",
    "Bangladesh Khelafat Majlis",
    "Khelafat Majlis",
    "Liberal Democratic Party - LDP",
    "Amar Bangladesh Party - AB Party",
    "Bangladesh Development Party",            # BDP
    "Bangladesh Nezame Islam Party",
    "Bangladesh Khilafat Andolan",             # BKA
    "Bangladesh Labour Party",
    "Jatiya Ganatantrik Party - JAGPA",
}

DUF = {
    "Communist Party of Bangladesh",            # CPB
    "Bangladesh Samajtantrik Dal - BASAD",      # SPB/BASAD
    "Bangladesh Samajtantrik Dal (Marxist)",    # SPB(Marxist)
    "Bangladesh Jatiyo Samajtantrik Dal - Jasod",  # BJSD/Jasod
    "Gonofront",                                # Gono Front
}

NDF = {
    "Jatiya Party",                             # JP (Ershad)
    "National Party - JP",                      # JP (Manju)
    "Bangladesh Muslim League",
    "Bangladesh Shanskritik Muktijot (Muktijot)",  # BSM/Muktijot
}

GREATER_SUNNI = {
    "Bangladesh Islami Front",
    "Islamic Front Bangladesh",
    "Bangladesh Supreme Party - BSP",
}


def norm(s):
    return unicodedata.normalize("NFC", s.strip())


def safe_int(val):
    return int(val or 0)


def bn_to_en_seat(name_bn):
    """Convert Bangla constituency name like পঞ্চগড়-১ to Panchagarh 1."""
    parts = name_bn.rsplit("-", 1)
    if len(parts) == 2:
        district, num = norm(parts[0]), parts[1].translate(BN_DIGITS)
    else:
        district, num = norm(name_bn), "1"
    return f"{DISTRICT_MAP.get(district, district)} {num}"


def load_symbol_map():
    """Load symbol_bn -> party_en mapping from ECS data."""
    smap = {}
    with open(SYMBOLS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            sym = norm(r["symbol_bn"])
            name = r["name_en"]
            if sym and sym not in ("-", "--", "---") and name and name != "-":
                smap[sym] = name
    # Spelling variants in EC data
    if norm("গরুর গাড়ি") in smap:
        smap[norm("গরুর গাড়ী")] = smap[norm("গরুর গাড়ি")]
    if norm("রিকশা") in smap:
        smap[norm("রিক্সা")] = smap[norm("রিকশা")]
    return smap


def classify(party):
    if party in BNP_PLUS:
        return "bnp_plus"
    if party in ELEVEN_PARTIES:
        return "eleven_parties"
    if party in DUF:
        return "duf"
    if party in NDF:
        return "ndf"
    if party in GREATER_SUNNI:
        return "greater_sunni"
    if party == "Independent":
        return "independent"
    return "other"


def main():
    symbol_map = load_symbol_map()
    constituencies = json.load(open(f"{RAW}/all_constituencies.json", encoding="utf-8"))

    # Collect all party names across all constituencies for column ordering
    all_parties = set()
    seat_data = {}

    for c in constituencies:
        cid = c["const_id"]
        seat_en = bn_to_en_seat(c["const_name"])

        # --- Center metadata ---
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
        absent_voters = sum(safe_int(x.get("absent_voter")) for x in centers)
        total_cast = valid_votes + rejected_votes

        # --- Candidate votes from detail files ---
        candidates = defaultdict(lambda: {"symbol": "", "votes": 0})
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
                name = cand.get("candidate_name", "")
                if name:
                    candidates[name]["symbol"] = cand.get("candidate_symbol", "")
                    candidates[name]["votes"] += safe_int(cand.get("vote"))

        # Map candidates to parties
        party_votes = defaultdict(int)
        cand_list = []
        for name, data in candidates.items():
            sym = norm(data["symbol"])
            party = symbol_map.get(sym, "Independent")
            party_votes[party] += data["votes"]
            all_parties.add(party)
            cand_list.append((name, party, data["votes"]))

        # Sort by votes descending
        cand_list.sort(key=lambda x: -x[2])

        # Alliance totals
        alliance = {"bnp_plus": 0, "eleven_parties": 0, "duf": 0, "ndf": 0,
                     "greater_sunni": 0, "independent": 0, "other": 0}
        for party, votes in party_votes.items():
            alliance[classify(party)] += votes

        # Winner / runner-up / 3rd place
        winner = cand_list[0] if cand_list else ("", "", 0)
        runner_up = cand_list[1] if len(cand_list) > 1 else ("", "", 0)
        margin = winner[2] - runner_up[2] if len(cand_list) > 1 else winner[2]
        margin_pct = round(margin / valid_votes * 100, 1) if valid_votes else 0

        # Competitiveness
        if margin_pct >= 20:
            competitiveness = "safe"
        elif margin_pct >= 10:
            competitiveness = "competitive"
        elif margin_pct >= 5:
            competitiveness = "marginal"
        else:
            competitiveness = "very_close"

        # Effective number of candidates (Laakso-Taagepera index)
        # ENP = 1 / sum(p_i^2) where p_i = vote share of candidate i
        if valid_votes:
            shares_sq = sum((c[2] / valid_votes) ** 2 for c in cand_list if c[2] > 0)
            enc = round(1 / shares_sq, 2) if shares_sq else 0
        else:
            enc = 0

        # Top 3 party votes (BNP, Jamaat, NCP)
        bnp_v = party_votes.get("Bangladesh Nationalist Party - BNP", 0)
        jamaat_v = party_votes.get("Bangladesh Jamaat-e-Islami", 0)
        ncp_v = party_votes.get("Jatiyo Nagorik Party - NCP", 0)

        seat_data[cid] = {
            "constituency_id": cid,
            "seat_name": seat_en,
            "seat_name_bn": c["const_name"],
            "district_bn": c["zilla_name"],
            # Voter stats
            "total_voters": total_voters,
            "total_votes_cast": total_cast,
            "valid_votes": valid_votes,
            "rejected_votes": rejected_votes,
            "absent_voters": absent_voters,
            # Turnout & rates
            "turnout_pct": round(total_cast / total_voters * 100, 1) if total_voters else 0,
            "rejection_pct": round(rejected_votes / total_cast * 100, 2) if total_cast else 0,
            "absence_pct": round(absent_voters / total_voters * 100, 1) if total_voters else 0,
            # Center stats
            "total_centers": len(centers),
            "total_candidates": len(candidates),
            "avg_voters_per_center": round(total_voters / len(centers)) if centers else 0,
            # Alliance totals
            "bnp_plus_votes": alliance["bnp_plus"],
            "bnp_plus_pct": round(alliance["bnp_plus"] / valid_votes * 100, 1) if valid_votes else 0,
            "eleven_parties_votes": alliance["eleven_parties"],
            "eleven_parties_pct": round(alliance["eleven_parties"] / valid_votes * 100, 1) if valid_votes else 0,
            "duf_votes": alliance["duf"],
            "duf_pct": round(alliance["duf"] / valid_votes * 100, 1) if valid_votes else 0,
            "ndf_votes": alliance["ndf"],
            "ndf_pct": round(alliance["ndf"] / valid_votes * 100, 1) if valid_votes else 0,
            "greater_sunni_votes": alliance["greater_sunni"],
            "greater_sunni_pct": round(alliance["greater_sunni"] / valid_votes * 100, 1) if valid_votes else 0,
            "independent_votes": alliance["independent"],
            "independent_pct": round(alliance["independent"] / valid_votes * 100, 1) if valid_votes else 0,
            "other_party_votes": alliance["other"],
            "other_party_pct": round(alliance["other"] / valid_votes * 100, 1) if valid_votes else 0,
            # Top 3 parties
            "bnp_votes": bnp_v,
            "bnp_pct": round(bnp_v / valid_votes * 100, 1) if valid_votes else 0,
            "jamaat_votes": jamaat_v,
            "jamaat_pct": round(jamaat_v / valid_votes * 100, 1) if valid_votes else 0,
            "ncp_votes": ncp_v,
            "ncp_pct": round(ncp_v / valid_votes * 100, 1) if valid_votes else 0,
            # Winner info
            "winner_name": winner[0],
            "winner_party": winner[1],
            "winner_votes": winner[2],
            "winner_pct": round(winner[2] / valid_votes * 100, 1) if valid_votes else 0,
            "runner_up_name": runner_up[0],
            "runner_up_party": runner_up[1],
            "runner_up_votes": runner_up[2],
            "margin": margin,
            "margin_pct": margin_pct,
            # Competitiveness & fragmentation
            "competitiveness": competitiveness,
            "effective_num_candidates": enc,
            # Per-party votes (filled below)
            "_party_votes": party_votes,
        }

    # Determine party columns sorted by total votes nationally
    party_totals = defaultdict(int)
    for s in seat_data.values():
        for p, v in s["_party_votes"].items():
            party_totals[p] += v
    # Exclude Independent from party columns (already has its own column)
    party_cols = [p for p, _ in sorted(party_totals.items(), key=lambda x: -x[1])
                  if p != "Independent"]

    # Build CSV
    base_fields = [
        "constituency_id", "seat_name", "seat_name_bn", "district_bn",
        "total_voters", "total_votes_cast", "valid_votes", "rejected_votes", "absent_voters",
        "turnout_pct", "rejection_pct", "absence_pct",
        "total_centers", "total_candidates", "avg_voters_per_center",
        "bnp_plus_votes", "bnp_plus_pct",
        "eleven_parties_votes", "eleven_parties_pct",
        "duf_votes", "duf_pct", "ndf_votes", "ndf_pct",
        "greater_sunni_votes", "greater_sunni_pct",
        "independent_votes", "independent_pct",
        "other_party_votes", "other_party_pct",
        "bnp_votes", "bnp_pct", "jamaat_votes", "jamaat_pct", "ncp_votes", "ncp_pct",
        "winner_name", "winner_party", "winner_votes", "winner_pct",
        "runner_up_name", "runner_up_party", "runner_up_votes",
        "margin", "margin_pct",
        "competitiveness", "effective_num_candidates",
    ]
    fields = base_fields + party_cols

    rows = []
    for cid in sorted(seat_data, key=int):
        s = seat_data[cid]
        row = {f: s.get(f, "") for f in base_fields}
        for p in party_cols:
            row[p] = s["_party_votes"].get(p, "")
        rows.append(row)

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    # Summary
    total_voters = sum(s["total_voters"] for s in seat_data.values())
    total_cast = sum(s["total_votes_cast"] for s in seat_data.values())
    total_valid = sum(s["valid_votes"] for s in seat_data.values())
    print(f"Wrote {len(rows)} constituencies to {OUTPUT}")
    print(f"  {len(party_cols)} party columns + {len(base_fields)} stat columns")
    print(f"\n  Total voters:      {total_voters:>12,}")
    print(f"  Total votes cast:  {total_cast:>12,}")
    print(f"  Valid votes:       {total_valid:>12,}")
    print(f"  Turnout:           {total_cast/total_voters*100:.1f}%")
    for label, key in [("BNP+", "bnp_plus_votes"), ("11 Parties", "eleven_parties_votes"),
                       ("DUF", "duf_votes"), ("NDF", "ndf_votes"),
                       ("Greater Sunni", "greater_sunni_votes"),
                       ("Independent", "independent_votes"), ("Other", "other_party_votes")]:
        t = sum(s[key] for s in seat_data.values())
        print(f"  {label:<16}   {t:>12,} ({t/total_valid*100:.1f}%)")
    print(f"\n  Winner parties:")
    from collections import Counter
    winners = Counter(s["winner_party"] for s in seat_data.values())
    for p, c in winners.most_common():
        print(f"    {c:>3} seats  {p}")


if __name__ == "__main__":
    main()
