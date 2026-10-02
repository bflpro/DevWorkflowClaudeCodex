# Reflexes — lessons that fire at the moment of action

A reflex is a one-fact note that gets injected into the agent's context **right before
the matching tool call** (via the PreToolUse hook → `.claude/scripts/reflex-check.mjs`).
Unlike memory files read once at session start, a reflex cannot be forgotten by turn 40 —
it arrives between the agent's intent and the action.

## Note format

```markdown
---
use-when:
  - bash:/pm2 (restart|reload)/i
  - edit:src/db/schema/**
---
One to three lines: the lesson, why it burned us, what to do instead.
```

Trigger syntax:

- `bash:/regex/flags` — matches the Bash command text
- `edit:glob` — matches the file path of Edit/Write/MultiEdit/NotebookEdit
  (project-relative; `**` crosses directories, `*` does not)

Multiple triggers per note are OR-ed.

## Rules

- **Keep the body ≤3 lines.** A reflex is a warning shot, not documentation — link to
  `ENGINEERING.md` or the project README for details.
- **Few and sharp beats many and broad.** A trigger that fires on every other call is
  noise and will be ignored. Scope it to the exact burn.
- Each reflex fires **once per session** (deduped via a temp state file).
- The hook is **fail-open**: if the script errors, work continues without the warning.
- A reflex earns its place through a real burn. Don't add speculative ones —
  that's what regular memory is for.

## Testing a new reflex

```bash
echo '{"tool_name":"Bash","session_id":"test-'$RANDOM'","tool_input":{"command":"pm2 restart my-agent"}}' \
  | node .claude/scripts/reflex-check.mjs
```

Expect a JSON with `additionalContext` containing your reflex; empty output = no match.
