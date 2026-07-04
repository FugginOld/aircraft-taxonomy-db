#!/usr/bin/env python3
"""
Expand aircraft aliases from a seed alias CSV in a way that is compatible with the
latest aircraft normalizer.

Compatibility target
--------------------
The latest normalizer loads aliases using only these columns:
    raw_value,match_key

This script therefore writes a normalizer-ready file containing exactly those two
columns, plus separate review/rejected files with extra metadata.

Usage
-----
python3 expand_aircraft_aliases_v2.py aliases.csv
python3 expand_aircraft_aliases_v2.py aliases.csv --public-metadata opensky.csv faa.csv
python3 expand_aircraft_aliases_v2.py aliases.csv --output-dir out/

Outputs
-------
<stem>_verified_expanded.csv               # includes metadata columns
<stem>_verified_expanded_for_normalizer.csv  # EXACTLY raw_value,match_key
<stem>_ambiguous_review.csv
<stem>_rejected.csv
<stem>_expansion_report.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from taxonomy_constants import MATCHKEY_RE, detect_delimiter, norm_ws

AMBIGUOUS_TERMS: Set[str] = {
    "jayhawk",
    "merlin",
    "lynx",
    "panther",
    "dolphin",
    "sentry",
    "hornet",
    "atlas",
    "harrier",
    "hawk",
    "beaver",
    "caravan",
    "tutor",
    "vigilant",
    "explorer",
    "premier",
    "poseidon",
    "orion",
    "chipmunk",
    "gazelle",
    "puma",
    "globemaster",
    "stallion",
    "super puma",
    "seahawk",
    "black hawk",
    "blackhawk",
}

PUBLIC_MATCHKEY_COLUMNS = (
    "typecode", "icao_type", "aircraft_type", "designator", "match_key", "icao"
)

PUBLIC_MODEL_COLUMNS = (
    "model", "manufacturername", "manufacturer_name", "type", "aircraft_model",
    "description", "name", "model_name"
)

WHITESPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[/_,.;:]+")
HYPHEN_VARIANTS_RE = re.compile(r"[-‐‑‒–—]+")
MULTISPACE_DASH_RE = re.compile(r"\s*-\s*")
NON_ALIAS_CHARS_RE = re.compile(r"[^a-z0-9 +\-]+")

def canonical_alias(s: str) -> str:
    s = (s or "").strip().lower()
    s = HYPHEN_VARIANTS_RE.sub("-", s)
    s = PUNCT_RE.sub(" ", s)
    s = MULTISPACE_DASH_RE.sub("-", s)
    s = NON_ALIAS_CHARS_RE.sub(" ", s)
    s = WHITESPACE_RE.sub(" ", s).strip()
    return s

def looks_like_matchkey(value: str) -> bool:
    return bool(MATCHKEY_RE.match((value or "").strip().upper()))

def generate_safe_variants(raw: str) -> Set[str]:
    raw = canonical_alias(raw)
    if not raw:
        return set()

    variants = {raw}

    # spacing/hyphen toggles
    variants.add(raw.replace("-", " "))
    variants.add(raw.replace("-", ""))
    variants.add(raw.replace(" ", ""))
    variants.add(raw.replace(" ", "-"))

    tokens = raw.split()
    if len(tokens) >= 2:
        variants.add(" ".join(tokens))
        variants.add("-".join(tokens))
        variants.add("".join(tokens))

    # c-130 <-> c130 <-> c 130
    m = re.match(r"^([a-z]{1,4})[- ]?(\d+[a-z]?)$", raw)
    if m:
        pfx, num = m.groups()
        variants.add(f"{pfx}-{num}")
        variants.add(f"{pfx} {num}")
        variants.add(f"{pfx}{num}")

    # ec 225 <-> ec225 <-> ec-225
    m2 = re.match(r"^([a-z]{1,4})\s+(\d+[a-z]?)$", raw)
    if m2:
        pfx, num = m2.groups()
        variants.add(f"{pfx}{num}")
        variants.add(f"{pfx}-{num}")
        variants.add(f"{pfx} {num}")

    manufacturer_prefixes = (
        "airbus", "boeing", "bell", "cessna", "de havilland", "embraer",
        "gulfstream", "hawker", "kamov", "learjet", "lockheed", "pilatus",
        "piper", "saab", "sikorsky", "bombardier", "beech", "beechcraft",
        "eurocopter", "agustawestland", "leonardo", "antonov", "ilyushin",
        "tupolev", "yakovlev", "northrop", "mil", "aerospatiale", "douglas",
        "general dynamics", "general atomics", "dassault"
    )
    for prefix in manufacturer_prefixes:
        if raw.startswith(prefix + " "):
            tail = raw[len(prefix) + 1:].strip()
            if tail and re.search(r"[0-9]", tail):
                variants.add(tail)

    variants.add(raw.replace(" mark ", " mk "))
    variants.add(raw.replace(" mk ", " mark "))

    return {v.strip() for v in variants if v.strip()}

def read_seed_aliases(path: Path) -> List[Dict[str, str]]:
    delimiter = detect_delimiter(path)
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        required = {"raw_value", "match_key"}
        if not reader.fieldnames or not required.issubset({c.strip() for c in reader.fieldnames}):
            raise ValueError("Seed alias file must have columns: raw_value,match_key")
        rows: List[Dict[str, str]] = []
        for row in reader:
            raw = norm_ws(row.get("raw_value", ""))
            key = (row.get("match_key", "") or "").strip().upper()
            if raw and key:
                rows.append({"raw_value": raw, "match_key": key})
        return rows

def sniff_public_columns(fieldnames: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
    lowered = {f.lower().strip(): f for f in fieldnames}
    mk = None
    model = None
    for c in PUBLIC_MATCHKEY_COLUMNS:
        if c in lowered:
            mk = lowered[c]
            break
    for c in PUBLIC_MODEL_COLUMNS:
        if c in lowered:
            model = lowered[c]
            break
    return mk, model

def read_public_metadata(paths: Sequence[Path]) -> List[Tuple[str, str, str]]:
    out: List[Tuple[str, str, str]] = []
    for path in paths:
        try:
            delimiter = detect_delimiter(path)
            with path.open("r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                if not reader.fieldnames:
                    continue
                mk_col, model_col = sniff_public_columns(reader.fieldnames)
                if not mk_col or not model_col:
                    continue
                for row in reader:
                    mk = (row.get(mk_col, "") or "").strip().upper()
                    model = norm_ws(row.get(model_col, ""))
                    if not mk or not model or not looks_like_matchkey(mk):
                        continue
                    out.append((model, mk, path.name))
        except Exception:
            continue
    return out

def is_ambiguous(alias: str) -> bool:
    a = canonical_alias(alias)
    if not a:
        return True
    if a in AMBIGUOUS_TERMS:
        return True
    if " " not in a and "-" not in a and not re.search(r"\d", a):
        return True
    generic = {
        "atlas", "hawk", "trainer", "mentor", "tutor", "explorer", "premier",
        "caravan", "beaver", "vigilant", "stallion", "super hercules"
    }
    return a in generic

def reason_for_reject(alias: str, match_key: str) -> Optional[str]:
    a = canonical_alias(alias)
    if not a:
        return "empty_alias"
    if not looks_like_matchkey(match_key):
        return "invalid_match_key_format"
    if len(a) < 2:
        return "alias_too_short"
    return None

def expand_aliases(seed_rows: List[Dict[str, str]], public_rows: List[Tuple[str, str, str]]):
    verified: Dict[Tuple[str, str], Dict[str, str]] = {}
    ambiguous: Dict[Tuple[str, str], Dict[str, str]] = {}
    rejected: Dict[Tuple[str, str], Dict[str, str]] = {}
    alias_to_keys: Dict[str, Set[str]] = defaultdict(set)
    alias_sources: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

    for row in seed_rows:
        raw = row["raw_value"]
        key = row["match_key"]
        reason = reason_for_reject(raw, key)
        if reason:
            rejected[(raw, key)] = {
                "raw_value": raw,
                "match_key": key,
                "reason": reason,
                "source": "seed",
            }
            continue
        for variant in generate_safe_variants(raw):
            alias_to_keys[variant].add(key)
            alias_sources[(variant, key)].add("seed")

    for model, key, source_file in public_rows:
        if reason_for_reject(model, key):
            continue
        for variant in generate_safe_variants(model):
            alias_to_keys[variant].add(key)
            alias_sources[(variant, key)].add(source_file)

    for alias, keys in alias_to_keys.items():
        if len(keys) > 1 or is_ambiguous(alias):
            for key in sorted(keys):
                ambiguous[(alias, key)] = {
                    "raw_value": alias,
                    "match_key": key,
                    "reason": "alias_maps_to_multiple_match_keys" if len(keys) > 1 else "ambiguous_alias",
                    "source": ";".join(sorted(alias_sources[(alias, key)])),
                }
        else:
            key = next(iter(keys))
            verified[(alias, key)] = {
                "raw_value": alias,
                "match_key": key,
                "source": ";".join(sorted(alias_sources[(alias, key)])),
            }

    stats = {
        "seed_rows": len(seed_rows),
        "public_rows_used": len(public_rows),
        "verified_rows": len(verified),
        "ambiguous_rows": len(ambiguous),
        "rejected_rows": len(rejected),
        "unique_aliases_seen": len(alias_to_keys),
    }
    return (
        sorted(verified.values(), key=lambda r: (r["match_key"], r["raw_value"])),
        sorted(ambiguous.values(), key=lambda r: (r["raw_value"], r["match_key"])),
        sorted(rejected.values(), key=lambda r: (r["reason"], r["match_key"], r["raw_value"])),
        stats,
    )

def write_csv(path: Path, rows: Sequence[Dict[str, str]], fieldnames: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Expand aircraft aliases from a seed alias CSV.")
    parser.add_argument("seed_aliases", help="CSV/TSV with raw_value,match_key columns")
    parser.add_argument("--public-metadata", nargs="*", default=[], help="Optional public metadata CSVs to mine")
    parser.add_argument("--output-dir", default=None, help="Directory for outputs; defaults to same directory as seed file")
    args = parser.parse_args(argv)

    seed_path = Path(args.seed_aliases)
    out_dir = Path(args.output_dir) if args.output_dir else seed_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_rows = read_seed_aliases(seed_path)
    public_rows = read_public_metadata([Path(p) for p in args.public_metadata])

    verified_rows, ambiguous_rows, rejected_rows, stats = expand_aliases(seed_rows, public_rows)

    stem = seed_path.stem
    verified_path = out_dir / f"{stem}_verified_expanded.csv"
    verified_normalizer_path = out_dir / f"{stem}_verified_expanded_for_normalizer.csv"
    ambiguous_path = out_dir / f"{stem}_ambiguous_review.csv"
    rejected_path = out_dir / f"{stem}_rejected.csv"
    report_path = out_dir / f"{stem}_expansion_report.json"

    write_csv(verified_path, verified_rows, ["raw_value", "match_key", "source"])
    write_csv(
        verified_normalizer_path,
        [{"raw_value": r["raw_value"], "match_key": r["match_key"]} for r in verified_rows],
        ["raw_value", "match_key"],
    )
    write_csv(ambiguous_path, ambiguous_rows, ["raw_value", "match_key", "reason", "source"])
    write_csv(rejected_path, rejected_rows, ["raw_value", "match_key", "reason", "source"])

    report = {
        "seed_aliases": str(seed_path),
        "public_metadata_files": args.public_metadata,
        "outputs": {
            "verified": str(verified_path),
            "verified_for_normalizer": str(verified_normalizer_path),
            "ambiguous": str(ambiguous_path),
            "rejected": str(rejected_path),
        },
        "stats": stats,
        "compatibility": {
            "normalizer_alias_columns": ["raw_value", "match_key"],
            "use_with_normalizer": str(verified_normalizer_path),
        },
        "notes": [
            "Ambiguous nicknames are intentionally withheld from direct auto-mapping.",
            "Use ICAO/FAA to validate match_key designators before promoting aliases.",
            "Public metadata files improve recall but should not be treated as canonical by themselves.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
