#!/usr/bin/env python3
"""
Validate and score aircraft lookup/alias data against cached public reference files.

Purpose
- consume local CSV/TSV reference exports (for example OpenSky metadata snapshots)
- score lookup rows and aliases with evidence
- emit normalizer-ready aliases and a validated lookup file
- keep weak/ambiguous candidates in review queues

Notes
- This script intentionally works from LOCAL cached files. It does not fetch on its own.
- It is designed to fit around normalize_aircraft_v5.py, whose alias loader expects:
      raw_value,match_key
- FAA/ICAO sources are still best for designator authority, but their public formats are
  not as automation-friendly as a plain metadata CSV, so this validator treats local CSV/TSV
  exports as the machine-readable evidence layer.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

MATCHKEY_RE = re.compile(r"^[A-Z0-9]{2,5}$")
WS_RE = re.compile(r"\s+")
HYPHEN_RE = re.compile(r"[-‐‑‒–—]+")
PUNCT_RE = re.compile(r"[/_,.;:]+")
NON_ALIAS_CHARS_RE = re.compile(r"[^a-z0-9 +\-]+")

LOOKUP_REQUIRED = {"match_key", "normalized_type", "category", "tag1", "tag2", "tag3"}
ALIAS_REQUIRED = {"raw_value", "match_key"}

PUBLIC_MATCHKEY_COLUMNS = (
    "typecode", "icao_type", "aircraft_type", "designator", "match_key", "icao", "aircrafttype"
)
PUBLIC_MODEL_COLUMNS = (
    "model", "manufacturername", "manufacturer_name", "type", "aircraft_model",
    "description", "name", "model_name", "aircraft", "model_full"
)

def norm_ws(value: str) -> str:
    return WS_RE.sub(" ", (value or "").strip())

def norm_matchkey(value: str) -> str:
    return norm_ws(value).upper()

def canonical_alias(value: str) -> str:
    s = (value or "").strip().lower()
    s = HYPHEN_RE.sub("-", s)
    s = PUNCT_RE.sub(" ", s)
    s = NON_ALIAS_CHARS_RE.sub(" ", s)
    s = WS_RE.sub(" ", s).strip()
    return s

def looks_like_matchkey(value: str) -> bool:
    return bool(MATCHKEY_RE.match(norm_matchkey(value)))

def sniff_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8-sig", errors="ignore")[:8192]
    if sample.count("\t") > sample.count(","):
        return "\t"
    return ","

def read_lookup(path: Path) -> Dict[str, Dict[str, str]]:
    delim = sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        missing = LOOKUP_REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Lookup missing required columns: {sorted(missing)}")
        out = {}
        for row in reader:
            key = norm_matchkey(row.get("match_key", ""))
            if key:
                out[key] = {k: norm_ws(v) for k, v in row.items()}
                out[key]["match_key"] = key
        return out

def read_aliases(path: Path) -> Dict[Tuple[str, str], Dict[str, str]]:
    delim = sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=delim)
        missing = ALIAS_REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Aliases missing required columns: {sorted(missing)}")
        out = {}
        for row in reader:
            raw = canonical_alias(row.get("raw_value", ""))
            key = norm_matchkey(row.get("match_key", ""))
            if raw and key:
                out[(raw, key)] = {"raw_value": raw, "match_key": key}
        return out

def sniff_public_columns(fieldnames: Sequence[str]) -> Tuple[Optional[str], Optional[str]]:
    lowered = {c.lower().strip(): c for c in fieldnames}
    mk = next((lowered[c] for c in PUBLIC_MATCHKEY_COLUMNS if c in lowered), None)
    model = next((lowered[c] for c in PUBLIC_MODEL_COLUMNS if c in lowered), None)
    return mk, model

def iter_public_rows(paths: Sequence[Path]) -> Iterable[Tuple[str, str, str]]:
    """
    Yield tuples: (match_key, model_text, source_name)
    """
    for path in paths:
        if not path.exists() or path.suffix.lower() not in {".csv", ".tsv"}:
            continue
        delim = sniff_delimiter(path)
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=delim)
            if not reader.fieldnames:
                continue
            mk_col, model_col = sniff_public_columns(reader.fieldnames)
            if not mk_col or not model_col:
                continue
            for row in reader:
                mk = norm_matchkey(row.get(mk_col, ""))
                model = norm_ws(row.get(model_col, ""))
                if mk and model:
                    yield mk, model, path.name

def build_evidence_index(paths: Sequence[Path]) -> Tuple[Dict[str, dict], Dict[str, set]]:
    """
    Returns:
    - by_matchkey: evidence summary keyed by match_key
    - alias_to_matchkeys: exact normalized model/alias text -> set(match_key)
    """
    by_matchkey: Dict[str, dict] = defaultdict(lambda: {"models": set(), "sources": set(), "rows": 0})
    alias_to_matchkeys: Dict[str, set] = defaultdict(set)

    for mk, model, source in iter_public_rows(paths):
        by_matchkey[mk]["models"].add(model)
        by_matchkey[mk]["sources"].add(source)
        by_matchkey[mk]["rows"] += 1

        alias_to_matchkeys[canonical_alias(model)].add(mk)

        low = canonical_alias(model)
        # mild safe variants
        variants = {
            low,
            low.replace("-", " "),
            low.replace("-", ""),
            low.replace(" ", ""),
            low.replace(" ", "-"),
        }
        for v in variants:
            if v:
                alias_to_matchkeys[v].add(mk)

    return by_matchkey, alias_to_matchkeys

def score_lookup_row(row: Dict[str, str], evidence: Dict[str, dict]) -> Tuple[str, str]:
    key = row["match_key"]
    ev = evidence.get(key)
    if not looks_like_matchkey(key):
        return "rejected", "invalid_match_key"
    if not ev:
        return "review", "no_public_evidence"
    norm_type = canonical_alias(row.get("normalized_type", ""))
    exact = any(canonical_alias(m) == norm_type for m in ev["models"])
    if exact:
        return "validated", "exact_model_match"
    return "validated", "match_key_present"

def score_alias(raw_value: str, match_key: str, evidence: Dict[str, dict], alias_map: Dict[str, set]) -> Tuple[str, str]:
    if not looks_like_matchkey(match_key):
        return "rejected", "invalid_match_key"
    ev = evidence.get(match_key)
    if not ev:
        return "review", "match_key_not_in_public_metadata"
    candidates = alias_map.get(canonical_alias(raw_value), set())
    if candidates == {match_key}:
        return "validated", "exact_alias_unique_match"
    if match_key in candidates and len(candidates) > 1:
        return "review", "alias_collision_in_public_metadata"
    if match_key in candidates:
        return "validated", "alias_supported"
    return "review", "alias_not_seen_in_public_metadata"

def write_csv(path: Path, fieldnames: List[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def main() -> int:
    p = argparse.ArgumentParser(description="Validate aircraft alias/lookup data against cached public metadata")
    p.add_argument("--lookup", required=True, help="Lookup CSV/TSV")
    p.add_argument("--aliases", required=True, help="Alias CSV/TSV")
    p.add_argument("--public-metadata", nargs="*", default=[], help="Local CSV/TSV metadata exports")
    p.add_argument("--output-dir", default=".", help="Output directory")
    args = p.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    lookup = read_lookup(Path(args.lookup))
    aliases = read_aliases(Path(args.aliases))
    public_paths = [Path(p) for p in args.public_metadata]
    evidence, alias_map = build_evidence_index(public_paths)

    validated_lookup = []
    review_lookup = []
    validated_aliases = []
    review_aliases = []
    rejected_aliases = []

    for key, row in sorted(lookup.items()):
        status, reason = score_lookup_row(row, evidence)
        out = {
            "match_key": row["match_key"],
            "normalized_type": row.get("normalized_type", ""),
            "category": row.get("category", ""),
            "tag1": row.get("tag1", ""),
            "tag2": row.get("tag2", ""),
            "tag3": row.get("tag3", ""),
            "validation_status": status,
            "validation_reason": reason,
            "public_model_count": len(evidence.get(key, {}).get("models", set())),
            "public_source_count": len(evidence.get(key, {}).get("sources", set())),
        }
        if status == "validated":
            validated_lookup.append(out)
        else:
            review_lookup.append(out)

    for (raw, key), row in sorted(aliases.items()):
        status, reason = score_alias(raw, key, evidence, alias_map)
        out = {
            "raw_value": raw,
            "match_key": key,
            "validation_status": status,
            "validation_reason": reason,
            "public_collision_count": len(alias_map.get(raw, set())),
        }
        if status == "validated":
            validated_aliases.append(out)
        elif status == "review":
            review_aliases.append(out)
        else:
            rejected_aliases.append(out)

    # canonical outputs
    write_csv(
        outdir / "aircraft_type_lookup_validated.csv",
        ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3", "validation_status", "validation_reason", "public_model_count", "public_source_count"],
        validated_lookup,
    )
    write_csv(
        outdir / "aircraft_type_lookup_review.csv",
        ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3", "validation_status", "validation_reason", "public_model_count", "public_source_count"],
        review_lookup,
    )
    write_csv(
        outdir / "aircraft_type_aliases_validated.csv",
        ["raw_value", "match_key", "validation_status", "validation_reason", "public_collision_count"],
        validated_aliases,
    )
    write_csv(
        outdir / "aircraft_type_aliases_validated_for_normalizer.csv",
        ["raw_value", "match_key"],
        ({"raw_value": r["raw_value"], "match_key": r["match_key"]} for r in validated_aliases),
    )
    write_csv(
        outdir / "aircraft_type_aliases_review.csv",
        ["raw_value", "match_key", "validation_status", "validation_reason", "public_collision_count"],
        review_aliases,
    )
    write_csv(
        outdir / "aircraft_type_aliases_rejected.csv",
        ["raw_value", "match_key", "validation_status", "validation_reason", "public_collision_count"],
        rejected_aliases,
    )

    report = {
        "lookup_validated": len(validated_lookup),
        "lookup_review": len(review_lookup),
        "aliases_validated": len(validated_aliases),
        "aliases_review": len(review_aliases),
        "aliases_rejected": len(rejected_aliases),
        "public_files_used": [str(p) for p in public_paths if p.exists()],
    }
    (outdir / "aircraft_reference_validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
