"""
DualMova — Stage 1: Public Domain Manifest Construction
========================================================
Traverses the author directory at knihi.com/autary.html, verifies author
biographical records and death dates via Wikipedia and Wikidata APIs,
retains strictly Public Domain entities (year of death < 1974), and serializes
the verified URL manifest to manifest_urls.json.

Execution:
    python 01_build_manifest.py

Outputs:
    DualMova/pipeline/manifest_urls.json
    DualMova/pipeline/author_death_cache.json

Requirements:
    requests beautifulsoup4
"""

import json
import ssl
import time
import re
import sys
import logging
from pathlib import Path
from urllib.parse import quote
import urllib.request
import urllib.error

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = "https://knihi.com"
AUTHORS_URL = "https://knihi.com/autary.html"
FOLKLORE_SECTIONS = ["/rfm.html"]

# Public Domain cut-off threshold: author deceased strictly before this year
PUBLIC_DOMAIN_DEATH_YEAR_LIMIT = 1974

CRAWL_DELAY_SECONDS = 2.0
WIKI_DELAY_SECONDS = 0.5

OUTPUT_DIR = Path(__file__).parent
MANIFEST_PATH = OUTPUT_DIR / "manifest_urls.json"
AUTHOR_CACHE_PATH = OUTPUT_DIR / "author_death_cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "01_manifest.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

_SSL_CTX = ssl._create_unverified_context()


# ── HTTP Helpers ──────────────────────────────────────────────────────────────

