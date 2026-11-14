#!/usr/bin/env python3
"""Audit source URLs in the catalogue: HTTP status + Wayback fallback."""
import argparse
import csv
import json
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data/raw/catalogue.jsonl"
BATCH_MAP = ROOT / "research/country_batch_map.csv"
OUTPUT = ROOT / "data/raw/eval/link_audit.jsonl"
RATE_LIMIT = 1.0  # seconds per host

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

WAYBACK_URL = "https://archive.org/wayback/available?url={}"


def load_country_batches(batch_arg: str | None) -> set[str] | None:
    """Return set of allowed countries, or None to include all."""
    if not batch_arg:
        return None
    wanted = {b.strip() for b in batch_arg.split(",")}
    country_map = {}
    if BATCH_MAP.exists():
        with open(BATCH_MAP, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                country_map[row["country"]] = row["batch_id"]
    return {c for c, b in country_map.items() if b in wanted}


def load_seen(output: Path) -> dict[str, str]:
    """Return {id: existing_line_str} for resumability."""
    seen = {}
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                seen[r["id"]] = line
    return seen


def check_url(url: str, host_timestamps: defaultdict) -> tuple[int | None, str | None]:
    """GET url with 20s timeout, return (status_code, exception_name)."""
    now = time.monotonic()
    last = host_timestamps.get(url, 0)
    wait = max(0, RATE_LIMIT - (now - last))
    if wait > 0:
        time.sleep(wait)
    host_timestamps[url] = time.monotonic()

    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=20,
            allow_redirects=True,
        )
        return r.status_code, None
    except Exception as e:
        return None, type(e).__name__


def lookup_wayback(url: str) -> str | None:
    """Query Wayback API, return closest snapshot URL or None."""
    try:
        r = requests.get(WAYBACK_URL.format(url), timeout=10)
        data = r.json()
        closest = data.get("archived_snapshots", {}).get("closest", {})
        if closest.get("available"):
            return closest["url"]
        return None
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Catalogue link audit")
    parser.add_argument("--region-batch", help="Comma-separated batches e.g. MTS1-A,MTS1-B")
    parser.add_argument("--limit", type=int, help="Max rows to process")
    args = parser.parse_args()

    allowed_countries = load_country_batches(args.region_batch)
    seen = load_seen(OUTPUT)

    # Counters for summary
    ok_count = 0
    dead_with_archive = 0
    dead_without_archive = 0
    written = 0
    skipped = 0
    host_timestamps: defaultdict = defaultdict(float)

    with open(CATALOGUE, encoding="utf-8") as fin:
        for line_num, line in enumerate(fin):
            if args.limit is not None and written >= args.limit:
                break

            row = json.loads(line)
            rid = row.get("id", f"line_{line_num}")

            # Skip if already audited (resumable)
            if rid in seen:
                skipped += 1
                continue

            # Country filter
            country = row.get("country_label", "")
            if allowed_countries is not None and country not in allowed_countries:
                skipped += 1
                continue

            # Get first URL (semicolon-separated list possible)
            raw_urls = row.get("source_url", "")
            url = raw_urls.split(";")[0].strip()
            if not url:
                continue

            # Check URL
            status, exc = check_url(url, host_timestamps)

            # Determine result
            if status is not None and 200 <= status < 400:
                result = {"status": status, "archive_url": None}
                ok_count += 1
            else:
                archive = lookup_wayback(url)
                result = {"status": status, "exception": exc, "archive_url": archive}
                if archive:
                    dead_with_archive += 1
                else:
                    dead_without_archive += 1

            record = {
                "id": rid,
                "url": url,
                "country": country,
                **result,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(OUTPUT, "a", encoding="utf-8") as out:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

            if written % 50 == 0:
                print(f"Progress: {written} processed, {skipped} skipped")

    # Summary
    print(f"\n=== Link Audit Summary ===")
    print(f"Processed: {written}")
    print(f"Skipped (already done): {skipped}")
    print(f"OK: {ok_count}")
    print(f"Dead with archive: {dead_with_archive}")
    print(f"Dead without archive: {dead_without_archive}")


if __name__ == "__main__":
    main()
