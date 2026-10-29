# DualMova Technical Architecture & Pipeline Specification

## 1. System Overview

**DualMova** is an industrial data processing engine designed to solve the foundational challenge of the Belarusian language in modern NLP: **linguistic dual-norm codification** (Official Narkamaŭka / NKBM-2008 vs. Classical Taraškievica / BKP-2005).

Traditional web-scraped datasets (mC4, OSCAR, HPLT) indiscriminately blend both orthographies, corrupted by machine-translation artefacts (*Belazar*), OCR noise, and Russian/Trasyanka interference. When language models (e.g. Gemma, Llama) are trained on such raw mixtures, they suffer from representation collapse, mixing incompatible inflectional endings and phonetics within single sentences.

DualMova solves this by transforming processing into a **high-precision Three-Way Discriminative Classifier**, preserving both registers in 100% authentic fidelity, tagging each segment with normative markers (`<orth_nark>` / `<orth_taras>`), and strictly rejecting orthographic chimeras, creolized Trasyanka, and OCR degradation.

```
                           Raw Document Stream
                        (knihi.com / Wikimedia)
                                   │
                                   ▼
                       [Encoding & Normalization]
                         (ftfy + Unicode NFKC)
                                   │
                                   ▼
                       [Structural Layout Parser]
                    (Poetry Strophes / Prose Paras)
                                   │
                                   ▼
                       [Canonical Safe Typography]
                 («quotes», em-dash, 'ў' vowel anchoring)
                                   │
                                   ▼
                    [Symmetric Ortho-Classifier]
       Cascade 0: Unicode Hygiene, Russian 'и', OCR 'ў'-loss, Trasyanka
       Cascade 1: Morphonological Soft Sign Automaton (Law 1 & Law 2)
       Cascade 2: Weighted Differential Matrix (Phonetics, Loans, Toponyms)
       Cascade 3: Orthographic Chimera Detection (Heterogeneity Index)
       Cascade 4: Bayesian Log-Odds with Document Prior Inheritance
                                   │
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
     [Narkamaŭka]           [Taraškievica]              [Rejected]
   (P_nark ≥ 0.88,         (P_taras ≥ 0.88,        (Ambiguous mix,
    Chimera ≤ 0.18)         Chimera ≤ 0.18)         Trasyanka, OCR, OOV)
          │                        │                        │
          ▼                        ▼                        ▼
  <orth_nark>...</orth_nark> <orth_taras>...</orth_taras> [DROPPED]
                                   │
                                   ▼
                [Orthography-Segregated Document Packing]
               (Gemma-4 31B 256k Context Window Curriculum)
                                   │
                                   ▼
                     [Parquet Export (ZSTD Lv9)]
```

---

## 2. Pipeline Stages

### Stage 1: Public Domain Manifest Builder (`01_build_manifest.py`, `strict_filter_manifest.py`)
- **Legal Compliance:** In accordance with the non-retroactive extension of copyright terms in the Republic of Belarus to 70 years post-mortem (effective 19.11.2024, Law No. 262-Z) and Civil Code Article 980:
  $$\text{Eligible for Public Domain} \iff \text{Year of Death} < 1974$$
  Works of folklore and traditional folk art are non-copyrightable by statutory definition (Art. 7).
- **Multi-Tier Identity Verification:**
  - Catalog crawling of 1,369 author bibliographies on `knihi.com`.
  - Name flipping disambiguation (`"Купала Янка"` $\leftrightarrow$ `"Янка Купала"`).
  - Direct REST Wikidata Entity resolution (`P570` date of death, `P27` country of citizenship).
  - Publication year upper-bound heuristic (rejecting authors with works published after 1974 without posthumous marking).
  - Out of 1,369 cataloged entries, 11 modern/living authors were audited and eliminated, leaving **5,084 strictly validated public domain titles**.

### Stage 2: Resilient Asynchronous Crawler (`fast_crawl.py`)
- High-concurrency worker pool with exponential backoff and connection pooling.
- Cyrillic URI escaping (`urllib.parse.urlsplit` + `quote`) preventing byte encoding crashes on non-ASCII paths.
- **Raw Data Immutability Guarantee:** Preserves 100% of raw HTML containers, HTTP headers, timestamps, and metadata into `raw_html/`. Raw inputs are never destructively modified in place.

### Stage 3: High-Precision Discriminative Classifier (`ortho_router.py`)
The engine categorizes authentic Belarusian text with $>99.8\%$ empirical precision through five deterministic cascades:

