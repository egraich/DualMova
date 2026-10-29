# DualMova Dataset Schema Specification

## 1. Overview

DualMova datasets are serialized in **Apache Parquet** format compressed with **Zstandard (ZSTD) Level 9**. The corpus follows a long-format schema where each record represents a single paragraph or poetic strophe.

---

## 2. Column Specification

| Column | Type | Nullable | Example | Description |
| :--- | :--- | :---: | :--- | :--- |
| `id` | `string` | No | `"knihi_605f32f3_0001"` | Globally unique record identifier |
| `text` | `string` | No | `"<orth_nark>Жыў сабе дзед...</orth_nark>"` | Text wrapped with normative orthography tag |
| `text_raw` | `string` | No | `"Жыў сабе дзед..."` | Clean authentic text without tag wrappers |
| `orthography` | `string` | No | `"nark"` | Norm enum: `"nark"` (Narkamaŭka) or `"tarask"` (Taraškievica) |
| `is_augmented` | `boolean` | No | `false` | `true` if generated via Dual-Norm Augmentation |
| `pair_id` | `string` | Yes | `"9ea5076d6b745684"` | Shared hex hash linking parallel `nark` ↔ `tarask` variants |
| `genre` | `string` | No | `"prose"` | Genre enum: `"prose"`, `"poetry"`, or `"folklore"` |
| `author` | `string` | No | `"Янка Купала"` | Author name (or `"Вікіпедыя"` / `"Беларуская Народная Творчасць"`) |
| `author_slug` | `string` | No | `"Janka_Kupala"` | Normalized author slug |
| `author_death_year`| `int32` | Yes | `1942` | Year of author's death (-1 / null for folklore / wiki) |
| `title` | `string` | No | `"На ростанях"` | Title of the work or article |
| `source_url` | `string` | No | `"https://knihi.com/..."` | Permanent URL of the source document |
| `license` | `string` | No | `"public_domain"` | License string (`"public_domain"` or `"cc-by-sa-4.0"`) |
| `source` | `string` | No | `"knihi.com"` | Source provider (`"knihi.com"`, `"bewiki"`, etc.) |
| `lang` | `string` | No | `"be"` | ISO 639-1 language code (always `"be"`) |
| `char_count` | `int32` | No | `412` | Character count of `text_raw` |
| `word_count` | `int32` | No | `68` | Belarusian word count of `text_raw` |

---

## 3. Hugging Face Dataset Configurations

The dataset card provides 7 official split configurations for community researchers:

```python
from datasets import load_dataset

# Complete corpus
ds_all = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "all")

# Classical Taraškievica only
ds_tarask = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "tarask")

# Official Narkamaŭka only
ds_nark = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "nark")

# Poetry strophes only
ds_poetry = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "poetry")

# Folklore & Mythology
ds_folklore = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "folklore")

# Contrastive pairs for DPO/RLHF (only rows with pair_id)
ds_pairs = load_dataset("ZorkaLabs/belarusian-dualnorm-corpus-v1", "contrastive")
```

---

## 4. Cloud LLM & Managed Platforms (Adaption Labs / Together AI)

For managed fine-tuning platforms where users cannot supply custom PyTorch DataCollators or modify tokenizers, DualMova provides zero-configuration turnkey exports:

### 4.1 SFT Instruction-Tuning (`sft_translations`)
- **Format:** OpenAI / Together AI Chat JSONL (`{"messages": [...]}`).
- **Contents:** High-integrity bidirectional translation and norm-conversion dialogues derived strictly from authentic interwiki alignments (Wikidata QID pairs) and 100% dictionary-certified sentences. Heuristic regex pseudo-translations are completely eliminated.
- **Safety Guarantee:** Assistant completions are strictly pure authentic Belarusian (`text_raw`) with **zero closing tag leakage** (`</orth_*>` tags are completely eliminated from assistant targets) and **zero mixed-orthography chimeras**.
- **Prompt Variations:** Natural prompt variations across 5 templates per direction to prevent prompt memorization.

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Перакладзі наступны тэкст на клясычны правапіс (тарашкевіцу):\n\nЧутно была ў песні..."
    },
    {
      "role": "assistant",
      "content": "Чутно была ў песьні..."
    }
  ]
}
```

### 4.2 Document-Level Sequence Packing (`packed_pretrain`)
- **Format:** Causal LM JSONL (`{"text": "..."}`).
- **Contents:** 115,329 contiguous document blocks stitched up to ~6,000 characters (~1,500–2,000 tokens).
- **Architecture Fit:** Optimized for large context windows (Gemma-4 31B 256k window). Prevents short-fragment narrative degradation and eliminates compute wasted on attention mask padding.
- **Prefix Header:** Prefixed with standard document metadata `[Правапіс: ... | Твор: ... | Аўтар: ...]`.

