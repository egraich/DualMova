"""
DualMova — High-Throughput Wikimedia Dump Extractor
===================================================
Streams, cleans, and tags Belarusian text directly from bz2 XML archives:
1. bewiki-latest-pages-articles.xml.bz2       (Official Standard, be.wikipedia.org)
2. be_x_oldwiki-latest-pages-articles.xml.bz2 (Classical Standard, be-tarask.wikipedia.org)
3. bewikisource-latest-pages-articles.xml.bz2 (Historical Source Archive, be.wikisource.org)

Key Features:
- Constant memory O(1) streaming directly from .xml.bz2 archives (zero intermediate disk decompression).
- Template ({{...}}) and nested wikitext table ({|...|}) removal via balanced bracket stack parsing.
- Orthographic verification and routing via DualMovaOrthographyClassifier.
- Strict typography normalization and compatibility with the DualMova schema.
"""

import bz2
import json
import logging
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

# Import discriminative classifier and typography normalizer
sys.path.insert(0, str(Path(__file__).parent))
from ortho_router import OrthographyRouter, normalize_typography

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / "wiki_extractor.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

DUMPS_DIR = Path("/root/dualmova/dumps")
PROCESSED_DIR = Path(__file__).parent / "processed"
TARASK_WORDLIST = Path(__file__).parent.parent / "dictionaries" / "tarask" / "wordlist.txt"

MIN_PARAGRAPH_CHARS = 50
MAX_PARAGRAPH_CHARS = 1500
MIN_WORDS_IN_PARA = 8

CYR_WORD_RE = re.compile(r"[а-яёіўА-ЯЁІЎь]+", re.IGNORECASE)
RUSSIAN_И_RE = re.compile(r"\b\w*и\w*\b")


# ── Wikitext Cleaner ─────────────────────────────────────────────────────────

def remove_templates_and_tables(text: str) -> str:
    """Removes templates {{...}} and tables {|...|} of arbitrary nesting depth via bracket stack."""
    # 1. Strip MediaWiki tables {| ... |}
    result = []
    i = 0
    n = len(text)
    tbl_depth = 0
    while i < n:
        if i + 1 < n and text[i] == "{" and text[i+1] == "|":
            tbl_depth += 1
            i += 2
        elif i + 1 < n and text[i] == "|" and text[i+1] == "}":
            if tbl_depth > 0:
                tbl_depth -= 1
            i += 2
        else:
            if tbl_depth == 0:
                result.append(text[i])
            i += 1
    text1 = "".join(result)

    # 2. Strip MediaWiki templates {{ ... }}
    result2 = []
    i = 0
    n = len(text1)
    tmpl_depth = 0
    while i < n:
        if i + 1 < n and text1[i] == "{" and text1[i+1] == "{":
            tmpl_depth += 1
            i += 2
        elif i + 1 < n and text1[i] == "}" and text1[i+1] == "}":
            if tmpl_depth > 0:
                tmpl_depth -= 1
            i += 2
        else:
            if tmpl_depth == 0:
                result2.append(text1[i])
            i += 1
    return "".join(result2)


def clean_wikitext(text: str) -> str:
    """Strips markup, templates, tables, comments, and links from wikitext."""
    if not text:
        return ""

    # 1. HTML comments <!-- ... -->
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # 2. Reference tags <ref>...</ref>, <ref ... />, <gallery>, <math>
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<ref[^>]*/>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<(gallery|math|timeline|source|syntaxhighlight)[^>]*>.*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)

    # 3. Strip templates and tables
    text = remove_templates_and_tables(text)

    # 4. Remove categories, images, templates, and files
    text = re.sub(
        r"\[\[\s*(?:Катэгорыя|Category|Файл|Выява|Відарыс|Шаблон|Шаблён|File|Image|Template)\s*:[^\]]+\]\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 5. Unwrap internal wiki links: [[Target|Label]] -> Label, [[Target]] -> Target
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)

    # 6. Unwrap external links: [http://example.com Label] -> Label
    text = re.sub(r"\[https?://[^\s\]]+(?:\s+([^\]]+))?\]", lambda m: m.group(1) or "", text)

    # 7. Section headings == Heading ==
    text = re.sub(r"^=+[^=]+=+\s*$", "", text, flags=re.MULTILINE)

    # 8. Bold / Italics formatting ''''' -> ''
    text = re.sub(r"'{2,5}", "", text)

    # 9. Filter leftover MediaWiki syntax lines
    lines = []
    for line in text.split("\n"):
        l = line.strip()
        if l and not l.startswith(("|", "!", "{", "}", "=", ":", "*", "#")):
            lines.append(l)
    text = "\n".join(lines)

    # 10. Decode essential HTML entities
    text = text.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

    return text.strip()


