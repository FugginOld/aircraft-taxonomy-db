#!/usr/bin/env python3
"""Download and cache public aircraft reference sources.

This script does not change your lookup or alias files directly.
It refreshes local cache files that can later be consumed by the weekly pipeline.

Sources supported by default:
- OpenSky aircraft metadata CSV (public, downloadable)
- FAA JO 7340.2P PDF metadata URL (cached as a file reference only)
- ICAO Doc 8643 search page metadata URL (cached as a file reference only)

The script is intentionally conservative because ICAO's online database and FAA's PDF
are authoritative for designators, while OpenSky is more useful for discovery than for
canonical truth. Store and inspect cache artifacts before promoting anything.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import urllib.request
from datetime import datetime, timezone

DEFAULT_SOURCES = {
    "opensky_aircraft_metadata_csv": "https://opensky-network.org/datasets/metadata/aircraftDatabase.csv",
    "faa_jo_7340_2p_pdf": "https://www.faa.gov/documentLibrary/media/Order/7340.2P_dtd_8-7-25.pdf",
    "icao_doc_8643_search": "https://www.icao.int/operational-safety/doc-8643-aircraft-type-designators/search",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fetch(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "aircraft-normalizer/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())


def main() -> int:
    p = argparse.ArgumentParser(description="Cache public aircraft reference sources")
    p.add_argument("--cache-dir", default="cache/public_sources", help="Cache directory")
    p.add_argument("--sources", nargs="*", choices=list(DEFAULT_SOURCES.keys()), default=list(DEFAULT_SOURCES.keys()))
    args = p.parse_args()

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"timestamp_utc": now_utc(), "sources": []}

    for key in args.sources:
        url = DEFAULT_SOURCES[key]
        ext = ".csv" if url.endswith(".csv") else ".pdf" if url.endswith(".pdf") else ".html"
        dest = cache_dir / f"{key}{ext}"
        fetch(url, dest)
        manifest["sources"].append({"key": key, "url": url, "path": str(dest)})

    (cache_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
