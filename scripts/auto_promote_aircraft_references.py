#!/usr/bin/env python3
"""
Auto-promote reviewed lookup and alias rows into canonical files using confidence scoring.

Purpose
- read review queues produced by validate_aircraft_references.py
- optionally merge in manually reviewed decisions
- auto-promote only rows meeting a confidence threshold
- write updated canonical files without duplicating existing records

Outputs
- aircraft_type_lookup_promoted.csv
- aircraft_type_aliases_promoted.csv
- aircraft_type_aliases_promoted_for_normalizer.csv
- aircraft_promotion_report.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

WS_RE = re.compile(r"\s+")
MATCHKEY_RE = re.compile(r"^[A-Z0-9]{2,5}$")
LOOKUP_FIELDS = ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3"]
ALIAS_FIELDS = ["raw_value", "match_key"]

def norm_ws(value: str) -> str:
    return WS_RE.sub(" ", (value or "").strip())

def norm_key(value: str) -> str:
    return norm_ws(value).upper()

def norm_alias(value: str) -> str:
    return norm_ws(value).casefold()

def sniff_delimiter(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")[:8192]
    return "\t" if text.count("\t") > text.count(",") else ","

def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    delim = sniff_delimiter(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim))

def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def load_lookup_map(path: Path) -> Dict[str, dict]:
    rows = read_csv(path)
    out = {}
    for row in rows:
        key = norm_key(row.get("match_key", ""))
        if key:
            clean = {k: norm_ws(row.get(k, "")) for k in row.keys()}
            clean["match_key"] = key
            out[key] = clean
    return out

def load_alias_map(path: Path) -> Dict[Tuple[str, str], dict]:
    rows = read_csv(path)
    out = {}
    for row in rows:
        raw = norm_alias(row.get("raw_value", ""))
        key = norm_key(row.get("match_key", ""))
        if raw and key:
            clean = {k: norm_ws(row.get(k, "")) for k in row.keys()}
            clean["raw_value"] = raw
            clean["match_key"] = key
            out[(raw, key)] = clean
    return out

def lookup_confidence(row: dict) -> Tuple[float, list[str]]:
    score = 0.0
    reasons = []
    match_key = norm_key(row.get("match_key", ""))
    if MATCHKEY_RE.match(match_key):
        score += 0.20
        reasons.append("valid_match_key")
    normalized_type = norm_ws(row.get("normalized_type", ""))
    if normalized_type:
        score += 0.15
        reasons.append("has_normalized_type")
    if row.get("validation_status") == "validated":
        score += 0.25
        reasons.append("validated_status")
    reason = norm_ws(row.get("validation_reason", ""))
    if reason == "exact_model_match":
        score += 0.20
        reasons.append("exact_model_match")
    elif reason == "match_key_present":
        score += 0.10
        reasons.append("match_key_present")
    try:
        model_count = int(float(row.get("public_model_count", 0) or 0))
    except ValueError:
        model_count = 0
    try:
        source_count = int(float(row.get("public_source_count", 0) or 0))
    except ValueError:
        source_count = 0
    if model_count >= 1:
        score += 0.10
        reasons.append("public_model_seen")
    if source_count >= 2:
        score += 0.10
        reasons.append("multi_source_support")
    elif source_count == 1:
        score += 0.05
        reasons.append("single_source_support")
    return min(score, 1.0), reasons

def alias_confidence(row: dict) -> Tuple[float, list[str]]:
    score = 0.0
    reasons = []
    raw = norm_alias(row.get("raw_value", ""))
    match_key = norm_key(row.get("match_key", ""))
    if raw:
        score += 0.10
        reasons.append("has_alias")
    if MATCHKEY_RE.match(match_key):
        score += 0.20
        reasons.append("valid_match_key")
    status = norm_ws(row.get("validation_status", ""))
    reason = norm_ws(row.get("validation_reason", ""))
    if status == "validated":
        score += 0.25
        reasons.append("validated_status")
    if reason == "exact_alias_unique_match":
        score += 0.25
        reasons.append("exact_alias_unique_match")
    elif reason == "alias_supported":
        score += 0.15
        reasons.append("alias_supported")
    try:
        collisions = int(float(row.get("public_collision_count", 0) or 0))
    except ValueError:
        collisions = 0
    if collisions == 1:
        score += 0.20
        reasons.append("no_collision")
    elif collisions == 0:
        score += 0.05
        reasons.append("no_public_collision_data")
    else:
        score -= min(0.30, 0.10 * (collisions - 1))
        reasons.append("collision_penalty")
    if len(raw) >= 4:
        score += 0.05
        reasons.append("usable_alias_length")
    return max(0.0, min(score, 1.0)), reasons

def merge_lookup(existing: Dict[str, dict], reviewed: list[dict], threshold: float) -> tuple[list[dict], list[dict]]:
    promoted = []
    skipped = []
    merged = dict(existing)
    for row in reviewed:
        key = norm_key(row.get("match_key", ""))
        if not key:
            skipped.append({**row, "promotion_reason": "missing_match_key"})
            continue
        score, reasons = lookup_confidence(row)
        out = {
            "match_key": key,
            "normalized_type": norm_ws(row.get("normalized_type", "")),
            "category": norm_ws(row.get("category", "")),
            "tag1": norm_ws(row.get("tag1", "")),
            "tag2": norm_ws(row.get("tag2", "")),
            "tag3": norm_ws(row.get("tag3", "")),
            "promotion_confidence": f"{score:.2f}",
            "promotion_reasons": ";".join(reasons),
        }
        if score >= threshold and key not in merged:
            merged[key] = out
            promoted.append(out)
        else:
            why = "already_exists" if key in merged else "below_threshold"
            skipped.append({**out, "promotion_reason": why})
    final_rows = []
    for key in sorted(merged.keys()):
        row = merged[key]
        final_rows.append({
            "match_key": key,
            "normalized_type": row.get("normalized_type", ""),
            "category": row.get("category", ""),
            "tag1": row.get("tag1", ""),
            "tag2": row.get("tag2", ""),
            "tag3": row.get("tag3", ""),
        })
    return final_rows, promoted, skipped

def merge_aliases(existing: Dict[Tuple[str, str], dict], reviewed: list[dict], threshold: float) -> tuple[list[dict], list[dict], list[dict]]:
    promoted = []
    skipped = []
    merged = dict(existing)
    for row in reviewed:
        raw = norm_alias(row.get("raw_value", ""))
        key = norm_key(row.get("match_key", ""))
        pair = (raw, key)
        if not raw or not key:
            skipped.append({**row, "promotion_reason": "missing_alias_or_match_key"})
            continue
        score, reasons = alias_confidence(row)
        out = {
            "raw_value": raw,
            "match_key": key,
            "promotion_confidence": f"{score:.2f}",
            "promotion_reasons": ";".join(reasons),
        }
        if score >= threshold and pair not in merged:
            merged[pair] = out
            promoted.append(out)
        else:
            why = "already_exists" if pair in merged else "below_threshold"
            skipped.append({**out, "promotion_reason": why})
    final_rows = []
    for raw, key in sorted(merged.keys()):
        row = merged[(raw, key)]
        final_rows.append({
            "raw_value": raw,
            "match_key": key,
        })
    return final_rows, promoted, skipped

def main() -> int:
    p = argparse.ArgumentParser(description="Auto-promote reviewed aircraft lookup/alias rows with confidence scoring")
    p.add_argument("--lookup-existing", required=True, help="Current canonical lookup CSV/TSV")
    p.add_argument("--aliases-existing", required=True, help="Current canonical aliases CSV/TSV")
    p.add_argument("--lookup-review", required=True, help="Lookup review CSV/TSV")
    p.add_argument("--aliases-review", required=True, help="Alias review CSV/TSV")
    p.add_argument("--lookup-threshold", type=float, default=0.70)
    p.add_argument("--alias-threshold", type=float, default=0.75)
    p.add_argument("--output-dir", default=".")
    args = p.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    existing_lookup = load_lookup_map(Path(args.lookup_existing))
    existing_aliases = load_alias_map(Path(args.aliases_existing))
    lookup_review = read_csv(Path(args.lookup_review))
    aliases_review = read_csv(Path(args.aliases_review))

    lookup_final, lookup_promoted, lookup_skipped = merge_lookup(existing_lookup, lookup_review, args.lookup_threshold)
    alias_final, alias_promoted, alias_skipped = merge_aliases(existing_aliases, aliases_review, args.alias_threshold)

    write_csv(outdir / "aircraft_type_lookup_promoted.csv", LOOKUP_FIELDS, lookup_final)
    write_csv(outdir / "aircraft_type_lookup_promoted_candidates.csv",
              ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3", "promotion_confidence", "promotion_reasons"],
              lookup_promoted)
    write_csv(outdir / "aircraft_type_lookup_promotion_skipped.csv",
              ["match_key", "normalized_type", "category", "tag1", "tag2", "tag3", "promotion_confidence", "promotion_reasons", "promotion_reason"],
              lookup_skipped)

    write_csv(outdir / "aircraft_type_aliases_promoted.csv",
              ["raw_value", "match_key", "promotion_confidence", "promotion_reasons"],
              alias_promoted)
    write_csv(outdir / "aircraft_type_aliases_promoted_for_normalizer.csv",
              ALIAS_FIELDS,
              alias_final)
    write_csv(outdir / "aircraft_type_aliases_promotion_skipped.csv",
              ["raw_value", "match_key", "promotion_confidence", "promotion_reasons", "promotion_reason"],
              alias_skipped)

    report = {
        "lookup_existing": len(existing_lookup),
        "lookup_review_rows": len(lookup_review),
        "lookup_promoted": len(lookup_promoted),
        "lookup_skipped": len(lookup_skipped),
        "lookup_final": len(lookup_final),
        "aliases_existing": len(existing_aliases),
        "aliases_review_rows": len(aliases_review),
        "aliases_promoted": len(alias_promoted),
        "aliases_skipped": len(alias_skipped),
        "aliases_final": len(alias_final),
        "lookup_threshold": args.lookup_threshold,
        "alias_threshold": args.alias_threshold,
    }
    (outdir / "aircraft_promotion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
