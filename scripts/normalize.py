import re

PARTY_NAME_MAP = {
    "BNP": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "Independent": "Independent Candidate (Independent)",
    "National Citizens Party - NCP": "National Citizen Party (NCP)",
    "National Citizens Party (NCP)": "National Citizen Party (NCP)",
    "Islamic Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Bangladesh Islamic Front": "Bangladesh Islami Front (BIF)",
    "Bangladesh Islami Front": "Bangladesh Islami Front (BIF)",
    "Islamic Front Bangladesh": "Bangladesh Islami Front (BIF)",
    "Islamic Front Bangladesh (IFB)": "Bangladesh Islami Front (BIF)",
    "Islamic Front Bangladesh - IFB": "Bangladesh Islami Front (BIF)",
    "Bangladesh Khilafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Khilafat Majlis": "Khelafat Majlis",
    "Liberal Democratic Party - LDP": "Bangladesh Liberal Democratic Party (LDP)",
    "Liberal Democratic Party (LDP)": "Bangladesh Liberal Democratic Party (LDP)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Jatiya Party - JAPA": "Jatiya Party (JaPa)",
    "Gono Odhikar Parishad": "Gono Odhikar Parishad (GOP)",
    "Gono Odhikar Porishad- GOP": "Gono Odhikar Parishad (GOP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "My Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Bangladesh Development Party - BDP": "Bangladesh Development Party (BDP)",
    "Bangladesh Development Party": "Bangladesh Development Party (BDP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Bangladesh Jatiya Party (Matin)": "Bangladesh Jatiya Party (BJP)",
    "Jamiat Ulama-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Jamiat Ulema-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Gono Forum": "Gono Forum (GF)",
    "Gano Forum": "Gono Forum (GF)",
    "Bangladesh Supreme Party - BSP": "Bangladesh Supreme Party (BSP)",
    "Zaker Party": "Zaker Party (ZP)",
    "Bangladesh Jasod": "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)",
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Jatiya Samajtantrik Dal (JSD Rab)": "Jatiya Samajtantrik Dal-JASAD",
    "Ganosamhati Andolon": "Ganosanhati Andolan (GSA)",
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League (BML)",
    "Bangladesh Muslim League": "Bangladesh Muslim League (BML)",
    "Bangladesh Nezam e Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Bangladesh Nezam Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Bangladesh Nezam-e-Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Nagorik Oikya": "Nagorik Oikya (NO)",
    "Nagorik Oikko": "Nagorik Oikya (NO)",
    "Bangladesh Republican Party - BRP": "Bangladesh Republican Party (BRP)",
    "Communist Party of Bangladesh": "Communist Party of Bangladesh (CPB)",
    "Bangladesh Samajtantrik Dal": "Bangladesh Samajtantrik Dal (Basad)",
    "Bangladesh Socialist Party (BASAD)": "Bangladesh Samajtantrik Dal (Basad)",
    "Bangladesher Samajtantrik Dal (BSD)": "Bangladesh Samajtantrik Dal (Basad)",
    "Insaniat Biplob Bangladesh - Insaniat Biplob": "Insaniyat Biplob Bangladesh (IBB)",
    "Insaniyat Biplob Bangladesh": "Insaniyat Biplob Bangladesh (IBB)",
    "Nationalist Democratic Movement - NDM": "Nationalist Democratic Movement (NDM)",
    "Nationalist Democratic Movement": "Nationalist Democratic Movement (NDM)",
    "Ganatantri Party": "Ganatantri Party (GP)",
    "Democratic Party": "Ganatantri Party (GP)",
    "Janatar Dal": "Janotar Dol",
    "Janata Party": "Janotar Dol",
    "Amjanatar Dal": "Amjanatar Dol",
    "Am Janata Party": "Amjanatar Dol",
    "Bangladesher Biplobi Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Revolutionary Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Revolutionary Workers Party of Bangladesh": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Khelafat Andolon": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Sangskritik Muktijote": "Bangladesh Sangskritik Muktijote (BSM)",
    "Bangladesh Cultural Liberation Front (Muktijot)": "Bangladesh Sangskritik Muktijote (BSM)",
    "Bangladesher Samajtantrik Dal (Marxist)": "Socialist Party of Bangladesh (Marxist) (SPB-M)",
    "Bangladesh Socialist Party (Marxist)": "Socialist Party of Bangladesh (Marxist) (SPB-M)",
    "Bangladesh Nationalist Front - BNF": "Bangladesh Nationalist Front (BNF)",
    "Bangladesh Kalyan Party": "Bangladesh Kallyan Party (BKP)",
    "Bangladesh Labor Party": "Bangladesh Labour Party",
    "Bangladesh Minority Janata Party - BMJP": "Bangladesh Minority Janata Party (BMJP)",
    "Bangladesh Minority People's Party (BMJP)": "Bangladesh Minority Janata Party (BMJP)",
    "Bangladesh Nap": "Bangladesh National Awami Party–Bangladesh NAP (BNAP)",
    "Bangladesh Gonofront": "Gono Front (GF)",
    "Gono Front": "Gono Front (GF)",
    "Bangladesh Equal Rights Party": "Bangladesh Somo Odhikar Party (BEP)",
    "Bangladesh Samo Odhikar Party (BEP)": "Bangladesh Somo Odhikar Party (BEP)",
    "Islamic Oikkojot": "Islami Oikya Jote (IOJ)",
    "National People's Party - NPP": "National People's Party (NPP)",
    "National Democratic Party - JDP": "Jatiya Ganatantrik Party (JAGPA)",
    "JAGPA": "Jatiya Ganatantrik Party (JAGPA)",
}

