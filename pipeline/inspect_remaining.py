import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import OrthographyRouter

router = OrthographyRouter()
reasons = Counter()
samples_by_reason = {}

rej_path = Path("/root/dualmova/pipeline/processed/rejected.jsonl")
if not rej_path.exists():
    rej_path = Path(__file__).parent / "processed" / "rejected.jsonl"

with open(rej_path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        text = row.get("text_raw", "")
        res = router.route(text)
        if res.label == "rejected":
            r = res.metrics.get("reason", "unknown")
            reasons[r] += 1
            if r not in samples_by_reason:
                samples_by_reason[r] = []
            if len(samples_by_reason[r]) < 3:
                samples_by_reason[r].append({
                    "title": row.get("title"),
                    "url": row.get("source_url"),
                    "text": text[:200],
                    "metrics": res.metrics
                })

print("NEW REASONS BREAKDOWN:")
for r, cnt in reasons.most_common():
    print(f"  {r}: {cnt} ({cnt/sum(reasons.values())*100:.2f}%)")

print("\nSAMPLES PER REASON:")
for r, samps in samples_by_reason.items():
    print(f"\n=== Reason: {r} ===")
    for s in samps:
        print(f"  [Book: {s['title']}] URL: {s['url']}")
        print(f"  Features: {s['metrics'].get('features')}")
        print(f"  Snippet: {s['text']}...\n")
