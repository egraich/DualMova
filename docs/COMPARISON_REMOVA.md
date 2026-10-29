# Technical Comparison: ReMova and DualMova

## Executive Summary

Both **ReMova** (*Pilinka et al., University of Oslo, arXiv:2609.16427*) and **DualMova** tackle foundational challenges in processing Belarusian text for modern neural models. While ReMova pioneered rigorous data filtration for English–Belarusian machine translation targeting the official orthographic standard, DualMova addresses multi-norm pre-training and alignment across both codified varieties.

| Dimension | ReMova (`peratrasher`) | DualMova |
| :--- | :--- | :--- |
| **Primary Goal** | Mononorm MT (EN $\rightarrow$ BE Official Standard) | Multi-Norm LLM Pretrain & Alignment |
| **Norm Policy** | **Mononorm Standardization:** Filter or normalize classical variants to ensure target uniformity | **Multi-Norm Preservation:** Explicitly classify, tag, and balance both codified standards |
| **Taraškievica Treatment** | Filtered or normalized via LanguageTool and targeted rewrite rules | Validated via 1.14M classical lexicon + morphonological automata; tagged `<orth_taras>` |
| **Cross-Norm Bitext** | Mononorm focus (EN $\leftrightarrow$ BE Narkamaŭka bitext) | **Authentic Interwiki Bitext (QID)** + Certified Dictionary Pairs |
| **Data Scope** | Web-scale parallel bitext (HPLT, Tatoeba, OpenSubtitles) | **Verified Public Domain** (Author death $< 1974$ + folklore) + CC BY-SA 4.0 Wikimedia |
| **Spelling Engine** | Custom Java LanguageTool Server (`LocalChecker`) | Self-contained Python/PyArrow engine with memory-mapped frozenset lookups |
| **Wikimedia Parsing** | Extraction of parallel sentence pairs | Memory-constant $O(1)$ streaming parser (reads directly from `.xml.bz2`) |
| **Dataset Granularity** | Sentence pairs (MT bitext) | Coherent multi-sentence paragraphs and poetic strophes (LLM pretraining) |

---

## 1. Architectural Perspectives

### 1.1. The Dual-Norm Context in Belarusian NLP
Belarusian features two codified orthographic and morphological standards:
1. **Official Standard (Narkamaŭka / NKBM-2008):** Used in state administration, education, and domestic public media.
2. **Classical Norm (Taraškievica / BKP-2005):** Standard in diaspora communities, independent publishers, and significant historical literature.

### 1.2. ReMova's Approach: Mononorm Filtration for Machine Translation
In supervised machine translation targeting the official standard, orthographic variation can introduce evaluation noise and split probability mass across competing spelling variants. ReMova addressed this by implementing strict normalisation (Section 2.1 of Pilinka et al.):
> *"A central element of our approach is the strict handling of misspellings and Taraškievica forms... Table 1 shows that about 12% of the pairs are dropped... mostly because they exceed the LanguageTool density threshold (a proxy for Taraškievica influence and chronic misspelling)."*

Because standard LanguageTool configurations evaluate against the official codification, classical forms (e.g. *сьнег*, *пляны*, *унівэрсытэт*) are flagged. For the specific task of mononorm English–Belarusian translation, ReMova's filtering successfully maximized stylistic uniformity in model generations.

### 1.3. DualMova's Approach: Two-Circuit Multi-Norm Routing
DualMova targets generative foundation models and multi-register representation where preserving both cultural traditions is valuable:
- **Circuit 1 (Official Standard):** Validates against official orthographic norms (NKBM-2008).
- **Circuit 2 (Classical Standard):** Evaluates candidate classical tokens against a dedicated **1,144,795 word-form Taraškievica lexicon** and verified assimilation soft-sign rules (BKP-2005).
- **Outcome:** Classical text is preserved with high precision and wrapped in normative tags (`<orth_taras>...</orth_taras>`), enabling controlled steerability via prompting or special tokens.

---

## 2. Cross-Norm Alignment and Bitext Construction

