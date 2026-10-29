# DualMova: Multi-Norm Data Engine for the Belarusian Language

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-brightgreen.svg)](https://www.python.org/)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-egraich-yellow.svg)](https://huggingface.co/egraich)
[![Architecture](https://img.shields.io/badge/Norms-Narkama%C5%ADka%20%7C%20Tara%C5%A1kievica-orange.svg)](#architecture)

**DualMova** is an open-source, high-throughput data processing engine and corpus construction framework specifically engineered for the Belarusian language. It addresses the unique linguistic dualism of Belarusian by providing **systematic multi-norm classification, orthographic tagging (`<orth_nark>` / `<orth_taras>`), and high-integrity cross-norm alignment (interwiki bitext & dictionary-verified pairs)**.

---

## 🏛️ Pipeline Architecture

```
                      +---------------------------------+
                      |       Raw Document Stream       |
                      |  (knihi.com / Wikimedia Dumps)  |
                      +----------------+----------------+
                                       |
                                       v
                      +---------------------------------+
                      |  Encoding & Layout Normalizer   |
                      |   - ftfy & Unicode NFKC         |
                      |   - Poetry & Prose Extractors   |
                      |   - Boilerplate Stripper        |
                      +----------------+----------------+
                                       |
                                       v
                      +---------------------------------+
                      |    Canonical Safe Typography    |
                      |   - Guillemets («...») & Dashes |
                      |   - 'ў' Post-Vocalic Anchoring  |
                      +----------------+----------------+
                                       |
                                       v
                      +---------------------------------+
                      |   Symmetric Ortho-Router        |
                      | Circuit 1: Official Standard    |
                      | Circuit 2: 1.14M Tarask Lexicon |
                      | Circuit 3: Nark Exception Mask  |
                      +----------------+----------------+
                                       |
         +-----------------------------+-----------------------------+
         |                             |                             |
         v                             v                             v
+------------------+         +-------------------+         +------------------+
|   Narkamaŭka     |         |   Taraškievica    |         |  Noise / Dialect |
|  <orth_nark>...  |         |   <orth_taras>... |         |    [REJECTED]    |
+------------------+         +---------+---------+         +------------------+
                                       |
                                       v
                             +-------------------+
                             |  Authentic Bitext |
                             | (Wikidata QID /   |
                             |  Dict-Verified)   |
                             +---------+---------+
                                       |
                                       v
                             +-------------------+
                             | Aligned Pair with |
                             |     `pair_id`     |
                             +---------+---------+
                                       |
                                       v
                      +---------------------------------+
                      |  Parquet Exporter (ZSTD Lv9)    |
                      |  7 HuggingFace Native Splits    |
                      +---------------------------------+
```

---

## 🌟 Key Features

1. **Strict Public Domain Guarantee:** Authors are audited through a multi-tier identity verification pipeline using Wikidata REST APIs (`P570` death year $< 1974$) and publication chronology heuristics. Zero risk of modern copyright infringement.
2. **Symmetric Discriminative Router:** Instead of discarding non-official spellings as errors or naively translating them with regexes, DualMova routes texts between **Narkamaŭka (NKBM-2008)** and **Taraškievica (BK-2005)** using a Bayesian differential scoring engine with etymological suffixal isolation (eliminating false-positive flags on words like *пісьмо, людзьмі, ведзьма, штосьці*).
3. **Authentic Bitext & Zero-Tolerance Pairs:** Completely deprecates fragile regex pseudo-translation for arbitrary prose. Cross-norm alignment (`pair_id`) is derived from **Wikimedia interwiki articles via Wikidata QID** and 100% dictionary-certified sentences, ensuring zero hybrid orthographic artifacts in SFT fine-tuning.
4. **$O(1)$ RAM Streaming Wiki Extraction:** Processes multi-gigabyte `.xml.bz2` Wikimedia dumps in streaming mode without extracting files to disk. Employs a stack-based matcher that strips arbitrarily nested templates `{{...}}` and tables `{|...|}` in linear time.
5. **Production Columnar Format:** Exports directly to **Apache Parquet** with **Zstandard Level 9** compression, achieving $\sim 8\times$ compression ratios over raw JSONL.

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/egraich/DualMova.git
cd DualMova
pip install -r requirements.txt
```

### Running the Pipeline

```bash
# 1. Build and verify public domain author manifest
python pipeline/01_build_manifest.py
python pipeline/strict_filter_manifest.py

# 2. Fast concurrent crawler
python pipeline/fast_crawl.py

# 3. Parse, clean boilerplate, and execute orthography routing
python pipeline/03_parse_and_tag.py

# 4. Stream & process Wikimedia dumps (bewiki, be_x_oldwiki, bewikisource)
python pipeline/wiki_extractor.py

# 5. Export multi-subset Parquet files (PyTorch / Hugging Face native)
python pipeline/04_export_parquet.py

# 6. Export turnkey SFT & Packed Pretrain (Adaption Labs / Together AI / Cloud Fine-Tuning)
python pipeline/05_export_adaption_labs.py

# 7. Run verification suite
python pipeline/verify_dataset.py
```

---

## 📊 Dataset Metrics (knihi.com Classic Literature)

| Subset / Split | Record Count | Parquet Size (ZSTD-9) | Target Use Case |
| :--- | :--- | :--- | :--- |
| **`all`** | **368,788** | **59.2 MB** | Full pretraining & continued pretraining |
| **`prose`** | **226,878** | **42.1 MB** | Prose & historical narrative modeling |
| **`folklore`** | **130,706** | **14.7 MB** | Traditional mythology, tales, and proverbs |
| **`poetry`** | **11,204** | **2.6 MB** | Metric poetry, strophes, and rhythm |
| **`nark`** | **264,811** | **47.2 MB** | Mononorm official standard tuning |
| **`tarask`** | **103,977** | **27.6 MB** | Mononorm classical orthography tuning |
| **`contrastive`** | **156,310** | **24.5 MB** | **DPO / Contrastive Pairs (78,155 pairs)** |

---

## ☁️ Adaption Labs & Together AI Ready Splits

For zero-code managed fine-tuning platforms (e.g., **Adaption Labs**, Together AI, Fireworks) where custom Python data collators or modified tokenizers cannot be executed, DualMova generates pre-packaged formats in `export/adaption_labs/`:

1. **`sft_translations.jsonl` (151,674 dialog turns, 176 MB):**
   - Standard OpenAI/Together AI Chat JSONL (`{"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}`).
   - Formatted for bidirectional orthographic translation (Narkamaŭka $\leftrightarrow$ Taraškievica).
   - **Zero Tag Leakage:** Assistant completions are pure authentic text (`text_raw`) with **no trailing XML closing tags**, preventing the model from outputting `</orth_*>` tokens into end-user chats.
2. **`packed_pretrain.jsonl` (115,329 packed documents, 120 MB):**
   - Consecutive clean paragraphs from the same literary work are stitched into ~6,000-character coherent narrative chapters (~1,500–2,000 tokens).
   - Prevents attention padding waste and protects against long-context degradation in models like **Gemma-4 31B Dense** (256k window).

---

## 💻 Using the Dataset via Hugging Face

```python
from datasets import load_dataset

# Stream the complete dual-norm corpus
dataset = load_dataset("egraich/belarusian-dualnorm-corpus-v1", "all", split="train")

# Access aligned contrastive pairs for DPO/RLHF
pairs_ds = load_dataset("egraich/belarusian-dualnorm-corpus-v1", "contrastive", split="train")
print(pairs_ds[0])
# {
#   "id": "knihi_605f32f3_0001",
#   "text": "<orth_taras>Кожная ілюстрацыя ў кнізе аздоблена цудоўным аповедам беларускай пісьменніцы...</orth_taras>",
#   "text_raw": "Кожная ілюстрацыя ў кнізе аздоблена цудоўным аповедам беларускай пісьменніцы...",
#   "orthography": "tarask",
#   "is_augmented": false,
#   "pair_id": "9ea5076d6b745684",
#   ...
# }
```

---

## 🔬 Relationship to Prior Art: ReMova

| Dimension | ReMova (`peratrasher`) | DualMova Engine |
| :--- | :--- | :--- |
| **Objective** | Mononorm MT (EN $\rightarrow$ BE Official Standard) | Multi-Norm LLM Pretrain & Alignment |
| **Norm Policy** | Mononorm standardization for MT target consistency | Balanced routing & dual-norm tagging |
| **Pair Alignment** | English ↔ Belarusian sentence pairs | Cross-norm contrastive pairs (`pair_id`) via interwiki & dictionary verification |
| **Data Scope** | Web-mined bitext (HPLT, Tatoeba, OpenSubtitles) | 100% Public Domain ($< 1974$) + CC BY-SA 4.0 |
| **Spelling Engine** | Custom Java LanguageTool Server | Lightweight, self-contained Python & PyArrow runtime |

For a full technical analysis, see [`docs/COMPARISON_REMOVA.md`](docs/COMPARISON_REMOVA.md).

---

## 📖 Citation

If you use **DualMova** in your research, please cite our repository and the foundational prior work:

```bibtex
@misc{egraich2026dualmova,
  author = {egraich},
  title = {DualMova: A Multi-Norm Data Engine and Contrastive Corpus for the Belarusian Language},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/egraich/DualMova}}
}
```

### Prior Art Citation
DualMova builds upon concepts and findings from the **ReMova** project (*University of Oslo*):

```bibtex
@article{pilinka2026remova,
  title={ReMova: Fine-tuning LLMs for English to Belarusian translation},
  author={Pilinka, Mikita and Kliuje{\u{u}}, Aliaksandr and Samuel, David and Scherrer, Yves},
  journal={arXiv preprint arXiv:2609.16427},
  year={2026}
}
```

---

## 📜 License

Licensed under the **[Apache License, Version 2.0](LICENSE)**.
Portions of the linguistic inspiration and dictionary structures are based on or inspired by prior research from the University of Oslo (ReMova) and the Belarusian LanguageTool open-source community.
