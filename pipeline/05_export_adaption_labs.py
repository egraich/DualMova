"""
DualMova — Stage 5: Export for Cloud Pretraining & SFT Alignment
================================================================
Constructs training splits tailored for large language model adaptation:
1. SFT Translation Split: Converts contrastive pairs (pair_id) into bidirectional
   chat dialogues formatted as {"messages": [...]} with clean text (text_raw)
   to ensure tag-leakage prevention during supervised instruction fine-tuning.
2. Packed Pretrain Split: Concatenates adjacent paragraphs from identical works into
   dense 4000-8000 character windows, preventing attention degradation and eliminating
   wasteful padding tokens over long context windows (e.g. 256k tokens).

Execution:
    python 05_export_adaption_labs.py
"""

import json
import random
import logging
from pathlib import Path
from collections import defaultdict

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    PA_AVAILABLE = True
except ImportError:
    PA_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent
PROCESSED_DIR = SCRIPT_DIR / "processed"
EXPORT_DIR = SCRIPT_DIR / "export" / "adaption_labs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# Prompt diversity for cross-norm translation alignment
PROMPTS_TO_TARASK = [
    "Перакладзі наступны тэкст на клясычны правапіс (тарашкевіцу):\n\n{text}",
    "Перапішы гэты ўрывак тарашкевіцай:\n\n{text}",
    "Перавядзі тэкст з афіцыйнага правапісу на клясычны (тарашкевіцу):\n\n{text}",
    "Адаптуй гэты тэкст пад нормы тарашкевіцы:\n\n{text}",
    "Перакладзі на беларускую мову (клясычны правапіс / тарашкевіца):\n\n{text}",
]

PROMPTS_TO_NARK = [
    "Перакладзі наступны тэкст на афіцыйны правапіс (наркамаўку):\n\n{text}",
    "Перапішы гэты ўрывак наркамаўкай:\n\n{text}",
    "Перавядзі тэкст з клясычнага правапісу на афіцыйную норму (наркамаўку):\n\n{text}",
    "Адаптуй гэты тэкст пад нормы сучаснага афіцыйнага правапісу:\n\n{text}",
    "Перакладзі на беларускую мову (афіцыйны правапіс / наркамаўка):\n\n{text}",
]