def is_clean_belarusian(text: str) -> bool:
    """Verifies linguistic quality: absence of un-Belarusian tokens, minimal token count."""
    if text.startswith(("|", "!", "{", "}", "=", ":", "*", "#")):
        return False
    if " | " in text or " = " in text:
        return False
    if "{{" in text or "}}" in text or "{|" in text or "|}" in text:
        return False

    words = CYR_WORD_RE.findall(text)
    if len(words) < MIN_WORDS_IN_PARA:
        return False

    # Ratio of Cyrillic character volume
    cyr_chars = sum(len(w) for w in words)
    if cyr_chars / max(len(text), 1) < 0.65:
        return False

    # Russian 'и' intrusion threshold
    ru_i_count = len(re.findall(r"\u0438", text))
    if ru_i_count / max(len(words), 1) > 0.02:
        return False

    return True


# ── Streaming Page Generator ──────────────────────────────────────────────────

def stream_wiki_articles(dump_path: Path):
    """
    Streaming generator yielding (title, page_id, wikitext) from .xml.bz2.
    """
    log.info("Opening archive: %s", dump_path)
    with bz2.open(dump_path, "rb") as f:
        context = ET.iterparse(f, events=("start", "end"))
        _, root = next(context)

        title = ""
        page_id = ""
        ns = ""
        is_redirect = False
        wikitext = ""

        for event, elem in context:
            if event != "end":
                continue

            tag = elem.tag.split("}")[-1]

            if tag == "title":
                title = elem.text or ""
            elif tag == "ns":
                ns = elem.text or ""
            elif tag == "id" and not page_id:
                page_id = elem.text or ""
            elif tag == "redirect":
                is_redirect = True
            elif tag == "text":
                wikitext = elem.text or ""
            elif tag == "page":
                if ns == "0" and not is_redirect and wikitext and title:
                    yield title, page_id, wikitext

                title = ""
                page_id = ""
                ns = ""
                is_redirect = False
                wikitext = ""
                elem.clear()
                root.clear()


# ── Dump Processor ────────────────────────────────────────────────────────────

