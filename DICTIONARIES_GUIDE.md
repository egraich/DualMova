# Registry of Dictionaries and Linguistic Resources for DualMova

This document catalogues all reference lexicons, grammatical databases, and linguistic toolkits integrated into the DualMova engine for the Belarusian language across both norms (Official Narkamaŭka and Classical Taraškievica).

---

## 1. Local Reference Lexicons (stored in `DualMova/dictionaries/`)

### 1.1. Classical Standard Lexicon (Taraškievica / BKP-2005)
* **Path:** `DualMova/dictionaries/tarask/wordlist.txt`
* **Source:** Derived from the `375gnu/spell-be-tarask` repository (upstream reference for Debian Taraškievica spellchecking packages, BKP-2005 codification).
* **Volume:** **26.2 MB**, **1,144,795 unique word forms**.
* **Coverage:** Full inflectional and conjugational paradigms in classical orthography:
  - Assimilative soft-sign marking (*сьвет, зьмена, сьнег*)
  - European loanword phonology (*кляса, плян, сыстэма, унівэрсытэт, эўрапейскі*)
  - Historical genitive case endings (*-а/-я* vs. *-у/-ю*) and prepositional case forms.
* **Runtime Characteristics:** Ingests into an in-memory Python `frozenset` in ~0.3 seconds (~85 MB RAM footprint), providing constant $O(1)$ membership verification.

### 1.2. Official Standard Lexicon (Narkamaŭka / NKBM-2008)
* **Path:** `DualMova/dictionaries/nark/be_BY.aff` and `DualMova/dictionaries/nark/be_BY.dic`
* **Source:** Official academic Hunspell dictionary of the Republic of Belarus (`375gnu/hunspell-be`, Debian package `hunspell-be`).
* **Authority:** Yakub Kolas Institute of Linguistics at the National Academy of Sciences of Belarus (2008 Rules, Law № 420-Z).
* **Usage:** Integrated via `spylls` or `pyhunspell` for morphological validation and lemmatization of the official norm.

---

## 2. Specialized Converters & Toolkits

### 2.1. `pravapis` Library (Python & NPM)
* **Repository:** `github.com/sewstie/pravapis`
* **Installation:** `pip install pravapis`
* **Capabilities:** Bidirectional conversion:
  - Narkamaŭka $\leftrightarrow$ Taraškievica
  - Cyrillic $\leftrightarrow$ Latin script (Łacinka)
* **Precision:** 96% rule precision, verified against 1,007 integration test cases covering contextual rules (e.g. pre-stress *не $\rightarrow$ ня* shifts).

---

## 3. Literary Lexical Sources (`knihi.com`)

1. **Archival Lexicography (`/slouniki.html`):**
   - Access to historical specialized dictionaries (`https://files.knihi.com/Knihi/Slounik/`):
     - Terminology lexicons (Lastoŭski, Duzh-Dusheŭski 1923 — Public Domain).
     - Toponymic and onomastic gazetteers (Zhuchkevich, Lemtiuhova — Belarusian geographic whitelist).
     - Dialectal dictionaries and ethnographic folklore collections.
2. **Interactive Slounik Plugin (`knihi.js`):**
   - Direct integration with `Slounik.org` lexical definitions.
