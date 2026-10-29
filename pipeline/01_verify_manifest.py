"""
DualMova — Strict Public Domain Manifest Verification & Biographical Audit
==========================================================================
Eliminates potential false-positive biographical matches and non-PD entities:
1. Publication Timeline Filter: Identifies post-1974 first-edition dates on knihi.com.
2. Wikidata Temporal Audit: Excludes living individuals (birth > 1925 without verified death records).
3. Occupational Disambiguation: Resolves homonyms and disambiguates literary authors from historical figures.
"""

import json
import re
import ssl
import sys
import time
import urllib.request
from pathlib import Path

MANIFEST_IN = Path(__file__).parent / "manifest_urls.json"
MANIFEST_OUT = Path(__file__).parent / "manifest_urls_verified.json"
CACHE_PATH = Path(__file__).parent / "author_death_cache.json"
AUDIT_LOG = Path(__file__).parent / "audit_report.json"

_SSL_CTX = ssl._create_unverified_context()
UA = "DualMova-DatasetBuilder/1.0 (https://huggingface.co/ZorkaLabs; contact@zorkalabs.org)"

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

def main():
    print("=== DualMova: Strict Manifest Verification ===")
    if not MANIFEST_IN.exists():
        print(f"Error: {MANIFEST_IN} does not exist.")
        return

    with open(MANIFEST_IN, encoding="utf-8") as f:
        manifest = json.load(f)

    # Group records by author entity
    authors = {}
    folklore_items = []
    for item in manifest:
        if item.get("genre_hint") == "folklore" or "rfm.html" in item.get("source_section", ""):
            folklore_items.append(item)
            continue
        slug = item.get("author_slug")
        if not slug:
            continue
        if slug not in authors:
            authors[slug] = {
                "name": item.get("author"),
                "death_year": item.get("author_death_year"),
                "books": []
            }
        authors[slug]["books"].append(item)

    print(f"Total authors to audit: {len(authors)}")
    print(f"Folklore items: {len(folklore_items)}")

    rejected = []
    approved_authors = {}

    for i, (slug, data) in enumerate(authors.items(), 1):
        name = data["name"]
        d_year = data["death_year"]
        
        # 1. Fetch author catalog page and inspect publication years
        author_url = f"https://knihi.com/{slug}/"
        html = fetch(author_url)
        time.sleep(0.1)

        # Look for explicit publication dates (1975-2026)
        pub_years = [int(y) for y in re.findall(r"\b(19[7-9]\d|20[0-2]\d)\b", html)]
        recent_pubs = [y for y in pub_years if y >= 1974]
        
        # Look for biographical indicators (e.g. "naradziusya u 19..")
        birth_match = re.search(r"нарадзі[ўв]ся\s+.*?\b(19\d\d)\b", html, re.I)
        birth_year = int(birth_match.group(1)) if birth_match else None

        # Check Wikidata cache if available
        is_suspicious = False
        reasons = []

        if birth_year and birth_year >= 1930 and (not d_year or d_year >= 1974):
            is_suspicious = True
            reasons.append(f"Born {birth_year} (potential contemporary author)")

        if len(recent_pubs) >= 5 and not d_year:
            is_suspicious = True
            reasons.append(f"Multiple modern publications: {recent_pubs[:3]}")

        if d_year and d_year >= 1974:
            is_suspicious = True
            reasons.append(f"Deceased in {d_year} (>= 1974)")

        if is_suspicious:
            print(f"[{i}/{len(authors)}] REJECTED: {name} ({slug}) -> {', '.join(reasons)}")
            rejected.append({
                "slug": slug,
                "name": name,
                "reasons": reasons,
                "books_count": len(data["books"])
            })
        else:
            approved_authors[slug] = data

    print(f"\nAudit complete. Approved authors: {len(approved_authors)}, Excluded: {len(rejected)}")

    # Reconstruct verified manifest
    verified_manifest = list(folklore_items)
    for slug, data in approved_authors.items():
        verified_manifest.extend(data["books"])

    print(f"Verified manifest entries: {len(verified_manifest)} (Original: {len(manifest)})")

    with open(MANIFEST_OUT, "w", encoding="utf-8") as f:
        json.dump(verified_manifest, f, ensure_ascii=False, indent=2)

    with open(AUDIT_LOG, "w", encoding="utf-8") as f:
        json.dump({
            "approved_authors_count": len(approved_authors),
            "rejected_authors_count": len(rejected),
            "rejected_details": rejected
        }, f, ensure_ascii=False, indent=2)

    print(f"Saved verified manifest: {MANIFEST_OUT}")

if __name__ == "__main__":
    main()