LOCATION_ALIASES = {
    "bogra": "Bogura",
    "comilla": "Cumilla",
    "jessore": "Jashore",
    "jhalakathi": "Jhalokathi",
    "jhalokati": "Jhalokathi",
    "netrokona": "Netrakona",
    "chapai nawabganj": "Chapainawabganj",
    "chapai nababganj": "Chapainawabganj",
    "chapainawabganj": "Chapainawabganj",
    "nawabganj": "Chapainawabganj",
    "coxs bazar": "Cox's Bazar",
    "cox's bazar": "Cox's Bazar",
    "cox?s bazar": "Cox's Bazar",
    "barisal": "Barishal",
    "chittagong": "Chattogram",
    "brahmanbaria": "Brahmanbaria",
    "habiganj": "Habiganj",
    "habjganj": "Habiganj",
    "maulvibazar": "Moulvibazar",
    "moulvibazar": "Moulvibazar",
    "sunamganj": "Sunamganj",
    "sylhet": "Sylhet",
    "bandarban": "Bandarban",
    "parbatya bandarban": "Bandarban",
    "khagrachhari": "Khagrachhari",
    "khagrachari": "Khagrachhari",
    "parbatya khagrachari": "Khagrachhari",
    "parbatya khagrachhari": "Khagrachhari",
    "rangamati": "Rangamati",
    "parbatya rangamati": "Rangamati",
    "patuakhali": "Patuakhali",
    "bhola": "Bhola",
    "pirojpur": "Pirojpur",
    "barguna": "Barguna",
    "chuadanga": "Chuadanga",
    "kushtia": "Kushtia",
    "meherpur": "Meherpur",
    "khulna": "Khulna",
    "bagerhal": "Bagerhat",
    "bagerhat": "Bagerhat",
    "satkhira": "Satkhira",
    "jhenaidah": "Jhenaidah",
    "magura": "Magura",
    "narail": "Narail",
    "faridpur": "Faridpur",
    "rajbari": "Rajbari",
    "gopalganj": "Gopalganj",
    "madaripur": "Madaripur",
    "shariatpur": "Shariatpur",
    "dhaka": "Dhaka",
    "gazipur": "Gazipur",
    "narsingdi": "Narsingdi",
    "narayanganj": "Narayanganj",
    "munshiganj": "Munshiganj",
    "manikganj": "Manikganj",
    "tangail": "Tangail",
    "kishoreganj": "Kishoreganj",
    "mymensingh": "Mymensingh",
    "netrakona": "Netrakona",
    "sherpur": "Sherpur",
    "jamalpur": "Jamalpur",
    "rajshahi": "Rajshahi",
    "natore": "Natore",
    "naogaon": "Naogaon",
    "pabna": "Pabna",
    "sirajganj": "Sirajganj",
    "rangpur": "Rangpur",
    "dinajpur": "Dinajpur",
    "kurigram": "Kurigram",
    "gaibandha": "Gaibandha",
    "lalmonirhat": "Lalmonirhat",
    "nilphamari": "Nilphamari",
    "nilphamhari": "Nilphamari",
    "panchagarh": "Panchagarh",
    "thakurgaon": "Thakurgaon",
}

# Canonical party equivalences — merges parties that are the same under different names
PARTY_CANONICAL = {
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Jatiya Samajtantrik Dal-JASAD": "Jatiya Samajtantrik Dal (JSD)",
    "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)": "Jatiya Samajtantrik Dal (JSD)",
    "Bangladesh Khelafat Majlish (BKM)": "Khelafat Majlis",
    "Khelafat Majlis": "Khelafat Majlis",
}


def normalize_party(name: str) -> str:
    """Normalize party name to common convention, then canonicalize."""
    if not name or not str(name).strip():
        return "Unknown"
    name = str(name).strip()
    name = name.replace("\u2018", "'").replace("\u2019", "'")
    name = PARTY_NAME_MAP.get(name, name)
    name = PARTY_CANONICAL.get(name, name)
    return name


