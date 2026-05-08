# Global AI Workflow — Core Rules

## Workflow Priority

1. Repository-local instructions override global instructions.
2. context-mode routing rules are mandatory.
3. Use token-efficient workflows.
4. Follow CI AI workflow discipline (see `workflow-gates.md`).
5. Prefer Matt Pocock-style issue/TDD workflow.

---

## Required Development Workflow

For non-trivial changes:

1. Inspect repository instructions.
2. Diagnose before implementing.
3. Search before opening files.
4. Use context-mode tools for scans, diagnostics, grep, test output, architecture review.
5. Break large work into smaller scoped tasks/issues.
6. Prefer TDD: reproduce → failing test → minimal fix → verify.
7. Run targeted checks first.
8. Run broader validation if shared behavior changes.
9. Summarize: changed files, tests run, remaining risks, next recommended actions.

---

## Token Efficiency Rules

Avoid:
- full logs
- large pasted outputs
- unnecessary file reads
- repeated context
- broad recursive scans without filtering

Prefer:
- summaries
- targeted reads
- concise diffs
- line references
- actionable findings

---

## File Reading Rules

Before opening large files:
1. Search/index first
2. Identify relevant sections
3. Read only necessary portions
4. Summarize before expanding context further

---

## Architecture Workflow

For unfamiliar repos:
1. Identify entrypoints
2. Identify build/test system
3. Identify dependency structure
4. Identify CI/CD flow
5. Identify shared libraries/modules
6. Identify existing patterns before creating new ones

---

## TDD Loop

1. Reproduce or define expected behavior.
2. Write/adjust a failing test.
3. Implement minimal fix.
4. Run targeted test.
5. Refactor only after green tests.
6. Run final verification.

---

## Required Output Format

```text
Changed files:
Commands run:
Tests passing:
Known risks:
Next step:
```

---

## Handoff Rule

When switching agents, use: `docs/agents/agent-handoff-template.md`

Rules:
- Do not restart work
- Do not expand scope
- Continue from current branch
