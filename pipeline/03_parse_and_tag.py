"""
DualMova — Stage 3: HTML Parsing & Orthographic Tagging
=======================================================
Reads raw HTML wrappers from raw_html/, extracts text (segregating prose and poetry),
routes each segment through the DualMova discriminative classifier (OrthographyRouter),
and serializes clean, tagged JSONL records into processed/.

Execution:
    python 03_parse_and_tag.py

Outputs:
    DualMova/pipeline/processed/dataset.jsonl  — Main corpus records
    DualMova/pipeline/processed/rejected.jsonl — Rejected noise / mixed records
    DualMova/pipeline/processed/stats.json     — Comprehensive run metrics

Requirements:
    pip install beautifulsoup4 ftfy
"""

import json
import os
import sys
import time
import logging
import hashlib
import urllib.parse
import re
import unicodedata
from pathlib import Path
from dataclasses import asdict

# Import discriminative orthography classifier
sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import OrthographyRouter, RouteResult

try:
    from selectolax.lexbor import LexborHTMLParser
    SELECTOLAX_AVAILABLE = True
except ImportError:
    SELECTOLAX_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

if not SELECTOLAX_AVAILABLE and not BS4_AVAILABLE:
    print("ERROR: Missing HTML parser dependency. Please run: pip install selectolax")
    sys.exit(1)

try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False
    print("Warning: ftfy is not installed; corrupted encoding repairs will be bypassed.")

# ── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
RAW_HTML_DIR = SCRIPT_DIR / "raw_html"
PROCESSED_DIR = SCRIPT_DIR / "processed"
TARASK_WORDLIST = SCRIPT_DIR.parent / "dictionaries" / "tarask" / "wordlist.txt"

MIN_SEGMENT_CHARS = 50
MAX_SEGMENT_CHARS = 2000
MIN_WORDS_IN_SEGMENT = 8

USE_LANGUAGETOOL = False
GENERATE_SYNTHETIC_PAIRS = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SCRIPT_DIR / "03_parse.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ── Text Cleaning & Structural Parser ─────────────────────────────────────────

_LATIN_TO_BY_CYR = re.compile(
    r"(?<=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])[iI](?=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])"
    r"|(?<=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])[iI]\b"
    r"|\b[iI](?=[а-яёўіґА-ЯЁЎІҐ'’ʼ`])"
    r"|\b([iI])\b(?=\s+[а-яёўіґА-ЯЁЎІҐ])"
)

def fix_encoding(text: str) -> str:
    """Repairs broken character encodings via ftfy and canonical Unicode NFC normalization."""
    if FTFY_AVAILABLE:
        text = ftfy.fix_text(text)
    text = unicodedata.normalize("NFC", text)
    return _LATIN_TO_BY_CYR.sub(lambda m: "І" if m.group(0).isupper() else "і", text)


def coalesce_short_paragraphs(paragraphs: list[str], min_chars: int = 120) -> list[str]:
    """
    Coalesces adjacent short dialog lines / drama cues into coherent textual windows.
    Prevents dialogue-heavy classical works (e.g. Kupala's Paulinka) from being dropped.
    """
    merged = []
    buffer = []
    buf_len = 0
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        buffer.append(p_clean)
        buf_len += len(p_clean)
        if buf_len >= min_chars:
            merged.append("\n".join(buffer))
            buffer.clear()
            buf_len = 0
    if buffer:
        if merged and buf_len < min_chars // 2:
            merged[-1] += "\n" + "\n".join(buffer)
        else:
            merged.append("\n".join(buffer))
    return merged


def strip_wiki_markup(text: str) -> str:
    """Cleans leftover wiki markup and HTML annotations."""
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


BOILERPLATE_SUBSTRINGS = (
    "выявы старонак пададзеныя",
    "каб атрымаць лепшую якасць",
    "спампуйце твор цалкам",
    "pdf файлы можна прагледзець",
    "djvu файлы",
    "adobe reader",
    "djview",
    "беларуская палічка",
    "старонка часова недасяжная",
    "пры выкарыстаньні матэрыялаў спасылка",
)


def is_boilerplate(text: str) -> bool:
    t_lower = text.lower()
    return any(b in t_lower for b in BOILERPLATE_SUBSTRINGS)


