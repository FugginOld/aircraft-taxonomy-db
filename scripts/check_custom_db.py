#!/usr/bin/env python3
"""Validate ``data/aircraft-taxonomy-custom-db.csv`` before it is merged.

Checks
------
1. The file is a well-formed CSV with the required column headers.
2. Every ``$ICAO`` value is a valid hexadecimal string.
3. There are no duplicate ``$ICAO`` codes within the submission file.
4. Every non-empty ``Category`` value appears in the canonical allowlist
   (``scripts/taxonomy_constants.ALLOWED_CATEGORIES``).  Empty Category is
   permitted — the post-merge normaliser will attempt to fill it from the
   taxonomy lookup table.

Exit codes
----------
0  All checks passed (or file has no data rows — header-only is valid).
1  One or more checks failed.
"""
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CUSTOM_DB = Path("data/aircraft-taxonomy-custom-db.csv")

REQUIRED_COLUMNS = {
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
}


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _load_allowed_categories() -> set[str]:
    """Return the canonical category allowlist from taxonomy_constants."""
    scripts_dir = str(Path(__file__).parent.resolve())
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from taxonomy_constants import ALLOWED_CATEGORIES  # noqa: PLC0415
    return set(ALLOWED_CATEGORIES)


def main() -> int:
    failed = False

    # ------------------------------------------------------------------
    # Check 1: file exists and header is well-formed
    # ------------------------------------------------------------------
    if not CUSTOM_DB.exists():
        logger.error("Custom database not found: %s", CUSTOM_DB)
        return 1

    with CUSTOM_DB.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        try:
            fieldnames = set(reader.fieldnames or [])
        except Exception as exc:
            logger.error("Could not read %s as a CSV: %s", CUSTOM_DB, exc)
            return 1

        missing_cols = REQUIRED_COLUMNS - fieldnames
        if missing_cols:
            logger.error(
                "Missing required column(s) in %s: %s",
                CUSTOM_DB,
                sorted(missing_cols),
            )
            return 1

        rows = list(reader)

    if not rows:
        logger.info("%s has no data rows — nothing to validate.", CUSTOM_DB)
        return 0

    logger.info("Validating %d submission row(s) in %s.", len(rows), CUSTOM_DB)

    # ------------------------------------------------------------------
    # Check 2: valid hexadecimal ICAO codes
    # ------------------------------------------------------------------
    invalid_icaos = [
        (i + 2, row.get("$ICAO", ""))
        for i, row in enumerate(rows)
        if not _is_hex((row.get("$ICAO") or "").strip())
    ]
    if invalid_icaos:
        failed = True
        logger.error("Invalid (non-hexadecimal) $ICAO values:")
        for line_num, icao in invalid_icaos:
            logger.error("  row %d: %r", line_num, icao)

    # ------------------------------------------------------------------
    # Check 3: no duplicate $ICAO codes within the submission file
    # ------------------------------------------------------------------
    seen: dict[str, int] = {}
    duplicates: list[tuple[int, str]] = []
    for i, row in enumerate(rows):
        icao = (row.get("$ICAO") or "").strip().upper()
        if icao in seen:
            duplicates.append((i + 2, icao))
        else:
            seen[icao] = i + 2
    if duplicates:
        failed = True
        logger.error("Duplicate $ICAO codes within %s:", CUSTOM_DB)
        for line_num, icao in duplicates:
            logger.error("  row %d: %s (first seen at row %d)", line_num, icao, seen[icao])

    # ------------------------------------------------------------------
    # Check 4: non-empty Category values must be in the canonical allowlist
    # Empty Category is allowed — the normaliser fills it from the lookup.
    # ------------------------------------------------------------------
    try:
        allowed_categories = _load_allowed_categories()
    except Exception as exc:
        logger.warning("Could not load taxonomy_constants — skipping category check: %s", exc)
        allowed_categories = None

    if allowed_categories is not None:
        invalid_categories: list[tuple[int, str]] = [
            (i + 2, row.get("Category", ""))
            for i, row in enumerate(rows)
            if (category := (row.get("Category") or "").strip())
            and category not in allowed_categories
        ]
        if invalid_categories:
            failed = True
            logger.error(
                "Invalid Category values (not in the canonical taxonomy allowlist):"
            )
            for line_num, cat in invalid_categories:
                logger.error("  row %d: %r", line_num, cat)

    if failed:
        sys.stdout.write(
            f"{CUSTOM_DB} failed one or more validation checks. "
            "See the log output above for details.\n"
        )
        return 1

    logger.info("All validation checks passed for %s.", CUSTOM_DB)
    return 0


if __name__ == "__main__":
    sys.exit(main())
