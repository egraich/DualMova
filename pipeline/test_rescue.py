import json
import re
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import OrthographyRouter

# Create updated classifier with the refined palatal regex and seams
router = OrthographyRouter()

# Let's inspect how many rows from rejected.jsonl are now accepted!
rej_path = Path("/root/dualmova/pipeline/processed/rejected.jsonl")
if not rej_path.exists():
    rej_path = Path(__file__).parent / "processed" / "rejected.jsonl"

rescued_counts = Counter()
rescued_nark = 0
rescued_taras = 0
still_rejected = 0

with open(rej_path, "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        text = row.get("text_raw", "")
        res = router.route(text)
        if res.label in ("nark", "tarask"):
            rescued_counts[res.label] += 1
        else:
            still_rejected += 1

print(f"Total evaluated from rejected.jsonl: {sum(rescued_counts.values()) + still_rejected}")
print(f"Rescued: {dict(rescued_counts)} (Total rescued: {sum(rescued_counts.values())})")
print(f"Still rejected: {still_rejected}")
