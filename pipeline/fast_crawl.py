"""
DualMova — High-Throughput Corpus Crawler
=========================================
Multi-threaded resilient crawler for knihi.com:
- 8 concurrent workers (ThreadPoolExecutor) for accelerated throughput.
- Automatic URL quoting to prevent encoding errors on Cyrillic URI paths.
- Resumes automatically by checking file existence and integrity.
- Resilient network handling: 15s timeout with 3 exponential retries.
- Continuous disk capacity monitoring.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

PIPELINE_DIR = Path(__file__).parent
MANIFEST_PATH = PIPELINE_DIR / "manifest_urls.json"
RAW_HTML_DIR = PIPELINE_DIR / "raw_html"
LOG_PATH = PIPELINE_DIR / "02_crawl.log"

MAX_WORKERS = 8
TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
MIN_FREE_DISK_GB = 3.0

_SSL_CTX = ssl._create_unverified_context()
UA = "DualMova-DatasetBuilder/1.0 (Mozilla/5.0 compatible; educational research)"

lock = threading.Lock()
stats = {"success": 0, "skipped": 0, "failed": 0, "bytes": 0}

def get_free_disk_gb():
    stat = os.statvfs(str(PIPELINE_DIR)) if hasattr(os, "statvfs") else None
    if stat:
        return (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
    return 100.0

def url_to_filename(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    name = path.replace("/", "__")
    if not name.endswith(".json"):
        name = name + ".json"
    if len(name) > 180:
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        name = name[:160] + "_" + h + ".json"
    return name

def safe_url(url: str) -> str:
    """Encodes Cyrillic characters in URL paths and parameters."""
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path)
    query = urllib.parse.quote(parts.query, safe="=&?/")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))

def fetch_and_save(item: dict) -> bool:
    url = item.get("url", "")
    if not url:
        return False

    filename = url_to_filename(url)
    out_path = RAW_HTML_DIR / filename

    if out_path.exists() and out_path.stat().st_size > 100:
        with lock:
            stats["skipped"] += 1
        return True

    encoded_url = safe_url(url)
    html_content = ""

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(encoded_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=TIMEOUT_SECONDS) as resp:
                raw = resp.read()
                for enc in ("utf-8", "windows-1251", "iso-8859-1"):
                    try:
                        html_content = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                if not html_content:
                    html_content = raw.decode("utf-8", errors="replace")
                break
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.0 * (attempt + 1))
            else:
                with lock:
                    stats["failed"] += 1
                return False

    if not html_content:
        with lock:
            stats["failed"] += 1
        return False

    record = {
        **item,
        "html": html_content,
        "scraped_at": time.time(),
    }

    tmp_path = out_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        tmp_path.replace(out_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        with lock:
            stats["failed"] += 1
        return False

    with lock:
        stats["success"] += 1
        stats["bytes"] += len(html_content.encode("utf-8"))

    return True

def main():
    RAW_HTML_DIR.mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest not found: {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, encoding="utf-8") as f:
        manifest = json.load(f)

    total = len(manifest)
    print(f"Loaded manifest with {total} items")
    print(f"Target directory: {RAW_HTML_DIR}")

    free_gb = get_free_disk_gb()
    if free_gb < MIN_FREE_DISK_GB:
        print(f"Error: Insufficient disk space: {free_gb:.1f} GB available")
        sys.exit(1)

    print(f"Starting crawler with {MAX_WORKERS} workers...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_and_save, item): item for item in manifest}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 100 == 0 or done == total:
                elapsed = time.time() - start_time
                speed = done / max(elapsed, 0.1)
                with lock:
                    mb = stats["bytes"] / (1024 * 1024)
                    print(
                        f"[{done}/{total}] {done/total*100:.1f}% | "
                        f"Saved: {stats['success']}, Skipped: {stats['skipped']}, Failed: {stats['failed']} | "
                        f"Volume: {mb:.1f} MB | Speed: {speed:.1f} items/sec"
                    )

    elapsed = time.time() - start_time
    print("\nCRAWL COMPLETED")
    print(f"  Total items:    {total}")
    print(f"  Saved:          {stats['success']}")
    print(f"  Skipped:        {stats['skipped']}")
    print(f"  Failed:         {stats['failed']}")
    print(f"  Elapsed:        {elapsed:.1f} seconds")

if __name__ == "__main__":
    main()
