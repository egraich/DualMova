"""
DualMova — Stage 2: Rate-Limited Server Crawler
================================================
Respectful, rate-limited corpus crawler archiving knihi.com book pages into raw_html/.

Execution:
    python 02_crawl_server.py

Safety Parameters:
    - Rate-limiting: CRAWL_DELAY_SECONDS per request
    - Storage guard: Halts execution if free disk space < MIN_FREE_GB
    - Payload guard: Skips responses exceeding MAX_FILE_SIZE_MB
"""

import json
import os
import ssl
import sys
import time
import hashlib
import logging
import shutil
import urllib.request
import urllib.error
from pathlib import Path

CRAWL_DELAY_SECONDS = 2.0
MIN_FREE_GB = 5.0
MAX_FILE_SIZE_MB = 10.0
HTTP_TIMEOUT_SECONDS = 20

SCRIPT_DIR = Path(__file__).parent
MANIFEST_PATH = SCRIPT_DIR / "manifest_urls.json"
RAW_HTML_DIR = SCRIPT_DIR / "raw_html"
PROGRESS_FILE = SCRIPT_DIR / "crawl_progress.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SCRIPT_DIR / "02_crawl.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

_SSL_CTX = ssl._create_unverified_context()


def get_free_disk_gb() -> float:
    """Returns available disk space in gigabytes."""
    usage = shutil.disk_usage(SCRIPT_DIR)
    return usage.free / (1024 ** 3)


def url_to_filename(url: str) -> str:
    """Converts a source URL into a deterministic safe file path."""
    path = url.replace("https://knjhi.com", "").replace("https://knihi.com", "")
    safe = path.lstrip("/").replace("/", "__")
    if not safe.endswith(".html"):
        safe += ".html"
    return safe


def load_progress() -> set:
    """Loads previously completed URLs."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_progress(done: set):
    """Persists crawling progress."""
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(done), f)


def fetch_page(url: str) -> tuple[str | None, int]:
    """Fetches a web page with payload size safeguards and encoding detection."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DualMova-DatasetBuilder/1.0 (ZorkaLabs; educational research)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "be,ru;q=0.9,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            status = resp.status
            content_length = int(resp.headers.get("Content-Length", 0))

            if content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
                log.warning("Skipping oversized payload: %d bytes", content_length)
                return None, -1

            raw = resp.read()
            if len(raw) > MAX_FILE_SIZE_MB * 1024 * 1024:
                log.warning("Skipping oversized payload: %d bytes", len(raw))
                return None, -1

            for enc in ("utf-8", "windows-1251", "iso-8859-1"):
                try:
                    return raw.decode(enc), status
                except UnicodeDecodeError:
                    continue
            return raw.decode("utf-8", errors="replace"), status

    except urllib.error.HTTPError as e:
        log.warning("HTTP %d: %s", e.code, url)
        return None, e.code
    except urllib.error.URLError as e:
        log.warning("URLError: %s — %s", e.reason, url)
        return None, -1
    except OSError as e:
        log.warning("OSError: %s — %s", e, url)
        return None, -1


def main():
    log.info("=" * 60)
    log.info("DualMova — Stage 2: Server-Side Crawler")
    log.info("=" * 60)

    if not MANIFEST_PATH.exists():
        log.error("Manifest not found: %s", MANIFEST_PATH)
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    log.info("Loaded manifest: %d entries", len(manifest))

    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)
    done_urls = load_progress()
    log.info("Previously crawled: %d entries", len(done_urls))

    remaining = [item for item in manifest if item["url"] not in done_urls]
    log.info("Remaining to crawl: %d entries", len(remaining))

    if not remaining:
        log.info("All manifest entries are already downloaded!")
        return

    success_count = 0
    fail_count = 0
    total_bytes = 0

    for i, item in enumerate(remaining, 1):
        free_gb = get_free_disk_gb()
        if free_gb < MIN_FREE_GB:
            log.critical("Disk space threshold reached (%.2f GB < %.2f GB). Stopping.", free_gb, MIN_FREE_GB)
            break

        url = item["url"]
        log.info("[%d/%d] Fetching: %s", i, len(remaining), url)

        html, status = fetch_page(url)

        if html:
            fname = url_to_filename(url)
            fpath = RAW_HTML_DIR / fname

            wrapper = {
                **item,
                "html": html,
                "scraped_at": time.time(),
            }

            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(wrapper, f, ensure_ascii=False)

            done_urls.add(url)
            success_count += 1
            total_bytes += len(html.encode("utf-8"))
            log.info("  ✓ Saved -> %s (%.1f KB)", fname, len(html) / 1024)
        else:
            fail_count += 1
            log.warning("  ✗ Failed to fetch %s", url)

        if i % 25 == 0:
            save_progress(done_urls)
            log.info("Progress checkpoint: %d total crawled", len(done_urls))

        time.sleep(CRAWL_DELAY_SECONDS)

    save_progress(done_urls)

    log.info("\n%s", "=" * 60)
    log.info("CRAWL SESSION FINISHED")
    log.info("  Successful:    %d", success_count)
    log.info("  Failed:        %d", fail_count)
    log.info("  Volume:        %.2f MB", total_bytes / (1024 * 1024))
    log.info("  Total cached:  %d", len(done_urls))


if __name__ == "__main__":
    main()