def normalize_location_name(name: str) -> str:
    """Normalize division or district name."""
    if not name:
        return ""
    name = str(name).strip()
    return LOCATION_ALIASES.get(name.lower(), name.title())


def normalize_seat_name(name: str) -> str:
    """Normalize seat name to a common format e.g. 'Bogura 1' instead of 'bogra-1'."""
    if not name:
        return ""
    name = str(name).strip()
    name = re.sub(r"[-–—]", " ", name)
    name = re.sub(r"[\?\''']", "'", name)
    name = re.sub(r"\s+", " ", name)

    # Handle Parbatya prefixes which often miss '-1'
    if name.lower().startswith("parbatya ") and not re.search(r'\d+$', name):
        name = name[9:].strip() + " 1"

    parts = name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return f"{normalize_location_name(parts[0])} {parts[1]}"

    # Single-constituency districts (e.g., "Bandarban" → "Bandarban 1")
    normalized_loc = normalize_location_name(name)
    if normalized_loc in {"Bandarban", "Rangamati", "Khagrachhari"}:
        return f"{normalized_loc} 1"

    return normalized_loc


# Spelling variations for candidate name normalization (pattern, replacement)
_NAME_SPELLING_FIXES = [
    (r"Rahaman", "Rahman"),
    (r"Hossan|Hossen|Hossaion", "Hossain"),
    (r"Chowdury", "Chowdhury"),
    (r"Miah", "Mia"),
    (r"Rumeen|Rumin", "Rumin"),
    (r"Mollah|Molla", "Molla"),
    (r"Siddique|Siddiqui|Siddiqie", "Siddiqui"),
    (r"Lutfor|Lutfar", "Lutfar"),
    (r"Tanbir|Tanvir", "Tanvir"),
    (r"Uddaula|Uddoula", "Uddoula"),
    (r"Sobur|Sabur", "Sabur"),
    (r"Eliyas|Elias|Ilias", "Elias"),
    (r"Nurunnabi|Noorannabi", "Nurunnabi"),
    (r"Yeasir|Yasir", "Yasir"),
    (r"Salahuddin|Salauddin", "Salahuddin"),
    (r"Minhaj|Minhaz", "Minhaz"),
    (r"Minhajul|Minhazul", "Minhazul"),
    (r"Ariful|Arif Ul", "Ariful"),
    (r"Sayed|Sayeed", "Sayed"),
    (r"Noor|Nur|Noor", "Nur"),
    (r"Mohhammad", "Mohammad"),   # double h typo
    (r"Uddin|Udeen|Uddeen", "Uddin"),
    (r"Akhter|Akhtar|Akter", "Akter"),
    (r"Howladar|Howlader|Haldar", "Howlader"),
    (r"Akand|Akanda", "Akand"),
    (r"Rouf|Rauf", "Rauf"),
    (r"Riyad|Riad", "Riad"),
    (r"Bidyut|Biddut", "Bidyut"),
    (r"Azizur|Azizar", "Azizur"),
    (r"Mosammat", "Mst."),        # Mosammat = Mst. (female prefix)
    (r"Khudi|Khude", "Khude"),
    (r"Mosaddiqul|Mosaddiqual", "Mosaddiqul"),
    (r"Gaus|Gouch|Gouse|Gous", "Gaus"),
    (r"Delowar|Deluare|Delwar", "Delowar"),
    (r"Selim|Salim", "Selim"),
]


# Bangla script → Roman phonetic transliteration
# Vowels
_BANGLA_MAP = {
    # Independent vowels
    'অ': 'o', 'আ': 'a', 'ই': 'i', 'ঈ': 'i', 'উ': 'u', 'ঊ': 'u',
    'ঋ': 'ri', 'এ': 'e', 'ঐ': 'oi', 'ও': 'o', 'ঔ': 'ou',
    # Vowel signs (matras)
    'া': 'a', 'ি': 'i', 'ী': 'i', 'ু': 'u', 'ূ': 'u',
    'ৃ': 'ri', 'ে': 'e', 'ৈ': 'oi', 'ো': 'o', 'ৌ': 'ou',
    # Consonants
    'ক': 'k', 'খ': 'kh', 'গ': 'g', 'ঘ': 'gh', 'ঙ': 'ng',
    'চ': 'ch', 'ছ': 'chh', 'জ': 'j', 'ঝ': 'jh', 'ঞ': 'n',
    'ট': 't', 'ঠ': 'th', 'ড': 'd', 'ঢ': 'dh', 'ণ': 'n',
    'ত': 't', 'থ': 'th', 'দ': 'd', 'ধ': 'dh', 'ন': 'n',
    'প': 'p', 'ফ': 'f', 'ব': 'b', 'ভ': 'bh', 'ম': 'm',
    'য': 'j', 'র': 'r', 'ল': 'l', 'শ': 'sh', 'ষ': 'sh', 'স': 's',
    'হ': 'h', 'ড়': 'r', 'ঢ়': 'rh', 'য়': 'y', 'ৎ': 't',
    # Hasanta (virama) — suppresses inherent vowel
    '্': '',
    # Anusvara, chandrabindu, visarga
    'ং': 'ng', 'ঁ': 'n', 'ঃ': 'h',
    # Bangla numerals
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
}

