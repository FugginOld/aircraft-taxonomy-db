#!/usr/bin/env python3
"""Promote manually reviewed lookup rows into the canonical aircraft_type_lookup.csv.

Expected reviewed CSV columns:
match_key,normalized_type,category,tag1,tag2,tag3
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

from taxonomy_constants import LOOKUP_COLUMNS, detect_delimiter, norm_lookup_key

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    delim = detect_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        return {
            norm_lookup_key(row.get("match_key") or ""): {c: (row.get(c) or "").strip() for c in LOOKUP_COLUMNS}
            for row in reader if (row.get("match_key") or "").strip()
        }


def write_rows(path: Path, rows: dict[str, dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOOKUP_COLUMNS)
        writer.writeheader()
        for _, row in sorted(rows.items(), key=lambda kv: kv[1]["match_key"].casefold()):
            writer.writerow(row)


def main() -> int:
    p = argparse.ArgumentParser(description="Promote reviewed lookup rows")
    p.add_argument("reviewed", help="Reviewed lookup CSV")
    p.add_argument("--target", default="taxonomy/aircraft_type_lookup.csv", help="Canonical lookup target")
    args = p.parse_args()

    reviewed = load_rows(Path(args.reviewed))
    target_path = Path(args.target)
    target = load_rows(target_path)
    target.update(reviewed)
    write_rows(target_path, target)
    logger.info("Promoted %d row(s) into %s", len(reviewed), target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
