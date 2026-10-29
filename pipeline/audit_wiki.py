import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import OrthographyRouter

wordlist_path = Path(__file__).parent.parent / "dictionaries" / "tarask" / "wordlist.txt"
if not wordlist_path.exists():
    wordlist_path = Path("/root/dualmova/dictionaries/tarask/wordlist.txt")

router = OrthographyRouter(tarask_wordlist_path=wordlist_path if wordlist_path.exists() else None)

wiki_path = Path(__file__).parent / "processed" / "dataset_wiki.jsonl"
if not wiki_path.exists():
    wiki_path = Path("/root/dualmova/pipeline/processed/dataset_wiki.jsonl")

counts = Counter()
nark_examples = []
rejected_reasons = Counter()

total = 0
print(f"Starting audit on {wiki_path}...")
with open(wiki_path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        if row.get("source") != "be_x_oldwiki":
            continue
        total += 1
        text = row.get("text_raw", "")
        res = router.route(text)
        counts[res.label] += 1

        if res.label == "rejected":
            reason = res.metrics.get("reason", "unknown")
            rejected_reasons[reason] += 1
        elif res.label == "nark":
            if len(nark_examples) < 25:
                nark_examples.append({
                    "title": row.get("title"),
                    "text": text,
                    "metrics": res.metrics
                })

        if total % 10000 == 0:
            print(f"Processed {total} paragraphs... Current counts: {dict(counts)}")

print("=" * 60)
print(f"TOTAL be_x_oldwiki PARAGRAPHS AUDITED: {total}")
print(f"Results: {dict(counts)}")
print(f"Rejected reasons: {dict(rejected_reasons)}")
print("=" * 60)
print(f"NARK EXAMPLES DETECTED ({len(nark_examples)}):")
for i, ex in enumerate(nark_examples[:10]):
    print(f"\n--- #{i+1} [Article: {ex['title']}] ---")
    print(f"Features: {ex['metrics'].get('features')}")
    print(f"Confidence: {ex['metrics'].get('confidence'):.4f}, Log-Odds: {ex['metrics'].get('effective_log_odds'):.4f}")
    print(f"Text snippet:\n{ex['text'][:250]}...")