# Two-char sequences that need special handling (conjuncts with hasanta)
_BANGLA_CONJUNCTS = {
    'ক্ষ': 'kkh', 'জ্ঞ': 'gn', 'ঞ্চ': 'nch', 'ঞ্জ': 'nj',
    'ঙ্ক': 'nk', 'ঙ্গ': 'ngg', 'ণ্ড': 'nd', 'ন্দ': 'nd',
    'ন্ত': 'nt', 'ম্ব': 'mb', 'ম্প': 'mp',
}


def transliterate_bangla(text: str) -> str:
    """Transliterate Bangla script to Roman phonetic spelling."""
    if not re.search(r'[\u0980-\u09FF]', text):
        return text  # no Bangla chars

    # Parse into tokens first, then decide inherent vowels
    tokens = []  # list of (roman_str, is_consonant)
    i = 0
    while i < len(text):
        # Try 3-char conjuncts (consonant + hasanta + consonant)
        if i + 2 < len(text) and text[i+1] == '্':
            trigram = text[i:i+3]
            if trigram in _BANGLA_CONJUNCTS:
                tokens.append((_BANGLA_CONJUNCTS[trigram], True))
                i += 3
                continue

        # Try 2-char sequences
        if i + 1 < len(text):
            digram = text[i:i+2]
            if digram in _BANGLA_MAP:
                tokens.append((_BANGLA_MAP[digram], False))
                i += 2
                continue
            if digram in _BANGLA_CONJUNCTS:
                tokens.append((_BANGLA_CONJUNCTS[digram], True))
                i += 2
                continue

        ch = text[i]
        if ch in _BANGLA_MAP:
            is_consonant = 'ক' <= ch <= 'হ' or ch in ('ড়', 'ঢ়', 'য়')
            next_is_vowel_sign = (i + 1 < len(text) and text[i+1] in 'ািীুূৃেৈোৌ্')
            tokens.append((_BANGLA_MAP[ch], is_consonant and not next_is_vowel_sign))
        else:
            tokens.append((ch, False))
        i += 1

    # Build result: add inherent 'o' after consonants, but NOT at word-end
    result = []
    for idx, (roman, needs_inherent) in enumerate(tokens):
        result.append(roman)
        if needs_inherent:
            # Add inherent 'o' between consonants, but not at word-end
            # (Bangla final consonants are typically silent/no vowel)
            next_is_boundary = (idx + 1 >= len(tokens) or tokens[idx + 1][0] in (' ', '', '-'))
            # Exception: conjuncts at word-end still need the 'o' for readability
            next_is_consonant = (idx + 1 < len(tokens) and tokens[idx + 1][1])
            if not next_is_boundary or next_is_consonant:
                result.append('o')

    return ''.join(result)


def normalize_candidate_name(name: str) -> str:
    """Normalize candidate name, whitespace, prefixes etc."""
    if not name:
        return ""
    name = str(name).strip()

    # Transliterate Bangla script to Roman
    name = transliterate_bangla(name)
    name = re.sub(r",+$", "", name)
    name = re.sub(r"\(.*?\)", "", name)         # Remove nicknames in parens
    name = re.sub(r"\s*-\s*", " ", name)        # Hyphens to spaces

    # Normalize common prefixes
    name = re.sub(r"\b(Khandaker|Khandker|Khandakar)\b", "Khandaker", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Md|Mohammad|Muhammed|Muhammad|Mahammad)\b\.?\s*", "Md. ", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Mst|Mosa|Ms)\b\.?\s*", "Mst. ", name, flags=re.IGNORECASE)
    name = re.sub(r"\bMr\b\.?\s*", "", name, flags=re.IGNORECASE)

    # Strip titles
    name = re.sub(r"\b(Dr|Advocate|Engr|Engineer|Barrister|Professor|Moulana|Maulana|Hazi|Haji|Alhaj|Al Haj|Al-Haj)\b\.?\s*", "", name, flags=re.IGNORECASE)

    # Single-letter initials
    name = re.sub(r"\b([A-Z])\b\.?\s*", r"\1. ", name)

    # Apply spelling fixes
    for pattern, repl in _NAME_SPELLING_FIXES:
        name = re.sub(rf"\b({pattern})\b", repl, name, flags=re.IGNORECASE)

    name = re.sub(r"\s+", " ", name).strip()
    return name.title()
