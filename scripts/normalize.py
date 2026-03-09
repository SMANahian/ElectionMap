import re

PARTY_NAME_MAP = {
    "BNP": "Bangladesh Nationalist Party (BNP)",
    "Bangladesh Jamaat-e-Islami": "Bangladesh Jamaat-e-Islami (Jamaat)",
    "Independent": "Independent Candidate (Independent)",
    "National Citizens Party - NCP": "National Citizen Party (NCP)",
    "Islamic Andolon Bangladesh": "Islami Andolan Bangladesh (IAB)",
    "Bangladesh Islamic Front": "Bangladesh Islami Front (BIF)",
    "Bangladesh Khilafat Majlis": "Bangladesh Khelafat Majlish (BKM)",
    "Khilafat Majlis": "Khelafat Majlis",
    "Liberal Democratic Party - LDP": "Bangladesh Liberal Democratic Party (LDP)",
    "Jatiya Party": "Jatiya Party (JaPa)",
    "Jatiya Party - JAPA": "Jatiya Party (JaPa)",
    "Gono Odhikar Parishad": "Gono Odhikar Parishad (GOP)",
    "Gono Odhikar Porishad- GOP": "Gono Odhikar Parishad (GOP)",
    "Amar Bangladesh Party (AB Party)": "Amar Bangladesh Party (AB)",
    "Bangladesh Development Party - BDP": "Bangladesh Development Party (BDP)",
    "Bangladesh National Party - BJP": "Bangladesh Jatiya Party (BJP)",
    "Jamiat Ulama-e-Islam Bangladesh": "Jamiat Ulema-e-Islam Bangladesh (JUIB)",
    "Gono Forum": "Gono Forum (GF)",
    "Gano Forum": "Gono Forum (GF)",
    "Bangladesh Supreme Party - BSP": "Bangladesh Supreme Party (BSP)",
    "Zaker Party": "Zaker Party (ZP)",
    "Bangladesh Jasod": "Bangladesh Jatiya Samajtantrik Dal (Bangladesh JaSad)",
    "Jatiya Samajtantrik Dal (JSD)": "Jatiya Samajtantrik Dal (JSD)",
    "Jatiya Samajtantrik Dal (JSD Rab)": "Jatiya Samajtantrik Dal-JASAD",
    "Ganosamhati Andolon": "Ganosanhati Andolan (GSA)",
    "Bangladesh Muslim League - BML": "Bangladesh Muslim League (BML)",
    "Bangladesh Nezam e Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Bangladesh Nezam Islam Party": "Bangladesh Nezame Islam Party (BNIP)",
    "Nagorik Oikya": "Nagorik Oikya (NO)",
    "Nagorik Oikko": "Nagorik Oikya (NO)",
    "Bangladesh Republican Party - BRP": "Bangladesh Republican Party (BRP)",
    "Communist Party of Bangladesh": "Communist Party of Bangladesh (CPB)",
    "Bangladesh Samajtantrik Dal": "Bangladesh Samajtantrik Dal (Basad)",
    "Insaniat Biplob Bangladesh - Insaniat Biplob": "Insaniyat Biplob Bangladesh (IBB)",
    "Nationalist Democratic Movement - NDM": "Nationalist Democratic Movement (NDM)",
    "Nationalist Democratic Movement": "Nationalist Democratic Movement (NDM)",
    "Ganatantri Party": "Ganatantri Party (GP)",
    "Janatar Dal": "Janotar Dol",
    "Amjanatar Dal": "Amjanatar Dol",
    "Islamic Front Bangladesh - IFB": "Islamic Front Bangladesh (IFB)",
    "Bangladesher Biplobi Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Revolutionary Workers Party": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Revolutionary Workers Party of Bangladesh": "Revolutionary Workers Party of Bangladesh (RWPB)",
    "Bangladesh Khelafat Andolon": "Bangladesh Khelafat Andolon (BKA)",
    "Bangladesh Sangskritik Muktijote": "Bangladesh Sangskritik Muktijote (BSM)",
    "Bangladesher Samajtantrik Dal (BSD)": "Bangladesh Samajtantrik Dal (Basad)",
    "Bangladesher Samajtantrik Dal (Marxist)": "Socialist Party of Bangladesh (Marxist) (SPB-M)",
    "Bangladesh Nationalist Front - BNF": "Bangladesh Nationalist Front (BNF)",
    "Bangladesh Kalyan Party": "Bangladesh Kallyan Party (BKP)",
    "Bangladesh Labor Party": "Bangladesh Labour Party",
    "Bangladesh Minority Janata Party - BMJP": "Bangladesh Minority Janata Party (BMJP)",
    "Bangladesh Nap": "Bangladesh National Awami Party–Bangladesh NAP (BNAP)",
    "Bangladesh Gonofront": "Gono Front (GF)",
    "Bangladesh Equal Rights Party": "Bangladesh Somo Odhikar Party (BEP)",
    "Islamic Oikkojot": "Islami Oikya Jote (IOJ)",
    "National People's Party - NPP": "National People's Party (NPP)",
    "National Democratic Party - JDP": "Jatiya Ganatantrik Party (JAGPA)",
    "Islamic Front Bangladesh": "Islamic Front Bangladesh (IFB)",
    "Bangladesh Muslim League": "Bangladesh Muslim League (BML)",
    "National Citizens Party (NCP)": "National Citizen Party (NCP)",
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
    "nawabganj": "Chapainawabganj",
    "pabna": "Pabna",
    "sirajganj": "Sirajganj",
    "rangpur": "Rangpur",
    "dinajpur": "Dinajpur",
    "kurigram": "Kurigram",
    "gaibandha": "Gaibandha",
    "lalmonirhat": "Lalmonirhat",
    "nilphamari": "Nilphamari",
    "panchagarh": "Panchagarh",
    "thakurgaon": "Thakurgaon"
}