def export_sft_translations(records: list[dict], out_dir: Path):
    """
    Generates a supervised fine-tuning (SFT) dataset from contrastive pairs.
    Format: OpenAI / Together AI Chat JSONL ('messages').
    Assistant output is strictly clean authentic text (text_raw) without tag wrappers.
    """
    log.info("--- Generating SFT Translation Split ---")
    pairs = defaultdict(dict)
    for r in records:
        pid = r.get("pair_id")
        if not pid:
            continue
        orth = r.get("orthography")
        text_clean = r.get("text_raw", "").strip()
        if not text_clean:
            continue
        pairs[pid][orth] = text_clean

    sft_rows = []
    rng = random.Random(42)

    for pid, pair in pairs.items():
        if "nark" in pair and "tarask" in pair:
            nark_text = pair["nark"]
            tarask_text = pair["tarask"]

            # Direction 1: Official Standard -> Classical Standard
            p_to_tarask = rng.choice(PROMPTS_TO_TARASK).format(text=nark_text)
            sft_rows.append({
                "messages": [
                    {"role": "user", "content": p_to_tarask},
                    {"role": "assistant", "content": tarask_text},
                ],
                "direction": "nark2tarask",
                "pair_id": pid,
            })

            # Direction 2: Classical Standard -> Official Standard
            p_to_nark = rng.choice(PROMPTS_TO_NARK).format(text=tarask_text)
            sft_rows.append({
                "messages": [
                    {"role": "user", "content": p_to_nark},
                    {"role": "assistant", "content": nark_text},
                ],
                "direction": "tarask2nark",
                "pair_id": pid,
            })

    log.info("Constructed %d SFT dialogues from %d contrastive pairs", len(sft_rows), len(pairs))
    rng.shuffle(sft_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "sft_translations.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in sft_rows:
            f.write(json.dumps({"messages": row["messages"]}, ensure_ascii=False) + "\n")
    log.info("Saved JSONL to %s (size: %.2f MB)", jsonl_path, jsonl_path.stat().st_size / 1e6)

    if PA_AVAILABLE:
        df = pd.DataFrame([{"messages": r["messages"]} for r in sft_rows])
        parquet_path = out_dir / "sft_translations.parquet"
        df.to_parquet(parquet_path, compression="zstd", index=False)
        log.info("Saved Parquet to %s (size: %.2f MB)", parquet_path, parquet_path.stat().st_size / 1e6)


def export_packed_pretrain(records: list[dict], out_dir: Path, target_chars: int = 6000):
    """
    Concatenates adjacent paragraphs of the same document into continuous blocks.
    Each block is prefixed by metadata headers while avoiding intrusive XML tags.
    """
    log.info("--- Generating Packed Pretrain Split (window ~%d chars) ---", target_chars)
    books = defaultdict(list)
    for r in records:
        if r.get("is_augmented", False):
            continue
        src = r.get("source_url") or r.get("author", "unknown")
        books[src].append(r)

    packed_records = []
    doc_id = 0

    for src, paras in books.items():
        if not paras:
            continue

        paras.sort(key=lambda x: str(x.get("id", "")))

        current_block = []
        current_len = 0
        current_orth = None
        current_author = paras[0].get("author", "")
        current_title = paras[0].get("title", "")

        for p in paras:
            t = p.get("text_raw", "").strip()
            orth = p.get("orthography", "nark")
            if not t:
                continue

            # Orthography boundary or token length threshold triggers block serialization
            if (current_orth and orth != current_orth) or (current_len + len(t) > target_chars and current_block):
                norm_label = "Тарашкевіца" if current_orth == "tarask" else "Наркамаўка"
                header = f"[Правапіс: {norm_label} | Твор: {current_title} | Аўтар: {current_author}]\n\n"
                full_text = header + "\n\n".join(current_block)
                packed_records.append({
                    "id": f"packed_{doc_id:06d}",
                    "text": full_text,
                    "orthography": current_orth,
                    "char_count": len(full_text),
                    "author": current_author,
                    "title": current_title,
                })
                doc_id += 1
                current_block = []
                current_len = 0

            current_orth = orth
            current_block.append(t)
            current_len += len(t)

        if current_block:
            norm_label = "Тарашкевіца" if current_orth == "tarask" else "Наркамаўка"
            header = f"[Правапіс: {norm_label} | Твор: {current_title} | Аўтар: {current_author}]\n\n"
            full_text = header + "\n\n".join(current_block)
            packed_records.append({
                "id": f"packed_{doc_id:06d}",
                "text": full_text,
                "orthography": current_orth,
                "char_count": len(full_text),
                "author": current_author,
                "title": current_title,
            })
            doc_id += 1

    log.info("Constructed %d packed pretraining documents", len(packed_records))
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "packed_pretrain.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in packed_records:
            f.write(json.dumps({"text": r["text"]}, ensure_ascii=False) + "\n")
    log.info("Saved JSONL to %s (size: %.2f MB)", jsonl_path, jsonl_path.stat().st_size / 1e6)

    if PA_AVAILABLE:
        df = pd.DataFrame(packed_records)
        parquet_path = out_dir / "packed_pretrain.parquet"
        df.to_parquet(parquet_path, compression="zstd", index=False)
        log.info("Saved Parquet to %s (size: %.2f MB)", parquet_path, parquet_path.stat().st_size / 1e6)


def main():
    jsonl_path = PROCESSED_DIR / "dataset.jsonl"
    if not jsonl_path.exists():
        log.error("File %s not found.", jsonl_path)
        return

    log.info("Loading %s...", jsonl_path)
    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    log.info("Loaded %d records.", len(records))
    export_sft_translations(records, EXPORT_DIR)
    export_packed_pretrain(records, EXPORT_DIR)
    log.info("Serialization for cloud training completed successfully.")


if __name__ == "__main__":
    main()