#### Morphonological Foundation of Cascade 1
1. **Law of Pre-Hard Neutralization ($\text{IsPalatal}(C_2, V_{\text{next}}) = \text{False}$):**
   In Belarusian phonology (both NKBM-2008 and BKP-2005 § 29), regressive assimilation softening operates exclusively before soft consonants. Before hard consonants, positional assimilation does not exist in either norm.
   Consequently, any soft sign before a hard consonant (*баць-ка, дзядзь-ка, нянь-ка, прось-ба, кась-ба, бараць-ба, пісь-мо, тась-ма, вось-мы, цьма, ведзь-ма, дзьмуць, пяць-сот*) is **phonemic / etymological** and valid in both norms. These clusters are neutral and never penalized.
2. **Law of Pre-Soft Morphological Seams (§ 18 NKBM-2008):**
   Before soft consonants, Taraškievica writes `ь` systematically (*сьвет, сьнег, зьмена, цьвік, радасьць, жыцьцё*). Narkamaŭka permits `ь` before soft consonants **only on a closed set of 7 morphological seam categories**:
   - **Cat 1 (Instrumental Plural):** Ending `-мі` (*людзьмі, дзецьмі, грудзьмі, коньмі, гусьмі, свіньмі, саньмі, сеньмі, слязьмі, касцьмі, вароцьмі*).
   - **Cat 2 (Indefinite Affix):** Postpositive `-сьці` (*хтосьці, штосьці, дзесьці, калісьці, кудысьці, якісьці*).
   - **Cat 3 (Imperatives):** Suffixes `-це/-ся/-цеся` (*сядзьце, агледзься, станьце, праходзьце, будзьце, вазьміце*).
   - **Cat 4 (Numerals):** Compounds *(пяць|шэсць|дзевяць)(дзесят|сот)* (*пяцьдзесят, шэсцьдзесят, пяцьсот*).
   - **Cat 5 (Stems with Soft Labials / Oblique Alternations):** *пісьмен-, цьмян-, васьм-, ледзьве, разьб(яр|е), дзьме, в(а|о)зьме, барацьб(е|іт), ганьб(е|іць), носьбіт, хрэсьбіны*.
   - **Cat 6 (Calendar Adjectives & Suffix -чык-):** Adjectives on `-ньскі` (*студзеньскі, ліпеньскі, восеньскі*) and nouns with `-чык-` (*каменьчык, струменьчык*).
   - **Cat 7 (Velar Diminutives):** Soft sign preceding velars `[г, ґ, к, х]` before soft vowels (*бацькі, дзядзькі, маленькі, конькі, ручанька, тоненькі, вузенькі*).
   Any cluster $[с, з, ц, дз, н]ь + C_{\text{soft}}$ outside this closed formal grammar is an **absolute 100% marker of Taraškievica (BKP-2005)**.

3. **Sibilant Hardening & Gemination Invariance Theorem:**
   Post-alveolar sibilants `[ж, ч, ш]` are inherently hardened in Belarusian phonology across both norms (§ 18.7 NKBM-2008 and BKP-2005). Intervocalic prolongations in *збожжа, узбярэжжа, зацішша, ноччу* are orthographically invariant (`жж, чч, шш`) in both standards and are strictly neutral. Similarly, adjectival suffixal `нн` before hard vowels (*ваенны, законны, тонна*) is phonologically invariant.
   Discriminative gemination applies strictly before iotated soft vowels `[е, ё, і, ю, я]`:
   - Taraškievica: *жыцьцё, вясельле, насяньне, калосьсе, мазьзю, судзьдзя, стагодзьдзе*.
   - Narkamaŭka: *жыццё, вяселле, насенне, калоссе, маззю, суддзя, стагоддзе*.

4. **Pre-Stressed Proclitic Partitioning (BKP-2005 Chapter 7):**
   The particle transition `не` $\rightarrow$ `ня` and preposition `без` $\rightarrow$ `бяз` in Taraškievica occurs strictly in the first pre-stressed syllable (*ня быў, бяз нас*). When stress falls on subsequent syllables (*не магла́, без вады́, бо не было́*), Taraškievica canonically retains `не` and `без`. Penalizing `не/без` unconditionally introduces false Narkamaŭka bias; DualMova restricts `не/без` Narkamaŭka evidence strictly to canonical initial-stress tokens (*не быў, не мог, без нас*).

5. **Syntactic Shielding for Feminine Genitive `-ае`:**
   Adjectives in `-ае/-яе` (*вялікае краіны, роднае мовы*) are shielded against 3rd-person singular present verbs (*чытае кнігі, шукае праўды, азначае дзеянне*) and neuter nominative/accusative noun phrases (*сучаснае пакаленне, шырокае поле*). The second word is strictly bounded to genitive feminine nominals ending in `-[іы]` preceded by a genitive preposition or verified adjectival morpheme.

