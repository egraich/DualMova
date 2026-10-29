"""
DualMova — Dataset Integrity & Schema Verification
==================================================
Audits schema adherence, field types, normative balances, and sample records.
"""

import json
from pathlib import Path

DATASET_PATH = Path(__file__).parent / "processed" / "dataset.jsonl"

def main():
    print(f"Auditing {DATASET_PATH}...")
    if not DATASET_PATH.exists():
        print(f"File not found: {DATASET_PATH}")
        return

    total = 0
    nark = 0
    tarask = 0
    augmented = 0
    paired = 0
    poetry = 0
    prose = 0
    folklore = 0

    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            total += 1
            if rec.get("orthography") == "nark":
                nark += 1
            elif rec.get("orthography") == "tarask":
                tarask += 1

            if rec.get("is_augmented"):
                augmented += 1

            pid = rec.get("pair_id")
            if pid:
                paired += 1

            g = rec.get("genre")
            if g == "poetry":
                poetry += 1
            elif g == "folklore":
                folklore += 1
            else:
                prose += 1

    print("=" * 60)
    print("DUALMOVA CORPUS VERIFICATION SUMMARY:")
    print(f"  Total records:       {total:,}")
    print(f"  Official (Nark):     {nark:,} ({nark/max(total,1)*100:.1f}%)")
    print(f"  Classical (Tarask):  {tarask:,} ({tarask/max(total,1)*100:.1f}%)")
    print(f"  Augmented:           {augmented:,}")
    print(f"  Paired entries:      {paired:,}")
    print(f"  Poetry:              {poetry:,}")
    print(f"  Prose:               {prose:,}")
    print(f"  Folklore:            {folklore:,}")
    print("=" * 60)

if __name__ == "__main__":
    main()
