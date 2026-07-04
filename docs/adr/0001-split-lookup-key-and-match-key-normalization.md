# ADR-0001: Split lookup-key and match-key normalization into two functions

**Date:** 2026-07-04
**Status:** Accepted

## Context

While consolidating duplicated helpers into `scripts/taxonomy_constants.py`, two existing functions shared the name `norm_key` but did different things: `normalize_aircraft_v5.py` casefolds a raw Type/ICAO Type string to search the lookup table in memory; `auto_promote_aircraft_references.py` uppercases a value to produce or validate the canonical `match_key` field that gets written to the lookup/alias CSVs. Centralizing the name as one function would have silently picked one casing convention for both use cases.

## Decision

Keep them as two distinctly-named functions in `taxonomy_constants.py`: `norm_lookup_key()` (casefold, in-memory matching only, never written to disk) and `norm_match_key()` (upper, produces/validates the canonical `match_key` value). See `CONTEXT.md` for the domain definitions of **Lookup key** and **Match key**.

## Consequences

A future contributor who notices two similar-looking normalization functions should not merge them back into one — doing so would either break case-insensitive lookup matching or start writing lowercase match keys into the canonical CSVs, both silent correctness bugs rather than refactors.

## Alternatives Considered

Unifying on a single casing convention (either all-uppercase or all-casefolded) was rejected: lookup matching needs to be case-insensitive against arbitrary input, while the stored `match_key` format is contractually uppercase (enforced by `MATCHKEY_RE`) — these are different concepts that happen to take the same input shape, not one concept with two implementations.
