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

    # Zero-Distance Identity Pairs (15-20% of SFT corpus to prevent hypercorrection hallucinations)
    inv_records = [r for r in records if r.get("orthography") == "invariant" and r.get("text_raw")]
    if inv_records and sft_rows:
        target_inv_count = min(len(inv_records), max(int(len(sft_rows) * 0.18), 1))
        sampled_inv = rng.sample(inv_records, target_inv_count) if target_inv_count < len(inv_records) else inv_records
        for inv_rec in sampled_inv:
            inv_text = inv_rec["text_raw"].strip()
            # Ask for translation to either norm; the correct target is identically unchanged!
            p_inv = rng.choice(PROMPTS_TO_TARASK if rng.random() < 0.5 else PROMPTS_TO_NARK).format(text=inv_text)
            sft_rows.append({
                "messages": [
                    {"role": "user", "content": p_inv},
                    {"role": "assistant", "content": inv_text},
                ],
                "direction": "identity_invariant",
                "pair_id": f"inv_{inv_rec.get('id', '')}",
            })
        log.info("Integrated %d Zero-Distance identity invariant pairs (%.1f%% of SFT)", target_inv_count, target_inv_count / max(len(sft_rows), 1) * 100)

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
                if current_orth == "tarask":
                    norm_label = "Тарашкевіца"
                elif current_orth == "invariant":
                    norm_label = "Агульны інварыянт"
                else:
                    norm_label = "Наркамаўка"
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
            if current_orth == "tarask":
                norm_label = "Тарашкевіца"
            elif current_orth == "invariant":
                norm_label = "Агульны інварыянт"
            else:
                norm_label = "Наркамаўка"
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


def export_dpo_split(records: list[dict], rejected_path: Path, out_dir: Path):
    """
    Generates Direct Preference Optimization (DPO) preference pairs:
      {"prompt": ..., "chosen": text_authentic, "rejected": text_chimera_or_corrupted}
    Trains the LLM to strictly penalize orthographic chimeras and cross-norm leakage.
    """
    log.info("--- Generating DPO Chimera-Penalty Split ---")
    if not rejected_path.exists():
        log.warning("Rejected file %s not found. Skipping DPO export.", rejected_path)
        return

    chimeras = []
    with open(rejected_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
                if rec.get("reject_reason") == "REJECT_ORTHOGRAPHIC_CHIMERA":
                    txt = rec.get("text_raw", "").strip()
                    if txt:
                        chimeras.append(txt)
            except json.JSONDecodeError:
                continue

    log.info("Found %d rejected chimera candidates for DPO negative samples", len(chimeras))
    if not chimeras:
        return

    rng = random.Random(42)
    contrastive_samples = [r.get("text_raw", "").strip() for r in records if r.get("pair_id") and r.get("text_raw")]
    if not contrastive_samples:
        contrastive_samples = [r.get("text_raw", "").strip() for r in records if r.get("text_raw")]

    dpo_rows = []
    for chimera in chimeras:
        chosen = rng.choice(contrastive_samples)
        prompt = "Напішы ці адрэдагуй тэкст на бездакорнай беларускай літаратурнай мове:"
        dpo_rows.append({
            "prompt": prompt,
            "chosen": chosen,
            "rejected": chimera,
            "negative_type": "orthographic_chimera",
        })

    rng.shuffle(dpo_rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    dpo_path = out_dir / "dpo_alignment.jsonl"
    with open(dpo_path, "w", encoding="utf-8") as f:
        for r in dpo_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("Saved DPO dataset to %s (%d pairs, size: %.2f MB)", dpo_path, len(dpo_rows), dpo_path.stat().st_size / 1e6)

    if PA_AVAILABLE:
        df = pd.DataFrame(dpo_rows)
        parquet_path = out_dir / "dpo_alignment.parquet"
        df.to_parquet(parquet_path, compression="zstd", index=False)
        log.info("Saved DPO Parquet to %s (size: %.2f MB)", parquet_path, parquet_path.stat().st_size / 1e6)


def main():
    jsonl_path = PROCESSED_DIR / "dataset.jsonl"
    rejected_path = PROCESSED_DIR / "rejected.jsonl"
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
    export_dpo_split(records, rejected_path, EXPORT_DIR)
    log.info("Serialization for cloud training completed successfully.")


if __name__ == "__main__":
    main()
