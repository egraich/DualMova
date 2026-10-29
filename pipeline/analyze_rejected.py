import json
from collections import Counter
from pathlib import Path

rej_path = Path("/root/dualmova/pipeline/processed/rejected.jsonl")
if not rej_path.exists():
    rej_path = Path(__file__).parent / "processed" / "rejected.jsonl"

c = Counter()
features_taras_fake = Counter()
features_nark_fake = Counter()

with open(rej_path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        reason = row.get("reject_reason") or row.get("metrics", {}).get("reason")
        c[reason] += 1
        if reason in ("REJECT_LOW_CONFIDENCE_AMBIGUOUS", "REJECT_ORTHOGRAPHIC_CHIMERA"):
            feats = row.get("metrics", {}).get("features", {})
            for t in feats.get("taras", []):
                features_taras_fake[t] += 1
            for n in feats.get("nark", []):
                features_nark_fake[n] += 1

print("TOTAL REJECTED:", sum(c.values()))
print("\nREASONS BREAKDOWN:")
for r, cnt in c.most_common():
    print(f"  {r}: {cnt} ({cnt/sum(c.values())*100:.2f}%)")

print("\nTOP TARAS FEATURES IN REJECTED:")
for feat, cnt in features_taras_fake.most_common(25):
    print(f"  {feat}: {cnt}")

print("\nTOP NARK FEATURES IN REJECTED:")
for feat, cnt in features_nark_fake.most_common(25):
    print(f"  {feat}: {cnt}")
