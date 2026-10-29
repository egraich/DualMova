import json
from pathlib import Path

# The 24 excluded author slugs identified during the forensic audit
EXCLUDED_SLUGS = {
    "Siarhiej_Jors",             # Modern historian (b. 1972); WWII nationalist leader monograph (political/legal risk)
    "Uladzimir_Valodzin",        # Modern author (b. 1970s); 2016 queer history study
    "Anatol_Barouski",           # Modern writer (1942–2024); lifetime publications in 1990s-2000s, not PD
    "Kastus_Travien",            # Modern writer (active 1990s-2000s); published by "Народная кніга", not PD
    "Maksim_Klimkovic",          # Modern author (b. 1958, grandson of Mikhas Klimkovic); living, not PD
    "Siarhiej_Ukrainka",         # Contemporary humorist (written 2000-2008); not PD
    "Alesia_Babareka",           # Daughter of Adam Babareka (memoirs written in 2000s); not PD
    "E_Zolava",                  # Literary scholar (commentary written in 1987); not PD
    "Michail_Bajaryn",           # Modern linguist/translator (b. 1970s); living, not PD
    "Tacciana_Karotkaja",        # Modern philosopher/scholar (active 1980s-2000s); living, not PD
    "Vital_Makarevic",           # Modern historian (b. 1970s/1980s); living, not PD
    "VS_Novak",                  # Modern folklorist (b. 1954); living, not PD
    "Hienadz_Prybytka",          # Modern historian (active 2000s); living, not PD
    "Ivan_Sarakavik",            # Modern professor (textbooks in 1990s-2000s); living, not PD
    "Siarhiej_Sciapan",          # Modern author/artist (b. 1967); living, not PD
    "Siarhiej_Chareuski",        # Modern culturologist/historian (b. 1967); living, not PD
    "Mikola_Chaustovic",         # Modern professor (b. 1959); living, not PD
    "Ludmila_Chmialnickaja",     # Modern historian (b. 1960s); living, not PD
    "Symon_Kandybovic",          # Emigre publicist (political book on BNR/anti-soviet resistance 1969)
    "Piotra_Palahoska",          # Emigre GULAG memoirs
    "Piotra_Syc",                # Emigre WWII Anders' army memoirs (Munich 1964)
    "Todar_Lebiada",             # Emigre poetry ("Песьні выгнаньня")
    "Vaclau_Lastouski",          # Prime minister of BNR; related works on official extremist materials list
    "I_Scarbovic",               # Non-literary veterinary parasitical guide
    "Alaksandr_Kavalenia",       # Modern academician (b. 1946); living, not PD
    "Dzmitryj_Matviejcyk",       # Modern archivist/historian (b. 1980); living, not PD
    "Jan_Sumski",                # Modern historian (b. 1970s); living, not PD
    "Maisiej_Polak",             # Non-literary medical gynecology textbook
}

EXCLUDED_TITLE_KEYWORDS = [
    "плывуць вятры",
    "гутарка старога дзеда",
    "што трэба ведаць кожнаму беларусу",
    "сабакі эўропы",
    "сабаки европы",
    "айчына",
    "рэвалюцыя",
]

def audit_record(r: dict) -> tuple[bool, str]:
    slug = r.get("author_slug", "")
    if slug in EXCLUDED_SLUGS:
        return False, f"EXCLUDED_AUTHOR_SLUG:{slug}"
    
    title = (r.get("title") or "").lower()
    for bkw in EXCLUDED_TITLE_KEYWORDS:
        if bkw in title:
            return False, f"BANNED_TITLE_KEYWORD:{bkw}"
            
    return True, "OK"
