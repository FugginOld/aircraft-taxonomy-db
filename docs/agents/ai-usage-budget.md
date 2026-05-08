# Agent Routing & Usage Budget

## Agent Role Assignments

| Agent | Role | Use For | Avoid |
|-------|------|---------|-------|
| Claude Pro | Scarce reasoning | Architecture, planning, review | Long coding loops |
| ChatGPT Plus / Codex | Implementation | Tests, code, debugging, scripts | Repeated broad planning |
| GitHub Copilot Pro | Local assist | Autocomplete, small edits, boilerplate | Full repo analysis, architecture |

---

## Claude — Context Rules

Send only:
- `AGENTS.md`
- `CONTEXT.md`
- Issue text
- Changed file list
- Selected affected files (when needed)
- Test output
- `git diff`

Do NOT send:
- Entire repo dumps
- Generated files (unless directly relevant)
- Repeated full context after every change
- Long terminal logs without trimming

### Session-Saving Prompt

```text
Use AGENTS.md and CONTEXT.md.
Use /caveman lite.
Do not re-read the whole repo.
Issue: #__
Branch: agent/__
Changed files:
- __
Tests run:
- __
Task:
Review only this diff for correctness, missing tests, architecture conflicts, and merge risk.
```

---

## Codex / ChatGPT — Usage Rules

Use for:
- Implementation
- Test writing
- Repeated test/fix loops
- Scripts and mechanical cleanup
- Local verification

Always summarize on completion:
```text
Changed files:
Commands run:
Tests passing:
Known risks:
Next recommended step:
```

### Session-Saving Prompt

```text
Use AGENTS.md and CONTEXT.md.
Use /caveman full.
Work only on issue #__.
Do not redesign unrelated code.
Write or update tests first when practical.
Run available checks.
Return changed files, commands run, and remaining risks.
```

---

## Copilot — Usage Rules

Use for:
- Inline suggestions
- Boilerplate
- Simple completion
- Repetitive edits

Avoid for:
- Architecture decisions
- Full repo review
- Large context analysis
- PRD or issue creation

---

## Escalation Rules

### Escalate Codex → Claude ONLY when:
- Architecture is unclear
- Tests conflict with expected behavior
- Requirements are ambiguous
- Change affects multiple subsystems
- An ADR may be needed

### Do NOT escalate for:
- Syntax errors
- Normal test failures
- Formatting
- Import fixes
- Boilerplate
