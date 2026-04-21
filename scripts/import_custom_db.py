#!/usr/bin/env python3
"""Import custom aircraft submissions into the main taxonomy database.

Workflow
--------
1. Read ``data/aircraft-taxonomy-custom-db.csv``.
2. If there are no data rows, exit 0 (nothing to do).
3. Normalise the rows using the published taxonomy lookup + aliases.
4. Deduplicate against ``data/aircraft-taxonomy-db.csv`` (keyed on ``$ICAO``).
5. Append new, normalised rows to ``data/aircraft-taxonomy-db.csv``.
6. Move any review-required rows to ``review/aircraft-taxonomy-custom-db_review.csv``.
7. Reset ``data/aircraft-taxonomy-custom-db.csv`` to header-only (clear-after-import).

Exit codes
----------
0  Success (including "nothing to import").
1  Validation or I/O error.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Column order for the main and custom databases
DB_COLUMNS = [
    "$ICAO",
    "$Registration",
    "$Operator",
    "$Type",
    "$ICAO Type",
    "#CMPG",
    "$Tag 1",
    "$#Tag 2",
    "$#Tag 3",
    "Category",
]


def _add_scripts_to_path() -> None:
    scripts_dir = str(Path(__file__).parent.resolve())
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


def _load_normalizer():
    _add_scripts_to_path()
    try:
        from normalize_aircraft_v5 import load_lookup, load_aliases, process_file  # noqa: PLC0415
        return load_lookup, load_aliases, process_file
    except ImportError as exc:
        logger.error("Cannot import normalize_aircraft_v5: %s", exc)
        sys.exit(1)


def _count_data_rows(path: Path) -> int:
    """Return the number of non-header rows in a CSV file."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # skip header
        return sum(1 for _ in reader)


def _load_existing_icaos(main_db: Path) -> set[str]:
    icaos: set[str] = set()
    with main_db.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            icao = (row.get("$ICAO") or "").strip().upper()
            if icao:
                icaos.add(icao)
    return icaos


def _reset_to_header(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=DB_COLUMNS)
        writer.writeheader()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import custom aircraft submissions into the main taxonomy database."
    )
    parser.add_argument(
        "--custom-db",
        default="data/aircraft-taxonomy-custom-db.csv",
        help="Path to the custom submission database (default: data/aircraft-taxonomy-custom-db.csv)",
    )
    parser.add_argument(
        "--main-db",
        default="data/aircraft-taxonomy-db.csv",
        help="Path to the main taxonomy database (default: data/aircraft-taxonomy-db.csv)",
    )
    parser.add_argument(
        "--lookup",
        default="taxonomy/aircraft_type_lookup.csv",
        help="Path to the canonical taxonomy lookup CSV",
    )
    parser.add_argument(
        "--aliases",
        default="taxonomy/aircraft_type_aliases.csv",
        help="Path to the canonical taxonomy aliases CSV",
    )
    parser.add_argument(
        "--review-dir",
        default="review",
        help="Directory to store review-required rows (default: review/)",
    )
    args = parser.parse_args(argv)

    custom_path = Path(args.custom_db)
    main_path = Path(args.main_db)
    review_dir = Path(args.review_dir)

    # ------------------------------------------------------------------
    # Guard: nothing to do if the inbox is empty
    # ------------------------------------------------------------------
    if not custom_path.exists():
        logger.error("Custom database not found: %s", custom_path)
        return 1

    row_count = _count_data_rows(custom_path)
    if row_count == 0:
        logger.info("No pending submissions in %s — nothing to import.", custom_path)
        return 0

    logger.info("Found %d pending submission(s) in %s.", row_count, custom_path)

    # ------------------------------------------------------------------
    # Normalise the custom-db file
    # ------------------------------------------------------------------
    load_lookup, load_aliases, process_file = _load_normalizer()

    try:
        lookup = load_lookup(str(args.lookup))
        aliases = load_aliases(str(args.aliases))
    except Exception as exc:
        logger.error("Failed to load taxonomy references: %s", exc)
        return 1

    try:
        normalized_path_str, review_path_str, stats = process_file(
            str(custom_path), lookup, aliases, no_audit_cols=True
        )
    except Exception as exc:
        logger.error("Normalisation failed: %s", exc)
        return 1

    normalized_path = Path(normalized_path_str)
    review_path = Path(review_path_str)

    logger.info(
        "Normalisation complete — normalised: %d, review_required: %d",
        stats["rows_normalized"],
        stats["rows_review"],
    )

    # ------------------------------------------------------------------
    # Deduplicate against the main database
    # ------------------------------------------------------------------
    existing_icaos = _load_existing_icaos(main_path)

    with normalized_path.open(encoding="utf-8-sig", newline="") as fh:
        normalized_rows = list(csv.DictReader(fh))

    new_rows = [
        r for r in normalized_rows
        if (r.get("$ICAO") or "").strip().upper() not in existing_icaos
    ]
    skipped = len(normalized_rows) - len(new_rows)
    if skipped:
        logger.info("Skipped %d row(s) whose ICAO code already exists in the main database.", skipped)

    # ------------------------------------------------------------------
    # Append new rows to the main database
    # ------------------------------------------------------------------
    if new_rows:
        with main_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=DB_COLUMNS, extrasaction="ignore")
            for row in new_rows:
                writer.writerow(row)
        logger.info("Appended %d new row(s) to %s.", len(new_rows), main_path)
    else:
        logger.info("No new rows to append (all submissions were duplicates).")

    # ------------------------------------------------------------------
    # Handle review-required rows
    # ------------------------------------------------------------------
    with review_path.open(encoding="utf-8-sig", newline="") as fh:
        review_rows = list(csv.DictReader(fh))

    if review_rows:
        review_dir.mkdir(parents=True, exist_ok=True)
        dest = review_dir / review_path.name
        shutil.move(str(review_path), str(dest))
        logger.info(
            "%d review-required row(s) moved to %s.",
            len(review_rows),
            dest,
        )
    else:
        review_path.unlink(missing_ok=True)

    # Clean up the temporary normalised file
    normalized_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Reset custom-db to header-only (clear-after-import)
    # ------------------------------------------------------------------
    _reset_to_header(custom_path)
    logger.info("Reset %s to header-only.", custom_path)

    logger.info(
        "Import summary — imported: %d, duplicates_skipped: %d, review_required: %d",
        len(new_rows),
        skipped,
        len(review_rows),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