def fetch_html(url: str, timeout: int = 15) -> str:
    """Fetches HTML content with automatic fallback encoding detection."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DualMova-DatasetBuilder/1.0 (ZorkaLabs; educational research)"},
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            raw = resp.read()
            for enc in ("utf-8", "windows-1251", "iso-8859-1"):
                try:
                    return raw.decode(enc)
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        log.warning("Failed to fetch %s: %s", url, e)
        return ""


WIKIMEDIA_USER_AGENT = "DualMova-DatasetBuilder/1.0 (https://huggingface.co/ZorkaLabs; mailto:dataset@zorkalabs.org)"


def wiki_api_get(params: dict, timeout: int = 15, max_retries: int = 3) -> dict:
    """Executes a GET request against the Wikipedia API with exponential backoff on HTTP 429."""
    qs = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    url = f"https://be.wikipedia.org/w/api.php?{qs}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": WIKIMEDIA_USER_AGENT},
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 5 * (attempt + 1)
                log.warning("Wikipedia 429 (Rate Limit). Waiting %d seconds...", wait_time)
                time.sleep(wait_time)
            else:
                log.debug("Wikipedia HTTP error %s for %s", e.code, params)
                return {}
        except Exception as e:
            log.debug("Wikipedia API error for %s: %s", params, e)
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {}
    return {}


def wikidata_entity_json(qid: str, timeout: int = 15, max_retries: int = 3) -> dict:
    """Retrieves full entity claims from the Wikidata REST API."""
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": WIKIMEDIA_USER_AGENT},
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("entities", {}).get(qid, {})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 5 * (attempt + 1)
                log.warning("Wikidata 429 (Rate Limit) for %s. Waiting %d seconds...", qid, wait_time)
                time.sleep(wait_time)
            else:
                log.debug("Wikidata REST API HTTP %s for %s", e.code, qid)
                return {}
        except Exception as e:
            log.debug("Wikidata REST API error for %s: %s", qid, e)
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {}
    return {}


# ── Directory Parsers ─────────────────────────────────────────────────────────

def parse_authors_list(html: str) -> list[dict]:
    """
    Parses /autary.html and returns cataloged authors:
    {'slug': '/Janka_Kupala/', 'name': 'Купала Янка', 'url_slug': 'Janka_Kupala'}
    """
    authors = []
    seen = set()

    pattern = re.compile(r'href="(/[A-Za-zА-Яа-яёЁіІўЎ][^/"]+/)">([^<]+)</a>')
    for m in pattern.finditer(html):
        href, name = m.group(1), m.group(2).strip()
        if href in seen:
            continue
        slug = href.strip("/")
        if not slug or "/" in slug or "." in slug:
            continue
        if re.search(r"[А-Яа-яёЁіІўЎ]", name):
            seen.add(href)
            authors.append({
                "slug": href,
                "url_slug": slug,
                "name": name,
            })

    log.info("Parsed %d authors from autary.html", len(authors))
    return authors


def parse_author_books(html: str, author_slug: str) -> list[dict]:
    """
    Parses author catalog and extracts book URLs.
    Filters out raster scans (_scan) and binary formats.
    """
    books = []
    seen = set()

    pattern = re.compile(
        r'href="(/?' + re.escape(author_slug) + r'/([^"]+\.html))"[^>]*>([^<]+)</a>'
    )
    for m in re.finditer(pattern, html):
        path, filename, title = m.group(1), m.group(2), m.group(3).strip()
        if path in seen:
            continue
        seen.add(path)
        if "scan" in filename.lower():
            continue
        full_url = BASE_URL + path if path.startswith("/") else path
        books.append({
            "title": title,
            "url": full_url,
            "filename": filename,
        })

    return books


def parse_folklore_books(html: str, section_url: str) -> list[dict]:
    """Parses folklore and ethnographic sections."""
    books = []
    seen = set()

    pattern = re.compile(r'href="(/[^"]+\.html)"[^>]*>([^<]+)</a>')
    for m in re.finditer(pattern, html):
        path, title = m.group(1), m.group(2).strip()
        if any(s in path.lower() for s in ["/slouniki", "/autary", "/rfm", "/skola", "/readers", "upload", "about", "donate"]):
            continue
        if path in seen:
            continue
        seen.add(path)
        full_url = BASE_URL + path
        books.append({
            "title": title,
            "url": full_url,
            "author": "Беларуская Народная Творчасць",
            "author_death_year": None,
            "genre_hint": "folklore",
            "license": "public_domain",
            "source_section": section_url,
        })

    return books


# ── Wikidata Biographical Resolver ───────────────────────────────────────────

def _flip_name(name: str) -> str:
    """'Купала Янка' → 'Янка Купала'."""
    parts = name.split()
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name


def _wikidata_entity_search(query: str, timeout: int = 15, max_retries: int = 3) -> list[str]:
    """Queries wbsearchentities directly with retry logic."""
    url = (
        f"https://www.wikidata.org/w/api.php?"
        f"action=wbsearchentities&search={quote(query)}"
        f"&language=be&uselang=be&type=item&limit=3&format=json"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": WIKIMEDIA_USER_AGENT},
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [item["id"] for item in data.get("search", [])]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait_time = 5 * (attempt + 1)
                log.warning("Wikidata 429 for %s. Waiting %d seconds...", query, wait_time)
                time.sleep(wait_time)
            else:
                return []
        except Exception as e:
            log.debug("Wikidata error for %s: %s", query, e)
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return []
    return []


def _get_death_year_from_qid(qid: str) -> int | None:
    """Extracts date of death (property P570) from entity claims."""
    entity = wikidata_entity_json(qid)
    time.sleep(WIKI_DELAY_SECONDS)

    claims = entity.get("claims", {})
    p570 = claims.get("P570", [])
    if p570:
        time_value = (p570[0].get("mainsnak", {})
                      .get("datavalue", {})
                      .get("value", {})
                      .get("time", ""))
        if time_value:
            m = re.match(r"[+-]?(\d{1,4})-", time_value)
            if m:
                return int(m.group(1))
    return None


def _wiki_titles_for_query(query: str) -> list[str]:
    """Searches be.wikipedia.org for matching article titles."""
    data = wiki_api_get({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": "3",
        "format": "json",
    })
    time.sleep(WIKI_DELAY_SECONDS)
    return [r.get("title", "") for r in data.get("query", {}).get("search", [])]


def _qids_from_wiki_titles(titles: list[str]) -> list[str]:
    """Resolves Wikidata entity IDs from Wikipedia titles."""
    qids = []
    for title in titles:
        props = wiki_api_get({
            "action": "query",
            "titles": title,
            "prop": "pageprops",
            "format": "json",
        })
        time.sleep(WIKI_DELAY_SECONDS)

        pages = props.get("query", {}).get("pages", {})
        for page_data in pages.values():
            qid = page_data.get("pageprops", {}).get("wikibase_item", "")
            if qid:
                qids.append(qid)
    return qids


def get_death_year_from_wikidata(slug: str, cache: dict,
                                  cyrillic_name: str = "") -> int | None:
    """
    Resolves an author's year of death using prioritized fallback cascades.
    """
    if slug in cache and cache[slug] is not None:
        return cache[slug]

    candidates_qids: list[str] = []

    # Strategy 1 & 2: be.wikipedia.org direct queries
    if cyrillic_name:
        flipped = _flip_name(cyrillic_name)
        queries = [flipped]
        if flipped != cyrillic_name:
            queries.append(cyrillic_name)

        titles = []
        for q in queries:
            for t in _wiki_titles_for_query(q):
                if t not in titles:
                    titles.append(t)

        candidates_qids.extend(_qids_from_wiki_titles(titles))

    # Strategy 3: Wikidata entity search by Cyrillic name
    if not candidates_qids and cyrillic_name:
        for q in [flipped, cyrillic_name]:
            candidates_qids.extend(_wikidata_entity_search(q))
            time.sleep(WIKI_DELAY_SECONDS)
            if candidates_qids:
                break

    # Strategy 4: Fallback entity search by Latin slug
    if not candidates_qids:
        latin_name = slug.replace("_", " ")
        candidates_qids.extend(_wikidata_entity_search(latin_name))
        time.sleep(WIKI_DELAY_SECONDS)

    # Evaluate P570 across candidate QIDs
    seen = set()
    for qid in candidates_qids:
        if qid in seen:
            continue
        seen.add(qid)
        year = _get_death_year_from_qid(qid)
        if year is not None:
            cache[slug] = year
            return year

    cache[slug] = None
    return None


def is_public_domain(death_year: int | None, slug: str) -> bool:
    """Verifies whether an author's works qualify under Public Domain rules."""
    if death_year is None:
        log.debug("No verified death year for %s — skipping (unverified status)", slug)
        return False
    return death_year < PUBLIC_DOMAIN_DEATH_YEAR_LIMIT


