# DualMova Technical Specification & Architecture
## Multi-Norm Data Engineering Pipeline for the Belarusian Language (Official Narkamaŭka & Classical Taraškievica)

---

## 1. Introduction & Objectives

### 1.1. Background
Modern Large Language Models (LLMs) exhibit degraded performance on Belarusian due to severe data scarcity (<0.04% in Common Crawl) and an underlying linguistic phenomenon: **codified orthographic dualism**:
1. **Official Standard (Narkamaŭka / NKBM-2008):** Used in state administration, education, and domestic public media (~90% of contemporary text volume).
2. **Classical Standard (Taraškievica / BKP-2005):** Alternative codification prevalent in diaspora literature, independent publishers, and digital media (~10% of text volume).

In uncurated web crawls (mC4, OSCAR, HPLT), both norms are haphazardly mixed, contaminated by OCR artifacts, Russian script intrusions, Trasyanka creoles, and legacy machine translations (*Belazar*). Naively training models on this mixture causes representation collapse and hybrid morphological hallucinations.

### 1.2. Project Goal
Construct an open-source, legally unencumbered (**100% Public Domain / CC BY-SA 4.0**) dataset **DualMova-v1** on Hugging Face (under **ZorkaLabs**) with strict normative register segmentation:
* `<orth_nark> ... </orth_nark>`
* `<orth_taras> ... </orth_taras>`

coupled with evaluation benchmarks for fine-tuning dense foundational architectures (e.g. Gemma-4 31B Dense).

---

## 2. Legal Framework & Corpus Ingestion

### 2.1. Statutory Compliance (Law of the Republic of Belarus № 262-Z & Civil Code)
1. **Public Domain Threshold:**
   Under the non-retroactive extension of copyright duration to 70 years post-mortem (effective 19.11.2024), works by authors deceased **prior to January 1, 1974** have irrevocably entered the Public Domain (*грамадскі набытак*).
   * **Approved Classical Authors:** Authors deceased $< 1974$ (Janka Kupała, Jakub Kołas, Maksim Bahdanovič, Kuźma Čorny, Vincent Dunin-Marcinkievič, Francišak Bahuševič, Ciotka, Vacłaŭ Łastoŭski, Aleś Harun, Zmitrok Biadula, Francišak Alachnovič, etc.).
2. **Folklore & Traditional Folk Art:**
   Article 7 of Law № 262-Z explicitly excludes folklore works without an identified individual author from copyright restrictions.
3. **Excluded Contemporary Authors:**
   Authors deceased in 1974 or later are strictly excluded from open distribution to ensure full legal compliance.

### 2.2. Phase 1 Data Ingestion Sources
1. **`knihi.com` («Беларуская Палічка»):**
   * `/autary.html` (1,377 cataloged authors) $\rightarrow$ filtered for death year $< 1974$.
   * `/rfm.html` (folklore, mythology, ethnographic collections — 100% Public Domain).
   * Structural separation of poetry (`div.POETRY`) and prose (`div.container`).
2. **Belarusian Wikipedia Editions:**
   * `be.wikipedia.org` (Official Standard, CC BY-SA 4.0).
   * `be-tarask.wikipedia.org` (Classical Standard, CC BY-SA 4.0).
3. **Belarusian Wikisource (`be.wikisource.org`):**
   * Archival historical sources and pre-revolutionary publications.

---

## 3. DualMova Engine Architecture

The architecture consists of a multi-stage pipeline:
1. **Stage 1: Manifest Builder & Validator (`01_build_manifest.py`, `01_verify_manifest.py`, `strict_filter_manifest.py`)** — Resolves biographical records and Wikidata QIDs to filter strictly Public Domain texts.
2. **Stage 2: Respectful Crawler (`02_crawl_server.py`, `fast_crawl.py`)** — Rate-limited, resilient crawler archiving raw HTML responses into immutable JSON wrappers.
3. **Stage 3: Discriminative Classifier & Tagger (`03_parse_and_tag.py`, `ortho_router.py`)** — Segregates prose and poetry, applies four-cascade classification, and tags valid segments.
4. **Stage 4: Parquet Serialization (`04_export_parquet.py`)** — Serializes corpus splits into Zstandard-compressed Parquet files with Hugging Face dataset cards.
5. **Stage 5: Pretraining & SFT Adaptation (`05_export_adaption_labs.py`)** — Builds packed pretrain blocks (4,000–8,000 chars) and clean instruction translation pairs.
