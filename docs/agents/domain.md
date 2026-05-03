# Domain Docs

How engineering skills should consume this repo's domain documentation.

## Layout

This repo is configured as **single-context**:

- Root `CONTEXT.md`
- Root `docs/adr/`

## Before exploring, read these

- `CONTEXT.md` at the repo root
- `docs/adr/` entries relevant to the area being changed

If a file is missing, proceed without failing and continue with best available context.

## Use glossary vocabulary

When naming domain concepts in issues, plans, tests, or refactors, use terminology defined in `CONTEXT.md`.

## Flag ADR conflicts

If a proposal or change conflicts with an ADR, call out the conflict explicitly instead of silently overriding it.