### 2.1. Linguistic Complexity of Surface Phonetic Replacement
When mapping between Taraškievica and Narkamaŭka, simple surface regular expressions encounter several complex linguistic boundaries:
- **Stress-Dependent Jakanne:** Taraškievica particles `ня` and `бяз` depend strictly on word stress in the following syllable (*ня бы́ў* vs. *не была́*; *бяз на́с* vs. *без мяне́*). Without accentual prosody data, surface rules can produce phonetically irregular forms.
- **Etymological vs. Foreign Loanword Consonants:** Western European loanwords retain soft liquids (*плян, кляса, лягічны, сыстэма*), whereas native Slavic roots do not (*лоб, лес*). Distinguishing these requires morphological and etymological lookups.
- **Morphological Paradigm Variations:** Inflectional endings (such as genitive case *-а/-я* vs. *-у/-ю*) and historical derivations (*існуючы* vs. *істнуючы*) require paradigm-aware mapping.
- **Hybrid Artifacts:** Unconstrained surface replacement risks creating inconsistent hybrid paragraphs containing mixed orthographic conventions.

### 2.2. DualMova's Solution: Authentic Interwiki Alignment and Strict Verification
DualMova avoids unconstrained synthetic rewriting on literary prose. Cross-norm alignment pairs (`pair_id`) are derived from:
1. **Authentic Interwiki Bitext (via Wikidata QID):**
   - Articles from `be.wikipedia.org` (Narkamaŭka) and `be-tarask.wikipedia.org` (Taraškievica) linked by shared Wikidata entity identifiers (`QID`).
   - Paragraph and sentence alignments are extracted from native, human-authored text produced independently by speakers of each standard.
2. **Dictionary-Verified Lexical Pairs:**
   - Synthetic parallel pairs are admitted only when 100% of transformed tokens are verified in both official dictionaries and the 1.14M Taraškievica lexicon, with zero rule ambiguities.

This ensures high data integrity for contrastive learning and multi-norm representation.

---

## 3. Data Provenance and Legal Framework

### 3.1. ReMova's Focus
ReMova targeted general-domain machine translation, drawing from extensive web-crawled bitext (HPLT, OpenSubtitles, and Tatoeba), which provides broad modern vocabulary across conversational and technical domains.

### 3.2. DualMova's Focus
DualMova focuses on building a vetted, open-source public domain literary and encyclopedic corpus:
1. **Statutory Expiration:** Works from `knihi.com` were verified against author death dates prior to 1974 (Law No. 262-Z and Civil Code Art. 980).
2. **Catalog Disambiguation:** 1,369 bibliographies were checked against Wikidata REST APIs to ensure public domain status.
3. **Folklore:** Traditional folklore materials are inherently non-copyrightable by statutory definition.
4. **Wikimedia Integration:** Modern encyclopedic prose is ingested under CC BY-SA 4.0.

---

## 4. Operational Characteristics

| Metric / Feature | ReMova (`peratrasher`) | DualMova Engine |
| :--- | :--- | :--- |
| **Runtime Environment** | Python 3.11 + Java 17 + Maven | Pure Python 3.10+ (PyArrow, requests, bs4) |
| **Memory Footprint** | ~2–4 GB RAM (JVM + fastText models) | Constant $O(1)$ ~50–200 MB RAM |
| **Dump Decompression** | Requires disk extraction of dumps | In-memory streaming from `.bz2` streams |
| **Output Formats** | TSV / JSONL | Columnar Apache Parquet with ZSTD Level 9 |
| **Downstream Target** | Machine Translation fine-tuning | Large Language Model pre-training & SFT |

---

## 5. Summary & Attribution

ReMova demonstrated that **data quality is a critical factor for Belarusian NLP**, setting an important precedent for corpus curation in low-resource Slavic languages. DualMova complements ReMova's pioneering mononorm work by offering multi-norm routing, document-level packaging, and contrastive cross-norm pairs for next-generation generative language models.

DualMova gratefully acknowledges the foundational research and contributions of Mikita Pilinka, Aliaksandr Kliujeŭ, David Samuel, and Yves Scherrer (*University of Oslo*).