def extract_text_segments(html: str) -> list[dict]:
    """
    Main HTML parser for literary works using high-performance C99 Lexbor (selectolax)
    with graceful fallback to BeautifulSoup.
    Distinguishes poetry strophes from continuous prose paragraphs.
    """
    if SELECTOLAX_AVAILABLE:
        tree = LexborHTMLParser(html)
        tree.strip_tags(["script", "style", "noscript", "nav", "footer", "header"])

        for el in tree.css(".navbar, .footer, .menu, .book-utils, .random-block, .nav, .header, .page-heading, .preview, .preview-builtin, #preview, #random-block, #buttonsStrip, #pageContainer"):
            el.decompose()

        segments = []

        # 1. Poetry Strophes: <div class="POETRY">
        for poetry_div in tree.css("div.POETRY"):
            strophes = []
            current_strophe = []

            for line in poetry_div.text().split("\n"):
                line = line.strip()
                if line:
                    current_strophe.append(line)
                elif current_strophe:
                    strophes.append("\n".join(current_strophe))
                    current_strophe = []

            if current_strophe:
                strophes.append("\n".join(current_strophe))

            for strophe in strophes:
                strophe = fix_encoding(strophe)
                strophe = strip_wiki_markup(strophe)
                if is_boilerplate(strophe):
                    continue
                if len(strophe) >= MIN_SEGMENT_CHARS:
                    segments.append({
                        "text": strophe,
                        "genre": "poetry",
                    })

            poetry_div.decompose()

        # 2. Prose: Paragraphs from container elements
        main_content = (
            tree.css_first("div.container")
            or tree.css_first("div#content")
            or tree.css_first("div#main")
            or tree.css_first("div#text")
            or tree.body
        )

        if main_content:
            paragraphs = []
            p_nodes = main_content.css("p")
            if p_nodes:
                for p in p_nodes:
                    text = p.text(separator=" ", strip=True)
                    if text:
                        paragraphs.append(text)

            if not paragraphs:
                full_text = main_content.text(separator="\n", strip=True)
                for para in re.split(r"\n{2,}", full_text):
                    para = para.strip()
                    if para:
                        paragraphs.append(para)

            cleaned_paras = []
            for para in paragraphs:
                para = fix_encoding(para)
                para = strip_wiki_markup(para)
                if para and not is_boilerplate(para):
                    cleaned_paras.append(para)

            coalesced_paras = coalesce_short_paragraphs(cleaned_paras, min_chars=120)

            for para in coalesced_paras:
                if len(para) > MAX_SEGMENT_CHARS:
                    sentences = re.split(r"(?<=[.!?])\s+", para)
                    chunk = ""
                    for sent in sentences:
                        if len(chunk) + len(sent) < MAX_SEGMENT_CHARS:
                            chunk += " " + sent
                        else:
                            chunk_clean = chunk.strip()
                            if len(chunk_clean) >= MIN_SEGMENT_CHARS and not is_boilerplate(chunk_clean):
                                segments.append({"text": chunk_clean, "genre": "prose"})
                            chunk = sent
                    chunk_clean = chunk.strip()
                    if len(chunk_clean) >= MIN_SEGMENT_CHARS and not is_boilerplate(chunk_clean):
                        segments.append({"text": chunk_clean, "genre": "prose"})
                elif len(para) >= MIN_SEGMENT_CHARS:
                    segments.append({"text": para, "genre": "prose"})

        return segments

    # Fallback to BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content UI and navigation elements
    for el in soup.find_all(class_=re.compile(
        r"navbar|footer|menu|book-utils|random-block|nav|header|page-heading|preview|preview-builtin", re.I
    )):
        el.decompose()

    for el in soup.find_all(id=re.compile(r"preview|random-block|buttonsStrip|pageContainer", re.I)):
        el.decompose()

    for el in soup.find_all(["script", "style", "noscript", "nav", "footer"]):
        el.decompose()

    segments = []

    # 1. Poetry Strophes: <div class="POETRY">
    for poetry_div in soup.find_all("div", class_="POETRY"):
        strophes = []
        current_strophe = []

        for line in poetry_div.get_text().split("\n"):
            line = line.strip()
            if line:
                current_strophe.append(line)
            elif current_strophe:
                strophes.append("\n".join(current_strophe))
                current_strophe = []

        if current_strophe:
            strophes.append("\n".join(current_strophe))

        for strophe in strophes:
            strophe = fix_encoding(strophe)
            strophe = strip_wiki_markup(strophe)
            if is_boilerplate(strophe):
                continue
            if len(strophe) >= MIN_SEGMENT_CHARS:
                segments.append({
                    "text": strophe,
                    "genre": "poetry",
                })

        poetry_div.decompose()

    # 2. Prose: Paragraphs from container elements
    main_content = (
        soup.find("div", class_=re.compile(r"container", re.I))
        or soup.find("div", id=re.compile(r"content|main|text", re.I))
        or soup.body
    )

    if main_content:
        paragraphs = []

        # Explicit paragraph elements
        p_tags = main_content.find_all("p")
        if p_tags:
            for p in p_tags:
                text = p.get_text(separator=" ").strip()
                if text:
                    paragraphs.append(text)

        # Fallback newline separation
        if not paragraphs:
            full_text = main_content.get_text(separator="\n")
            for para in re.split(r"\n{2,}", full_text):
                para = para.strip()
                if para:
                    paragraphs.append(para)

        cleaned_paras = []
        for para in paragraphs:
            para = fix_encoding(para)
            para = strip_wiki_markup(para)
            if para and not is_boilerplate(para):
                cleaned_paras.append(para)

        coalesced_paras = coalesce_short_paragraphs(cleaned_paras, min_chars=120)

        for para in coalesced_paras:
            # Split excessively long paragraphs on sentence boundaries
            if len(para) > MAX_SEGMENT_CHARS:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                chunk = ""
                for sent in sentences:
                    if len(chunk) + len(sent) < MAX_SEGMENT_CHARS:
                        chunk += " " + sent
                    else:
                        chunk_clean = chunk.strip()
                        if len(chunk_clean) >= MIN_SEGMENT_CHARS and not is_boilerplate(chunk_clean):
                            segments.append({"text": chunk_clean, "genre": "prose"})
                        chunk = sent
                chunk_clean = chunk.strip()
                if len(chunk_clean) >= MIN_SEGMENT_CHARS and not is_boilerplate(chunk_clean):
                    segments.append({"text": chunk_clean, "genre": "prose"})
            elif len(para) >= MIN_SEGMENT_CHARS:
                segments.append({"text": para, "genre": "prose"})

    return segments


