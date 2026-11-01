# ZCode workflow hooks

Two advisory hooks wired in `.zcode/config.json` (configuration-file hooks require
`hooks.enabled: true`):

- **PreToolUse** (`Bash|Write|Edit|MultiEdit|NotebookEdit|ApplyPatch`) → `workflow-hooks.py
  pre-tool-use`: normalizes the ZCode payload to the canonical Claude shape and calls the shared
  reflex engine `.claude/scripts/reflex-check.mjs` (never a copy). Reflexes live in
  `.claude/reflexes/`; each fires at most once per session; patch bodies are never interpreted
  as shell commands — only file paths are extracted.
- **SessionStart** (`startup|resume|clear|compact`) → `workflow-hooks.py session-start`: bounded
  recovery context (active `work/*/` features with planned/in_progress cards, checkpoint paths).
  ZCode has no PostCompact event; compaction recovery rides on `SessionStart(compact)`.

## Invariants

- Local processes only; no network, no model calls, no writes outside OS tmp (session-dedup
  state kept by the shared engine).
- Limits: 1 MiB input, 12000 chars of injected context, 3 s per engine call, 4 s total budget,
  8 s hook timeout (configured in `.zcode/config.json`).
- Fail-open: any error (malformed stdin, timeout, oversized payload) → diagnostic on stderr
  with the error **type** only (never the payload) and exit 0. The hook cannot block a session;
  these hooks grant no authorization for commits, delegation, external writes or deployment.
- Paths outside the repository and symlinks in `work/` are ignored; checkpoint contents are
  listed as paths, never injected.

## Activation

Configuration-file hooks run when `.zcode/config.json` has `hooks.enabled: true` — the installed
file already sets it. If you maintain your own `.zcode/config.json`, keep the key when merging
(you may need to reload the session for discovery to pick up changes).

## Testing

```bash
python3 -m unittest discover -s .zcode -p 'test_*.py'
```

## Diagnostics

- Nothing fires: check `hooks.enabled: true` in `.zcode/config.json` and that the session was
  started in this repository.
- A reflex fires once and not again: per-session dedup in the shared engine — by design.
- `zcode-workflow-hook: ...` in the ZCode log: see the message; `TimeoutExpired`/`payload limit`
  mean the engine call or input exceeded its budget, and the hook stayed fail-open.