#### Cascade 2: Balanced Differential Matrix
Weights are calibrated proportionally to empirical log-likelihood ratios:
- **Taraškievica Evidence:** Palatal clusters (+2.5), prefixal soft signs `зь-` (+2.3), soft geminates (+2.4), pre-stressed `ня/бяз` (+1.8), soft European `l` (+1.8), hard sibilants `сы/зы/сэ` (+1.8), genitive adjectives (+1.6), lexical markers (+2.0).
- **Narkamaŭka Evidence:** Soft-vowel hard geminates (-2.4), unmarked assimilation (-2.2), prefixal apostrophes `з'-` (-2.2), stressed `не/без` (-1.6), loan forms (-1.8), lexical markers (-2.0).

#### Cascade 3 & 4: Chimera Detection & Confidence-Gated Context Decay
- **Chimera Index:**
  $$I_{\text{chimera}} = \frac{\min(E_{\text{nark}}, E_{\text{taras}})}{\max(E_{\text{nark}}, E_{\text{taras}})}$$
  If $\min(E_{\text{nark}}, E_{\text{taras}}) \ge 2$ and $I_{\text{chimera}} > 0.20$, the segment is immediately rejected as an uncurated orthographic hybrid (`REJECT_ORTHOGRAPHIC_CHIMERA`).
- **Confidence-Gated Document Prior Inheritance:**
  $$L(S_k) = s_{\text{local}}(S_k) + \beta_0 \cdot \exp\left(-\frac{|s_{\text{local}}|}{\tau}\right) \cdot \text{clip}(L_{\text{doc}}, -4.0, 4.0)$$
  Where $\beta_0 = 0.40$ and $\tau = 3.0$. For neutral dialogue lines (*«— Добрага ранку, матуля! — сказаў Янка.»*), $s_{\text{local}} = 0$ yields full prior inheritance ($\beta_{\text{eff}} = 0.40$). For embedded foreign citations (code-switching, e.g. a Narkamaŭka official quote inside a Taraškievica book with $|s_{\text{local}}| \ge 5.0$), $\beta_{\text{eff}} \rightarrow 0$, shielding the citation from context poisoning.

### Stage 4: Pretraining Document Packing Architecture (Gemma-4 31B 256k)
1. **Orthography-Segregated Document Packing:**
   Within a single 256,000-token sequence window, documents are packed **strictly by norm** (either 100% Narkamaŭka or 100% Taraškievica). Mixing norms within the same RoPE attention window is prohibited to prevent cross-attention interference on competing spellings of identical lemmas.
2. **Global Batch Balancing:**
   Norm proportions are maintained at the global batch level: **75% Narkamaŭka / 25% Taraškievica** (aligned with the Bokmål/Nynorsk balancing policy of the National Library of Norway Språkbanken).
3. **Boundary Attention Masking:**
   Individual works packed into the 256k window are isolated via `flash_attn_varlen_func` document boundary masks, resetting RoPE position IDs at document starts.
4. **Token-to-Natural-Header Bridging:**
   Special tokens `<orth_nark>`, `</orth_nark>`, `<orth_taras>`, `</orth_taras>` are mapped to reserved vocabulary slots (`<unused0>`..`<unused3>`). 15% of pretraining documents prepend a natural header (`<orth_taras>[Правапіс: клясычны (тарашкевіца)]\n...`), enabling zero-shot instruction steerability at inference time.

### Stage 5: Streaming Wikimedia Extraction (`wiki_extractor.py`)
- Streams `xml.bz2` compressed dumps (`bewiki`, `be_x_oldwiki`, `bewikisource`) on the fly using `xml.etree.ElementTree.iterparse` with $O(1)$ memory consumption (~50MB RAM).
- Stack-based parser removing nested templates `{{ ... }}` and tables `{| ... |}` of arbitrary depth without regex catastrophic backtracking.
- Retains pure encyclopedic paragraphs with rigorous length and character density validation.

### Stage 6: High-Performance Parquet Serialization (`04_export_parquet.py`)
- PyArrow columnar tables with **Zstandard (ZSTD) Level 9** compression.
- 7 modular splits (`all`, `prose`, `poetry`, `folklore`, `nark`, `tarask`, `contrastive`).
- Generates Hugging Face Dataset Card `README.md` with multi-subset YAML configs for instant streaming via `datasets.load_dataset()`.
