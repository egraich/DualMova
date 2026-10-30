"""
DualMova — Stage 4: Apache Parquet Serialization for Hugging Face
=================================================================
Reads processed/dataset.jsonl, stratifies into normative and genre splits
(all, prose, poetry, folklore, nark, tarask, contrastive), and writes
compressed Parquet files (Zstandard Level 9) following Hugging Face standards.

Execution:
    python 04_export_parquet.py

Outputs:
    DualMova/pipeline/export/
        all/             — Complete corpus
        prose/           — Prose subset
        poetry/          — Poetry subset
        folklore/        — Folklore & mythological texts
        nark/            — Official Narkamaŭka standard
        tarask/          — Classical Taraškievica standard
        contrastive/     — Inter-norm contrastive pairs
        README.md        — Dataset Card for Hugging Face Hub

Requirements:
    pip install pandas pyarrow datasets
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    print("ERROR: Missing dependencies. Please run: pip install pandas pyarrow")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR / "processed"
EXPORT_DIR = SCRIPT_DIR / "export"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Parquet Schema Definition
PARQUET_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("text", pa.string()),
    pa.field("text_raw", pa.string()),
    pa.field("orthography", pa.string()),      # "nark" | "tarask" | "invariant"
    pa.field("genre", pa.string()),            # "prose" | "poetry" | "folklore"
    pa.field("author", pa.string()),
    pa.field("author_slug", pa.string()),
    pa.field("author_death_year", pa.int32()),
    pa.field("title", pa.string()),
    pa.field("source_url", pa.string()),
    pa.field("license", pa.string()),
    pa.field("source", pa.string()),
    pa.field("lang", pa.string()),
    pa.field("is_augmented", pa.bool_()),
    pa.field("pair_id", pa.string()),
    pa.field("char_count", pa.int32()),
    pa.field("word_count", pa.int32()),
])

DATASET_ID = "ZorkaLabs/belarusian-dualnorm-corpus-v1"


def load_jsonl(path: Path) -> list[dict]:
    """Loads records from a JSONL file."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def to_parquet(records: list[dict], out_dir: Path, name: str):
    """Converts a list of records into Zstandard-compressed Parquet."""
    if not records:
        log.warning("Empty split encountered: %s", name)
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    normalized = []
    for r in records:
        normalized.append({
            "id": str(r.get("id", "")),
            "text": str(r.get("text", "")),
            "text_raw": str(r.get("text_raw", "")),
            "orthography": str(r.get("orthography", "")),
            "genre": str(r.get("genre", "prose")),
            "author": str(r.get("author", "")),
            "author_slug": str(r.get("author_slug", "")),
            "author_death_year": int(r.get("author_death_year") or -1),
            "title": str(r.get("title", "")),
            "source_url": str(r.get("source_url", "")),
            "license": str(r.get("license", "public_domain")),
            "source": str(r.get("source", "knihi.com")),
            "lang": str(r.get("lang", "be")),
            "is_augmented": bool(r.get("is_augmented", False)),
            "pair_id": str(r.get("pair_id") or ""),
            "char_count": int(r.get("char_count") or len(r.get("text_raw", ""))),
            "word_count": int(r.get("word_count") or len(r.get("text_raw", "").split())),
        })

    df = pd.DataFrame(normalized)
    table = pa.Table.from_pandas(df, schema=PARQUET_SCHEMA)

    out_path = out_dir / "data.parquet"
    pq.write_table(
        table,
        out_path,
        compression="zstd",
        compression_level=9,
    )

    size_mb = out_path.stat().st_size / (1024 * 1024)
    log.info("  Saved split %s: %d records, %.2f MB -> %s", name, len(records), size_mb, out_path)


