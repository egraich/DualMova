"""
DualMova — Remote Server Deployment Utility
===========================================
Synchronizes pipeline scripts to the remote server and initializes crawler sessions.

Usage:
    python deploy_to_server.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PIPELINE_DIR = SCRIPT_DIR
SERVER = "vpn"
REMOTE_DIR = "~/dualmova"


def run(cmd: str, check: bool = True):
    print(f">>> {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if check and result.returncode != 0:
        print(f"ERROR: Command exited with code {result.returncode}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print(f"DualMova — Deploying to remote server ({SERVER})")
    print("=" * 60)

    print("\n[1] Creating remote directory hierarchy...")
    run(f'ssh {SERVER} "mkdir -p {REMOTE_DIR}/pipeline {REMOTE_DIR}/dictionaries/tarask {REMOTE_DIR}/dictionaries/nark"')

    print("\n[2] Synchronizing pipeline scripts...")
    pipeline_scripts = [
        "01_build_manifest.py",
        "02_crawl_server.py",
        "03_parse_and_tag.py",
        "ortho_router.py",
        "04_export_parquet.py",
        "05_export_adaption_labs.py",
        "wiki_extractor.py",
        "fast_crawl.py",
    ]
    for script in pipeline_scripts:
        src = PIPELINE_DIR / script
        if src.exists():
            run(f'scp "{src}" {SERVER}:{REMOTE_DIR}/pipeline/{script}')
        else:
            print(f"  Warning: {script} not found locally, skipping")

    print("\nDeployment complete.")


if __name__ == "__main__":
    main()