def normalize_party(name: str) -> str:
    """Normalize party name to common convention."""
    if not name or str(name).strip() == "":
        return "Unknown"
    name = str(name).strip()
    return PARTY_NAME_MAP.get(name, name)

def normalize_location_name(name: str) -> str:
    """Normalize division or district name."""
    if not name: return ""
    name = str(name).strip()
    
    # lowercase to check against aliases
    lower_name = name.lower()
    if lower_name in LOCATION_ALIASES:
        return LOCATION_ALIASES[lower_name]
        
    return name.title()

def normalize_seat_name(name: str) -> str:
    """Normalize seat name to a common format e.g. 'Bogura 1' instead of 'bogra-1'."""
    if not name: return ""
    name = str(name).strip()
    name = re.sub(r"[-–—]", " ", name)
    name = re.sub(r"[\?\'’‘]", "'", name) # Normalize apostrophes and broken unicode
    name = re.sub(r"\s+", " ", name)
    
    # Handle Parbatya prefixes which often miss '-1'
    lower_name = name.lower()
    if lower_name.startswith("parbatya ") and not bool(re.search(r'\d+$', lower_name)):
        # Strip parbatya and add 1
        name = name[9:].strip() + " 1"

    parts = name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit():
        loc, num = parts
        loc = normalize_location_name(loc)
        return f"{loc} {num}"
    
    return normalize_location_name(name)

def normalize_candidate_name(name: str) -> str:
    """Normalize candidate name, whitespace, prefixes etc."""
    if not name: return ""
    name = str(name).strip()
    
    # Remove trailing commas
    name = re.sub(r",+$", "", name)
    # Remove bracketed text/nicknames e.g. "(Badsha)", " (Hira)"
    name = re.sub(r"\(.*?\)", "", name)
    
    # Replace hyphens with spaces (Arif-Ul-Islam -> Arif Ul Islam)
    name = re.sub(r"\s*-\s*", " ", name)
    
    # Titles and prefixes
    name = re.sub(r"\b(Khandaker|Khandker|Khandakar)\b", "Khandaker", name, flags=re.IGNORECASE)
    
    # Generic fixes
    name = re.sub(r"\b(Md|Mohammad|Muhammed|Muhammad|Mahammad)\b\.?\s*", "Md. ", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Mst|Mosa|Ms)\b\.?\s*", "Mst. ", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Dr|Advocate|Engr|Engineer|Barrister|Professor|Moulana|Maulana|Hazi|Haji|Al Haj|Al-Haj)\b\.?\s*", "", name, flags=re.IGNORECASE)
    
    # Initialize acronyms
    name = re.sub(r"\b([A-Z])\b\.?\s*", r"\1. ", name)
    
    # Very common name spelling variations
    name = re.sub(r"Rahaman", "Rahman", name, flags=re.IGNORECASE)
    name = re.sub(r"Hossan", "Hossain", name, flags=re.IGNORECASE)
    name = re.sub(r"Uddin", "Uddin", name, flags=re.IGNORECASE)
    name = re.sub(r"Chowdury", "Chowdhury", name, flags=re.IGNORECASE)
    name = re.sub(r"Miah", "Mia", name, flags=re.IGNORECASE)
    name = re.sub(r"Rumeen|Rumin", "Rumin", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Mollah|Molla)\b", "Molla", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Siddique|Siddiqui)\b", "Siddiqui", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Lutfor|Lutfar)\b", "Lutfar", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Tanbir|Tanvir)\b", "Tanvir", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Uddaula|Uddoula)\b", "Uddoula", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Sobur|Sabur)\b", "Sabur", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Eliyas|Elias)\b", "Elias", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Nurunnabi|Noorannabi)\b", "Nurunnabi", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Yeasir|Yasir)\b", "Yasir", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Salahuddin|Salauddin)\b", "Salahuddin", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Minhaj|Minhaz)\b", "Minhaz", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Minhajul|Minhazul)\b", "Minhazul", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Ariful|Arif Ul)\b", "Ariful", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Kawsar|Kawsar)\b", "Kawsar", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Ilias|Elias)\b", "Elias", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(Sayed|Sayeed)\b", "Sayed", name, flags=re.IGNORECASE)
    
    # Double spaces cleanup
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()