def generate_dataset_card(stats: dict) -> str:
    """Generates a dataset card for the Hugging Face Hub."""
    now = datetime.now().strftime("%Y-%m-%d")
    total = stats.get("total", 0)
    nark = stats.get("nark", 0)
    tarask = stats.get("tarask", 0)
    invariant = stats.get("invariant", 0)
    prose = stats.get("prose", 0)
    poetry = stats.get("poetry", 0)
    folklore = stats.get("folklore", 0)
    contrastive = stats.get("contrastive_pairs", 0)

    card = f"""---
license: cc-by-sa-4.0
language:
- be
tags:
- belarusian
- NLP
- orthography
- tarashkievica
- narkamauka
- text-classification
- low-resource
pretty_name: "DualMova: Belarusian Dual-Norm Corpus v1"
size_categories:
- 100K<n<1M
source_datasets:
- original
task_categories:
- text-generation
- text-classification
configs:
- config_name: all
  data_files:
    - split: train
      path: all/data.parquet
- config_name: prose
  data_files:
    - split: train
      path: prose/data.parquet
- config_name: poetry
  data_files:
    - split: train
      path: poetry/data.parquet
- config_name: folklore
  data_files:
    - split: train
      path: folklore/data.parquet
- config_name: nark
  data_files:
    - split: train
      path: nark/data.parquet
- config_name: tarask
  data_files:
    - split: train
      path: tarask/data.parquet
- config_name: invariant
  data_files:
    - split: train
      path: invariant/data.parquet
- config_name: contrastive
  data_files:
    - split: train
      path: contrastive/data.parquet
---

# DualMova: Belarusian Dual-Norm Corpus v1

> Published: {now} | [ZorkaLabs](https://huggingface.co/ZorkaLabs)

## Dataset Description

**DualMova v1** is an open-source, high-integrity Belarusian text corpus providing
rigorous classification and tagging across the language's two codified orthographic standards:

| Tag | Orthographic Standard | Description |
|-----|----------------------|-------------|
| `<orth_nark>` | Official Standard (Narkamaŭka / NKBM-2008) | Official standard of the Republic of Belarus |
| `<orth_taras>` | Classical Standard (Taraškievica / BKP-2005) | Classical orthography (Branisłaŭ Taraškievič tradition) |
| `<orth_invariant>` | Certified Invariant Core | Common invariant core valid across both orthographies |

## Dataset Statistics

| Metric | Value |
|--------|-------|
| **Total Segments** | {total:,} |
| Official Standard (`nark`) | {nark:,} ({nark/max(total,1)*100:.1f}%) |
| Classical Standard (`tarask`) | {tarask:,} ({tarask/max(total,1)*100:.1f}%) |
| Certified Invariant (`invariant`) | {invariant:,} ({invariant/max(total,1)*100:.1f}%) |
| Prose Paragraphs | {prose:,} |
| Poetry Strophes | {poetry:,} |
| Folklore & Mythology | {folklore:,} |
| Contrastive Pairs | {contrastive:,} |

## Source Verification & Legal Framework

**100% Verified Public Domain & Open Knowledge:**
- Literary Texts: `knihi.com` («Беларуская Палічка»)
- Verification: Authors deceased prior to January 1, 1974 (Law of the Republic of Belarus № 262-Z).
- Folklore: Traditional folk art and folklore (Statutory public domain under Art. 7).
- Encyclopedic Corpora: `be.wikipedia.org` and `be-tarask.wikipedia.org` (CC BY-SA 4.0).

## Data Schema

```python
{{
    "id": "knihi_abc12345_0001",
    "text": "<orth_taras>Сьнег пакрыў зямлю белым дываном.</orth_taras>",
    "text_raw": "Сьнег пакрыў зямлю белым дываном.",
    "orthography": "tarask",         # "nark" | "tarask"
    "genre": "prose",                # "prose" | "poetry" | "folklore"
    "author": "Янка Купала",
    "author_slug": "Janka_Kupala",
    "author_death_year": 1942,
    "title": "Назва твору",
    "source_url": "https://knihi.com/...",
    "license": "public_domain",
    "source": "knihi.com",
    "is_augmented": False,
}}
```

## Quick Start

```python
from datasets import load_dataset

# Complete corpus
ds = load_dataset("{DATASET_ID}", "all")

# Classical Taraškievica standard
ds_tarask = load_dataset("{DATASET_ID}", "tarask")

# Official Narkamaŭka standard
ds_nark = load_dataset("{DATASET_ID}", "nark")

# Poetry strophes
ds_poetry = load_dataset("{DATASET_ID}", "poetry")
```
"""
    return card


def main():
    log.info("=" * 60)
    log.info("DualMova — Stage 4: Parquet Serialization")
    log.info("=" * 60)

    dataset_jsonl = PROCESSED_DIR / "dataset.jsonl"
    if not dataset_jsonl.exists():
        log.error("Dataset file not found: %s", dataset_jsonl)
        log.error("Please run 03_parse_and_tag.py before Stage 4.")
        sys.exit(1)

    log.info("Loading %s...", dataset_jsonl)
    all_records = load_jsonl(dataset_jsonl)
    log.info("Loaded %d records.", len(all_records))

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    prose = [r for r in all_records if r.get("genre") == "prose"]
    poetry = [r for r in all_records if r.get("genre") == "poetry"]
    folklore = [r for r in all_records if r.get("genre") == "folklore"]
    nark = [r for r in all_records if r.get("orthography") == "nark"]
    tarask = [r for r in all_records if r.get("orthography") == "tarask"]
    invariant = [r for r in all_records if r.get("orthography") == "invariant"]
    contrastive = [r for r in all_records if r.get("pair_id")]

    log.info("Serializing Parquet splits...")
    to_parquet(all_records,  EXPORT_DIR / "all",         "all")
    to_parquet(prose,        EXPORT_DIR / "prose",       "prose")
    to_parquet(poetry,       EXPORT_DIR / "poetry",      "poetry")
    to_parquet(folklore,     EXPORT_DIR / "folklore",    "folklore")
    to_parquet(nark,         EXPORT_DIR / "nark",        "nark")
    to_parquet(tarask,       EXPORT_DIR / "tarask",      "tarask")
    to_parquet(invariant,    EXPORT_DIR / "invariant",   "invariant")
    to_parquet(contrastive,  EXPORT_DIR / "contrastive", "contrastive")

    stats = {
        "total": len(all_records),
        "prose": len(prose),
        "poetry": len(poetry),
        "folklore": len(folklore),
        "nark": len(nark),
        "tarask": len(tarask),
        "invariant": len(invariant),
        "contrastive_pairs": len(contrastive),
    }

    card_path = EXPORT_DIR / "README.md"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(generate_dataset_card(stats))
    log.info("Dataset card written to: %s", card_path)

    stats_path = EXPORT_DIR / "export_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log.info("\n%s", "=" * 60)
    log.info("PARQUET SERIALIZATION COMPLETED")
    log.info("  Total records:         %d", stats["total"])
    log.info("  Narkamaŭka:            %d", stats["nark"])
    log.info("  Taraškievica:          %d", stats["tarask"])
    log.info("  Invariant Core:        %d", stats["invariant"])
    log.info("  Prose:                 %d", stats["prose"])
    log.info("  Poetry:                %d", stats["poetry"])
    log.info("  Folklore:              %d", stats["folklore"])
    log.info("  Export directory:      %s", EXPORT_DIR)


if __name__ == "__main__":
    main()