def process_dump(dump_name: str, default_orth: str, router: OrthographyRouter, f_out, seen_ids: set = None):
    dump_path = DUMPS_DIR / dump_name
    if not dump_path.exists():
        log.warning("Dump %s not found in %s", dump_name, DUMPS_DIR)
        return {"articles": 0, "paragraphs": 0}

    source_key = dump_name.split("-")[0]
    base_url = {
        "bewiki": "https://be.wikipedia.org/wiki/",
        "be_x_oldwiki": "https://be-tarask.wikipedia.org/wiki/",
        "bewikisource": "https://be.wikisource.org/wiki/",
    }.get(source_key, "https://be.wikipedia.org/wiki/")

    is_wikisource = (source_key == "bewikisource")
    source_label = "Вікікрыніцы" if is_wikisource else "Вікіпедыя"
    author_slug = "wikisource" if is_wikisource else "wikipedia"

    stats = {"articles": 0, "paragraphs": 0, "nark": 0, "tarask": 0, "chars": 0}

    log.info("Starting processing for %s (routing mode: %s)...", dump_name, default_orth)

    if seen_ids is None:
        seen_ids = set()

    skipped = 0
    for title, page_id, raw_wikitext in stream_wiki_articles(dump_path):
        stats["articles"] += 1

        probe_id = f"wiki_{source_key}_{page_id}_0000"
        if probe_id in seen_ids:
            skipped += 1
            continue

        cleaned = clean_wikitext(raw_wikitext)
        if not cleaned:
            continue

        raw_paras = re.split(r"\n{2,}", cleaned)
        para_idx = 0

        for para in raw_paras:
            para = para.strip()
            if len(para) < MIN_PARAGRAPH_CHARS:
                continue

            para = normalize_typography(para)

            if not is_clean_belarusian(para):
                continue

            chunks = []
            if len(para) > MAX_PARAGRAPH_CHARS:
                sents = re.split(r"(?<=[.!?])\s+", para)
                curr = ""
                for s in sents:
                    if len(curr) + len(s) < MAX_PARAGRAPH_CHARS:
                        curr += " " + s
                    else:
                        if len(curr.strip()) >= MIN_PARAGRAPH_CHARS:
                            chunks.append(curr.strip())
                        curr = s
                if len(curr.strip()) >= MIN_PARAGRAPH_CHARS:
                    chunks.append(curr.strip())
            else:
                chunks = [para]

            for chunk in chunks:
                if not is_clean_belarusian(chunk):
                    continue

                if default_orth == "route":
                    route_res = router.route(chunk)
                    if route_res.label not in ("nark", "tarask"):
                        continue
                    orth = route_res.label
                else:
                    orth = default_orth

                tag_name = "orth_taras" if orth == "tarask" else "orth_nark"
                tag = f"<{tag_name}>{chunk}</{tag_name}>"

                rec_id = f"wiki_{source_key}_{page_id}_{para_idx:04d}"
                record = {
                    "id": rec_id,
                    "text": tag,
                    "text_raw": chunk,
                    "orthography": orth,
                    "genre": "prose",
                    "author": source_label,
                    "author_slug": author_slug,
                    "author_death_year": -1,
                    "title": title,
                    "source_url": f"{base_url}{title.replace(' ', '_')}",
                    "license": "cc-by-sa-4.0",
                    "source": source_key,
                    "lang": "be",
                    "is_augmented": False,
                    "pair_id": None,
                    "char_count": len(chunk),
                    "word_count": len(chunk.split()),
                }

                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                seen_ids.add(rec_id)
                para_idx += 1
                stats["paragraphs"] += 1
                stats["chars"] += len(chunk)
                if orth == "nark":
                    stats["nark"] += 1
                else:
                    stats["tarask"] += 1

        if stats["articles"] % 10000 == 0:
            log.info(
                "[%s] Articles: %d (skipped: %d) | Paragraphs: %d (nark=%d, tarask=%d) | %.1fM chars",
                source_key,
                stats["articles"],
                skipped,
                stats["paragraphs"],
                stats["nark"],
                stats["tarask"],
                stats["chars"] / 1_000_000,
            )

    log.info(
        "Completed %s: %d articles, %d paragraphs (nark=%d, tarask=%d, %.1f MB raw text)",
        dump_name,
        stats["articles"],
        stats["paragraphs"],
        stats["nark"],
        stats["tarask"],
        stats["chars"] / (1024 * 1024),
    )
    return stats


def main():
    log.info("=" * 60)
    log.info("DualMova — Wikimedia Archive Extractor")
    log.info("=" * 60)

    router = OrthographyRouter(tarask_wordlist_path=TARASK_WORDLIST, use_languagetool=False)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "dataset_wiki.jsonl"

    seen_ids = set()
    if out_path.exists():
        log.info("Reading existing identifiers from %s...", out_path)
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    rid = obj.get("id")
                    if rid:
                        seen_ids.add(rid)
                except Exception:
                    pass
        log.info("Found %d pre-existing paragraphs. Resuming without duplicates.", len(seen_ids))

    all_stats = {}
    with open(out_path, "a", encoding="utf-8") as f_out:
        # 1. be_x_oldwiki (Classical Taraškievica Wikipedia) — ~91K articles
        s1 = process_dump("be_x_oldwiki-latest-pages-articles.xml.bz2", "route", router, f_out, seen_ids)
        all_stats["be_x_oldwiki"] = s1

        # 2. bewikisource (Wikisource) — Historical literary and archival texts
        s2 = process_dump("bewikisource-latest-pages-articles.xml.bz2", "route", router, f_out, seen_ids)
        all_stats["bewikisource"] = s2

        # 3. bewiki (Official Narkamaŭka Wikipedia) — ~267K articles
        s3 = process_dump("bewiki-latest-pages-articles.xml.bz2", "route", router, f_out, seen_ids)
        all_stats["bewiki"] = s3

    stats_file = PROCESSED_DIR / "stats_wiki.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)

    log.info("=" * 60)
    log.info("ALL WIKIMEDIA ARCHIVES EXTRACTED TO %s", out_path)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
