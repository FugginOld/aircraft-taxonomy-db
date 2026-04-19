# Weekly aircraft update architecture v3

This version adds auto-promotion and confidence scoring.

## Files
- `sync_public_aircraft_sources.py`
- `expand_aircraft_aliases_v2.py`
- `validate_aircraft_references.py`
- `auto_promote_aircraft_references.py`
- `weekly_update_pipeline_v3.py`
- `normalize_aircraft_v5.py`

## Flow
1. Refresh cached public sources into `cache/public_sources/`
2. Expand aliases from the seed alias list
3. Validate aliases and lookup rows against local public metadata CSV/TSV files
4. Auto-promote review rows that meet confidence thresholds
5. Publish:
   - `aircraft_type_aliases.csv`
   - `aircraft_type_lookup.csv`
6. If either published file changed, rerun normalization over every `plane_alert_*.csv`

## Confidence defaults
- Lookup promotion threshold: `0.70`
- Alias promotion threshold: `0.75`

## Promotion outputs
- `aircraft_type_lookup_promoted.csv`
- `aircraft_type_lookup_promoted_candidates.csv`
- `aircraft_type_lookup_promotion_skipped.csv`
- `aircraft_type_aliases_promoted.csv`
- `aircraft_type_aliases_promoted_for_normalizer.csv`
- `aircraft_type_aliases_promotion_skipped.csv`
- `aircraft_promotion_report.json`

## Recommended weekly run

```bash
python3 sync_public_aircraft_sources.py --cache-dir cache/public_sources
python3 weekly_update_pipeline_v3.py \
  --workspace . \
  --normalizer normalize_aircraft_v5.py \
  --alias-expander expand_aircraft_aliases_v2.py \
  --validator validate_aircraft_references.py \
  --promoter auto_promote_aircraft_references.py \
  --seed-aliases aircraft_aliases.csv \
  --seed-lookup aircraft_lookup_seed.csv \
  --no-audit-cols
```

## Cron example

```cron
0 4 * * 0 cd /path/to/workspace && /usr/bin/python3 sync_public_aircraft_sources.py --cache-dir cache/public_sources >> logs/aircraft_sync.log 2>&1
30 4 * * 0 cd /path/to/workspace && /usr/bin/python3 weekly_update_pipeline_v3.py --workspace . --normalizer normalize_aircraft_v5.py --alias-expander expand_aircraft_aliases_v2.py --validator validate_aircraft_references.py --promoter auto_promote_aircraft_references.py --seed-aliases aircraft_aliases.csv --seed-lookup aircraft_lookup_seed.csv --no-audit-cols >> logs/aircraft_weekly.log 2>&1
```