def count_words(text: str) -> int:
    """Counts Belarusian Cyrillic word tokens."""
    return len(re.findall(r"[а-яёіўА-ЯЁІЎь]+", text))


def make_segment_id(author_slug: str, title: str, index: int, augmented: bool) -> str:
    """Generates a deterministic unique segment identifier."""
    base = f"{author_slug}__{title}__{index}"
    h = hashlib.md5(base.encode()).hexdigest()[:8]
    suffix = "_aug" if augmented else ""
    return f"knihi_{h}_{index:04d}{suffix}"


# ── Main Pipeline Execution ───────────────────────────────────────────────────

MANIFEST_PATH = SCRIPT_DIR / "manifest_urls_verified.json"
if not MANIFEST_PATH.exists() or MANIFEST_PATH.stat().st_size < 10000:
    MANIFEST_PATH = SCRIPT_DIR / "manifest_urls.json"

try:
    from corpus_safety_filter import EXCLUDED_SLUGS, EXCLUDED_TITLE_KEYWORDS
except ImportError:
    EXCLUDED_SLUGS = set()
    EXCLUDED_TITLE_KEYWORDS = []


def url_to_filename(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    name = path.replace("/", "__")
    if not name.endswith(".json"):
        name = name + ".json"
    if len(name) > 180:
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        name = name[:160] + "_" + h + ".json"
    return name


def main():
    log.info("=" * 60)
    log.info("DualMova — Stage 3: Extraction, Classification & Tagging")
    log.info("=" * 60)

    if not RAW_HTML_DIR.exists():
        log.error("Raw data directory not found: %s", RAW_HTML_DIR)
        log.error("Please run fast_crawl.py before Stage 3.")
        sys.exit(1)

    log.info("Initializing OrthographyRouter...")
    router = OrthographyRouter(
        tarask_wordlist_path=TARASK_WORDLIST,
        use_languagetool=USE_LANGUAGETOOL,
    )

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dataset_path = PROCESSED_DIR / "dataset.jsonl"
    rejected_path = PROCESSED_DIR / "rejected.jsonl"

    items_to_process = []
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
        log.info("Loaded verified Public Domain manifest: %d titles", len(manifest))
        for m in manifest:
            slug = m.get("author_slug", "")
            title = (m.get("title") or "").lower()
            if slug in EXCLUDED_SLUGS or any(bkw in title for bkw in EXCLUDED_TITLE_KEYWORDS):
                continue
            fname = url_to_filename(m["url"])
            fpath = RAW_HTML_DIR / fname
            if fpath.exists():
                items_to_process.append((fpath, m))
        log.info("Found %d corresponding cached files on disk.", len(items_to_process))
    else:
        log.warning("Manifest %s not found. Processing all raw_html/*.json files.", MANIFEST_PATH)
        for fpath in sorted(RAW_HTML_DIR.glob("*.json")):
            slug = fpath.name.split("__")[0]
            if slug in EXCLUDED_SLUGS:
                continue
            items_to_process.append((fpath, None))

    if not items_to_process:
        log.error("No valid input files available in %s", RAW_HTML_DIR)
        sys.exit(1)

    stats = {
        "files_processed": 0,
        "segments_total": 0,
        "chars_total": 0,
        "segments_nark": 0,
        "segments_tarask": 0,
        "segments_rejected": 0,
        "augmented_pairs": 0,
        "poetry": 0,
        "prose": 0,
        "folklore": 0,
    }

    t_start = time.perf_counter()

    with open(dataset_path, "w", encoding="utf-8") as f_out, \
         open(rejected_path, "w", encoding="utf-8") as f_rej:

        for file_path, manifest_item in items_to_process:
            try:
                with open(file_path, encoding="utf-8") as f:
                    wrapper = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Skipping unreadable %s: %s", file_path.name, e)
                continue

            html = wrapper.get("html", "")
            if not html:
                continue

            metadata = {
                "author": (manifest_item.get("author") if manifest_item else None) or wrapper.get("author", ""),
                "author_slug": (manifest_item.get("author_slug") if manifest_item else None) or wrapper.get("author_slug", ""),
                "author_death_year": (manifest_item.get("author_death_year") if manifest_item else None) or wrapper.get("author_death_year"),
                "title": (manifest_item.get("title") if manifest_item else None) or wrapper.get("title", ""),
                "source_url": (manifest_item.get("url") if manifest_item else None) or wrapper.get("url", ""),
                "license": "public_domain",
                "source": "knihi.com",
                "lang": "be",
            }

            default_genre = "prose"
            if manifest_item and manifest_item.get("genre_hint") == "folklore":
                default_genre = "folklore"
            elif wrapper.get("genre_hint") == "folklore":
                default_genre = "folklore"

            segments = extract_text_segments(html)
            stats["files_processed"] += 1

            # Filter segments by minimum words
            valid_segments = []
            for seg in segments:
                if count_words(seg["text"]) >= MIN_WORDS_IN_SEGMENT:
                    valid_segments.append(seg)

            if not valid_segments:
                continue

            # High-speed single-pass routing across document
            seg_texts = [s["text"] for s in valid_segments]
            doc_prior, results = router.route_document(seg_texts)

            seg_index = 0
            for seg, result in zip(valid_segments, results):
                text = seg["text"]
                seg_genre = "poetry" if seg["genre"] == "poetry" else default_genre
                seg_chars = len(text)

                stats["segments_total"] += 1
                stats["chars_total"] += seg_chars

                if result.label == "rejected":
                    stats["segments_rejected"] += 1
                    rej_record = {
                        **metadata,
                        "genre": seg_genre,
                        "text_raw": text,
                        "reject_reason": result.metrics.get("reason", "unknown"),
                        "metrics": result.metrics,
                    }
                    f_rej.write(json.dumps(rej_record, ensure_ascii=False) + "\n")
                    continue

                aug = None
                pair_id = None
                if GENERATE_SYNTHETIC_PAIRS:
                    aug = router.generate_augmented_pair(result)
                    if aug is not None:
                        pair_id = hashlib.sha256(result.text_original.encode("utf-8")).hexdigest()[:16]

                seg_id = make_segment_id(
                    metadata["author_slug"],
                    metadata["title"],
                    seg_index,
                    False,
                )
                seg_index += 1

                record = {
                    "id": seg_id,
                    "text": result.text_tagged,
                    "text_raw": result.text_original,
                    "orthography": result.label,
                    "is_augmented": False,
                    "pair_id": pair_id,
                    "genre": seg_genre,
                    **metadata,
                    "char_count": len(result.text_original),
                    "word_count": len(result.text_original.split()),
                    "metrics": result.metrics,
                }

                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

                if seg_genre == "poetry":
                    stats["poetry"] += 1
                elif seg_genre == "folklore":
                    stats["folklore"] += 1
                else:
                    stats["prose"] += 1

                if result.label == "nark":
                    stats["segments_nark"] += 1
                else:
                    stats["segments_tarask"] += 1

            if stats["files_processed"] % 100 == 0:
                t_cur = time.perf_counter() - t_start
                cur_seg_rate = stats["segments_total"] / max(t_cur, 0.001)
                cur_chars_rate = stats["chars_total"] / max(t_cur, 0.001)
                log.info(
                    "Processed %d/%d files (%.1f%%) | %d segs (%.0f seg/s, %s char/s) | Valid: %d (nark=%d, tarask=%d, rej=%d)",
                    stats["files_processed"],
                    len(items_to_process),
                    stats["files_processed"] / max(len(items_to_process), 1) * 100,
                    stats["segments_total"],
                    cur_seg_rate,
                    f"{cur_chars_rate:,.0f}",
                    stats["segments_nark"] + stats["segments_tarask"],
                    stats["segments_nark"],
                    stats["segments_tarask"],
                    stats["segments_rejected"],
                )

    t_elapsed = time.perf_counter() - t_start
    seg_rate = stats["segments_total"] / max(t_elapsed, 0.001)
    chars_rate = stats["chars_total"] / max(t_elapsed, 0.001)
    mb_out = (dataset_path.stat().st_size + rejected_path.stat().st_size) / (1024 * 1024)
    mb_rate = mb_out / max(t_elapsed, 0.001)
    book_rate = stats["files_processed"] / max(t_elapsed, 0.001)
    stats["elapsed_seconds"] = round(t_elapsed, 2)
    stats["throughput_segments_per_sec"] = round(seg_rate, 1)
    stats["throughput_chars_per_sec"] = round(chars_rate, 1)
    stats["throughput_books_per_sec"] = round(book_rate, 2)
    stats["throughput_mb_per_sec"] = round(mb_rate, 2)

    stats_path = PROCESSED_DIR / "stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    log.info("\n%s", "=" * 60)
    log.info("EXTRACTION & TAGGING COMPLETE (DETERMINISTIC BENCHMARK)")
    log.info("  Execution time:        %.2f s (%.2f min)", t_elapsed, t_elapsed / 60)
    log.info("  Throughput (segments): %.1f segments/s", seg_rate)
    log.info("  Throughput (chars):    %s chars/s (%.2f MB/s)", f"{chars_rate:,.0f}", mb_rate)
    log.info("  Throughput (books):    %.2f books/s", book_rate)
    log.info("  Files processed:       %d", stats["files_processed"])
    log.info("  Total segments:        %d", stats["segments_total"])
    log.info("  Total characters:      %s", f"{stats['chars_total']:,}")
    log.info("  Official (Narkamaŭka): %d (%.1f%%)", stats["segments_nark"], stats["segments_nark"] / max(stats["segments_total"], 1) * 100)
    log.info("  Classical (Taraškievica): %d (%.1f%%)", stats["segments_tarask"], stats["segments_tarask"] / max(stats["segments_total"], 1) * 100)
    log.info("  Rejected (Noise):      %d (%.1f%%)", stats["segments_rejected"], stats["segments_rejected"] / max(stats["segments_total"] + stats["segments_rejected"], 1) * 100)
    log.info("  Poetry strophes:       %d", stats["poetry"])
    log.info("  Prose paragraphs:      %d", stats["prose"])
    log.info("  Folklore segments:     %d", stats["folklore"])
    log.info("  Target dataset:        %s", dataset_path)
    log.info("  Poetry strophes:       %d", stats["poetry"])
    log.info("  Prose paragraphs:      %d", stats["prose"])
    log.info("  Folklore segments:     %d", stats["folklore"])
    log.info("  Target dataset:        %s", dataset_path)


if __name__ == "__main__":
    main()
