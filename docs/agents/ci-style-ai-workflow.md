# CI-Style AI Workflow

## Purpose

Enforces a **repeatable, low-token, high-quality AI development process**.

Ensures:
- predictable changes
- strict scope control
- proper agent usage
- minimal token waste
- safe, test-driven delivery

---

## Workflow Overview (Mandatory Order)

```text
Context -> Plan -> Issue -> Branch -> Test -> Change
-> Diagnose -> Review -> PR -> Merge
```

Agents MUST NOT skip steps.

---

## Gate 0 — Repo Setup (Run Once)

Command:
```text
/setup-matt-pocock-skills
```

Verify files exist:
```text
AGENTS.md
CONTEXT.md
docs/agents/ci-style-ai-workflow.md
docs/agents/ai-usage-budget.md
docs/agents/agent-handoff-template.md
docs/adr/
.github templates
```

Pass condition: Repo is AI-ready. Workflow + rules enforced.

---

## Gate 1 — Context (Claude)

Commands:
```text
/caveman lite
/grill-with-docs
/zoom-out
```

Prompt:
```text
Use AGENTS.md and CONTEXT.md.

Identify:
- affected files
- domain terminology
- related architecture decisions
- smallest safe change

Do NOT propose implementation yet.
```

Pass condition: Scope clearly defined. No unknown domain terms. No architecture conflicts ignored.

---

## Gate 2 — Plan → Issue (Claude)

Commands:
```text
/to-prd
/to-issues
```

Prompt:
```text
Break this work into the smallest independent issue.

Include:
- problem
- acceptance criteria
- files likely touched
- tests required
- risks
- rollback plan

Do NOT combine multiple concerns.
```

Pass condition: Issue is independently completable. Fits in one branch. Has clear acceptance criteria.

---

## Gate 3 — Branch (Human or Codex)

```bash
git checkout -b agent/<issue-number>-short-name
```

Rules: One branch per issue. Clean working tree required.

---

## Gate 4 — TDD Loop (Codex / ChatGPT)

Commands:
```text
/caveman full
/tdd
```

Prompt:
```text
Use AGENTS.md and CONTEXT.md.

Work only on this issue.

Loop:
1. Write or identify failing test
2. Run test and confirm failure
3. Implement smallest possible fix
4. Run test and confirm pass
5. Refactor only if tests stay green

Do NOT:
- modify unrelated files
- redesign architecture
- skip tests unless justified
```

Pass condition: Tests exist or justification provided. Smallest change implemented. No scope creep.

---

## Gate 5 — Diagnose (Codex → Claude if needed)

Command:
```text
/diagnose
```

Prompt:
```text
Validate this change.

Check:
- expected behavior
- edge cases
- regressions
- assumptions

List any risks or gaps.
```

Pass condition: No unresolved blockers. Critical paths tested. Risks identified.

---

## Gate 6 — Architecture Check (Claude, if needed)

Command:
```text
/improve-codebase-architecture
```

Prompt:
```text
Evaluate ONLY if needed.

Did this change:
- preserve behavior?
- avoid duplication?
- align with CONTEXT.md?
- introduce unnecessary abstraction?

Reject overengineering.
```

Pass condition: No unnecessary abstraction. No duplication introduced. No ADR conflicts.

---

## Gate 7 — Local CI (Codex / Human)

```bash
git status
npm test
npm run lint
pytest
ruff check .
mypy .
```

Pass condition: All checks pass. Failures fixed or documented.

---

## Gate 8 — Final Review (Claude)

Commands:
```text
/caveman lite
/diagnose
```

Prompt:
```text
Use AGENTS.md.

Review ONLY this diff.

Block for:
- correctness issues
- missing tests
- risky assumptions
- unnecessary complexity
- architecture conflicts

Do NOT review entire repo.
```

Pass condition: Issues resolved. Risks documented.

---

## Gate 9 — Pull Request

```bash
gh pr create --fill
```

PR must include: linked issue, summary, tests run, risks, rollback plan.

---

## Gate 10 — Merge

```bash
git status
git pull --rebase
```

Merge only if: acceptance criteria met, tests pass, review complete, no unresolved comments.

---

## Agent Role Summary

| Agent | Gates |
|-------|-------|
| Claude | 1, 2, 6, 8 (planning, architecture, review) |
| Codex / ChatGPT | 4, 5, 7 (implementation, testing, debugging) |
| Copilot | Inline assistance only |

For escalation rules, see: `core/agent-routing.md`

---

## Core Principles

- Small changes win
- Tests validate behavior
- Scope must stay tight
- Tokens are limited → use them intentionally
- Workflow discipline > speed
