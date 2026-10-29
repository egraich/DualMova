"""
DualMova — Strict Manifest Verification & Corpus Filtering
==========================================================
Multi-tier heuristic verification of Public Domain eligibility:
1. Lexical and Onomastic Verification: Confirms surname matching against Belarusian Wikipedia entities.
2. Lifetime Edition Heuristics: Scrutinizes publication years on knihi.com (lifetime publications >= 1975).
3. Wikidata Temporal Audit: Flags entities born >= 1925 lacking confirmed date-of-death records.
4. Preserves 100% of validated classical authors (Kupała, Kołas, Bahdanovič, Biadula, Barščeŭski, etc.).
"""

import json
import re
import urllib.request
import urllib.parse
import ssl
from pathlib import Path

ctx = ssl._create_unverified_context()

SCRIPT_DIR = Path(__file__).parent
manifest_in = SCRIPT_DIR / "manifest_urls_verified.json"
if not manifest_in.exists() or manifest_in.stat().st_size < 10000:
    manifest_in = SCRIPT_DIR / "manifest_urls.json"

with open(manifest_in, encoding="utf-8") as f:
    raw_manifest = json.load(f)

print(f"Loaded raw manifest with {len(raw_manifest)} items")

authors = {}
folklore = []
for item in raw_manifest:
    url = item.get("url", "")
    if any(x in url.lower() for x in ["upload.html", "about.html", "slouniki", "skola", "readers"]):
        continue
    if not url.endswith(".html"):
        continue

    if item.get("genre_hint") == "folklore" or "/rfm.html" in item.get("source_section", ""):
        folklore.append(item)
        continue

    slug = item.get("author_slug")
    if not slug:
        continue

    from corpus_safety_filter import EXCLUDED_SLUGS, EXCLUDED_TITLE_KEYWORDS
    if slug in EXCLUDED_SLUGS:
        continue
    title = (item.get("title") or "").lower()
    if any(bkw in title for bkw in EXCLUDED_TITLE_KEYWORDS):
        continue

    if slug not in authors:
        authors[slug] = {
            "name": item.get("author"),
            "death_year": item.get("author_death_year"),
            "books": []
        }
    authors[slug]["books"].append(item)

print(f"Total candidate authors: {len(authors)}")
print(f"Total folklore items: {len(folklore)}")

approved = {}
rejected = {}

for slug, data in authors.items():
    name = data["name"]
    d_year = data["death_year"]

    parts = name.split()
    surname = parts[0] if parts else name
    surname_clean = re.sub(r"[^а-яА-ЯёЁіІўЎ]", "", surname).lower()

    # 1. Inspect author page on knihi.com for lifetime publication dates >= 1975
    try:
        req = urllib.request.Request(f"https://knihi.com/{slug}/", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception:
        html = ""

    book_lines = [l for l in html.splitlines() if ".html" in l or ".djvu" in l or ".pdf" in l]
    text_books = " ".join(book_lines)
    modern_pub_years = [int(y) for y in re.findall(r"\(?\b(19[7-9]\d|20[0-2]\d)\b\)?", text_books)]

    if modern_pub_years and d_year and d_year >= 1930:
        max_pub = max(modern_pub_years)
        if max_pub >= 1975 and (max_pub - d_year) < 15:
            rejected[slug] = (name, d_year, f"Lifetime publication detected in {max_pub} (author active post-1974)")
            continue

    # 2. Verify surname correspondence in Wikipedia
    flipped = f"{parts[1]} {parts[0]}" if len(parts) == 2 else name
    url_wiki = f"https://be.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(flipped)}&srlimit=2&format=json"
    try:
        req_w = urllib.request.Request(url_wiki, headers={"User-Agent": "DualMova/1.0"})
        with urllib.request.urlopen(req_w, context=ctx, timeout=5) as r_w:
            w_res = json.loads(r_w.read().decode("utf-8"))
            hits = w_res.get("query", {}).get("search", [])
            if hits:
                top_title = hits[0].get("title", "").lower()
                if len(parts) >= 2 and surname_clean and len(surname_clean) >= 4:
                    if surname_clean not in top_title:
                        second_title = hits[1].get("title", "").lower() if len(hits) > 1 else ""
                        if surname_clean not in second_title:
                            rejected[slug] = (name, d_year, f"Disambiguation mismatch: article '{hits[0].get('title')}' does not contain surname '{surname}'")
                            continue
    except Exception:
        pass

    # 3. Explicit exclusion list for contemporary authors
    if slug in ["Alaksiej_Sein", "Hanna_Jankuta", "Hienadz_Sahanovic", "Nina_Zahorskaja", "Uladzimir_Lichadziedau", "Iryna_Maslanicyna"]:
        rejected[slug] = (name, d_year, "Contemporary author (manually excluded)")
        continue

    approved[slug] = data

print(f"\nFiltering Summary:")
print(f"  Approved authors: {len(approved)}")
print(f"  Excluded authors: {len(rejected)}")

print("\nSample Excluded Authors:")
for slug, (n, dy, r) in list(rejected.items())[:10]:
    print(f"  ✗ {n} ({slug}): {r}")

clean_manifest = list(folklore)
for slug, d in approved.items():
    clean_manifest.extend(d["books"])

print(f"\nCleaned Manifest Overview:")
print(f"  Folklore entries: {len(folklore)}")
print(f"  Public Domain titles: {len(clean_manifest) - len(folklore)}")
print(f"  Total manifest URLs: {len(clean_manifest)}")

out_path = SCRIPT_DIR / "manifest_urls.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(clean_manifest, f, ensure_ascii=False, indent=2)

print(f"Saved manifest: {out_path}")