# ── Main Controller ───────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("DualMova — Stage 1: Manifest Construction")
    log.info("Public Domain Cut-off: Deceased strictly before %d", PUBLIC_DOMAIN_DEATH_YEAR_LIMIT)
    log.info("=" * 60)

    death_cache: dict = {}
    if AUTHOR_CACHE_PATH.exists():
        with open(AUTHOR_CACHE_PATH, encoding="utf-8") as f:
            death_cache = json.load(f)
        log.info("Loaded cached biographical records: %d", len(death_cache))

    manifest_items: list[dict] = []

    # 1. Ingest Folklore Sections
    log.info("\n--- Ingesting Folklore Corpora ---")
    for section in FOLKLORE_SECTIONS:
        url = BASE_URL + section
        log.info("Fetching section: %s", url)
        html = fetch_html(url)
        time.sleep(CRAWL_DELAY_SECONDS)
        if not html:
            continue
        books = parse_folklore_books(html, section)
        log.info("  Found %d folklore titles", len(books))
        manifest_items.extend(books)

    # 2. Ingest Authors Directory
    log.info("\n--- Ingesting Authors Catalog ---")
    html = fetch_html(AUTHORS_URL)
    time.sleep(CRAWL_DELAY_SECONDS)
    if not html:
        log.error("Failed to load author catalog!")
        sys.exit(1)

    authors = parse_authors_list(html)
    pd_authors = []
    skipped = []

    log.info("\n--- Biographical Verification via Wikidata ---")
    for i, author in enumerate(authors, 1):
        slug = author["url_slug"]
        name = author["name"]

        log.info("[%d/%d] Resolving: %s (%s)", i, len(authors), name, slug)
        death_year = get_death_year_from_wikidata(slug, death_cache, cyrillic_name=name)

        if is_public_domain(death_year, slug):
            pd_authors.append({**author, "death_year": death_year})
            log.info("  ✓ Public Domain verified (deceased %d)", death_year)
        else:
            if death_year:
                log.info("  ✗ Protected by copyright (deceased %d)", death_year)
            else:
                log.info("  ? Unverified death year — excluded")
            skipped.append(slug)

        if i % 20 == 0:
            with open(AUTHOR_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(death_cache, f, ensure_ascii=False, indent=2)
            log.info("  [Saved biographical cache: %d records]", len(death_cache))

    log.info("\n--- Ingesting Titles for Verified Authors (%d) ---", len(pd_authors))
    for author in pd_authors:
        slug = author["url_slug"]
        author_url = BASE_URL + author["slug"]

        log.info("Fetching author index: %s", author_url)
        html = fetch_html(author_url)
        time.sleep(CRAWL_DELAY_SECONDS)

        if not html:
            continue

        books = parse_author_books(html, slug)
        log.info("  Found %d titles", len(books))

        for book in books:
            manifest_items.append({
                "title": book["title"],
                "url": book["url"],
                "author": author["name"],
                "author_slug": slug,
                "author_death_year": author["death_year"],
                "license": "public_domain",
                "source": "knihi.com",
                "genre_hint": "prose",
            })

    with open(AUTHOR_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(death_cache, f, ensure_ascii=False, indent=2)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest_items, f, ensure_ascii=False, indent=2)

    log.info("\n%s", "=" * 60)
    log.info("MANIFEST CONSTRUCTION COMPLETE")
    log.info("  Total authors checked: %d", len(authors))
    log.info("  Public Domain authors: %d", len(pd_authors))
    log.info("  Excluded authors:      %d", len(skipped))
    log.info("  Total manifest URLs:   %d", len(manifest_items))
    log.info("  Saved manifest to:     %s", MANIFEST_PATH)


if __name__ == "__main__":
    main()
