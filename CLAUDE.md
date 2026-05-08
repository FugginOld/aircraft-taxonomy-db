# Global AI Coding Workflow — Claude

<!-- Source: https://github.com/FugginOld/ai-config/blob/main/global/CLAUDE.md -->
<!-- Core rules: https://github.com/FugginOld/ai-config/tree/main/core/ -->

## Priority Order

1. Follow repository-local instructions first.
2. Use context-mode before consuming large raw context.
3. Follow CI AI workflow (core/workflow-gates.md).
4. Follow Matt Pocock-style workflow:
   - understand context
   - diagnose
   - create/confirm issue
   - implement with TDD
   - run local checks
   - summarize changes
5. Optimize for token efficiency.

---

## Context-Mode Requirements

Use context-mode tools for:

- repository scans
- grep/search output
- test output
- build output
- lint output
- dependency inspection
- large file summaries
- multi-file architecture review

Do not paste large raw outputs into chat unless explicitly required.

Prefer: summarized findings, file paths, line references, actionable failures, next commands.

For full context-mode routing rules, see: `core/context-mode-rules.md`

---

## Token Efficiency Rules

- Search before opening files.
- Open only relevant sections.
- Summarize long files instead of reading entire files.
- Prefer targeted commands over broad commands.
- Avoid repeating unchanged code.
- Avoid dumping logs.

Model selection:

- Sonnet — default for all routine tasks
- Opus — complex multi-file architecture or deep cross-system debugging only
- Haiku — mechanical tasks: renaming, formatting, lookups, repetitive operations

---

## TDD Loop

1. Reproduce or define expected behavior.
2. Write/adjust a failing test.
3. Implement minimal fix.
4. Run targeted test.
5. Refactor only after green tests.
6. Run final verification.

---

## Agent Routing

For escalation rules and agent context budgets, see: `core/agent-routing.md`

---

## Required Output Format

```text
Changed files:
Commands run:
Tests passing:
Known risks:
Next step:
```
