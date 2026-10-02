# Codex workflow hooks

These local hooks adapt Codex to the existing Claude reflex engine and restore the workflow index after session startup/resume/compaction. They do not send data to a model or external API themselves.

## Data flow

```text
PreToolUse JSON → Bash command or apply_patch path normalization
                 → .claude/scripts/reflex-check.mjs (timeout)
                 → hookSpecificOutput.additionalContext

SessionStart JSON → shared instruction paths + active task/checkpoint paths
                 → SessionStart additionalContext for the next model request
```

## Why this implementation

The existing reflex engine is reused without modifying Claude's behavior. Codex patch tools name several files in `tool_input.command`; each changed/moved path is normalized from the working directory. Patch contents are never interpreted as Bash commands. Session ids are hashed before reaching the engine's state filename.

Plain stdout from PostCompact is ignored by current Codex. Recovery therefore uses SessionStart with `compact`, as well as startup/resume/clear. The compatibility shell script delegates to the new adapter; configure it only as SessionStart, not PostCompact.

Recovery emits paths to unfinished task cards, not checkpoint contents or team claims. Multiple features remain explicit candidates; the session's intent determines which one to resume.

## External access and invariants

- Only local Python/Node/Git processes and repository files are used. No token/account/scope is needed.
- The canonical engine stores only fired reflex filenames in the operating system temporary directory. It is best-effort session deduplication, not a correctness gate.
- Incoming hook JSON is limited to 1 MiB; model-visible output to 12,000 characters. Individual engine calls have a 3-second timeout and the whole reflex loop a 4-second budget; runtime hook timeout is 8 seconds.
- Recovery skips completed folders, symbolic feature folders, completed cards and cards larger than 64 KiB; output is capped at 12 active features and five pending card paths per feature.
- Failures return exit 0 so an advisory hook cannot wedge the session, but emit the failure type on stderr without commands, tokens, checkpoint contents or other payload values.
- Hooks do not authorize commits, delegation, external writes or deployment. Receipt and Prod Gate checks remain explicit.

## Run, test and activation

From the repository root:

```bash
python3 -m unittest discover -s .codex -p test_workflow_hooks.py -v
bash -n .codex/hooks/post-compact-restore.sh
```

Tests use temporary repositories and the actual canonical reflex engine. The lifecycle test creates a synthetic Git baseline only in its temporary directory, creates project templates, runs wave-check, and asserts an accepted task receipt with observed verification output. It does not commit in the host repository or call a model.

`.codex/hooks.json` is loaded from the project's active trusted configuration layer. Review and trust the two definitions through Codex `/hooks`; restarting the app/session may be needed after configuration changes. The hooks feature must be enabled. Runtime discovery/trust evidence belongs in `work/codex-workflow-sync/validation.md`; protocol tests alone do not prove live execution.

On the installation machine, the two reviewed hashes were trusted through the same `config/batchWrite` operation used by the Codex hooks UI. Only their entries under user `hooks.state` changed; other user settings were compared and preserved. This machine-specific trust is outside git. Another computer must review/trust its own hook definitions.

## Диагностика: как понять, что сломалось

- `codex-workflow-hook: TimeoutExpired`: the reflex engine exceeded its time budget; run required checks explicitly.
- `payload limit exceeded` / JSON errors: a malformed or unsupported input was rejected; payload contents are deliberately absent from the diagnostic.
- No model-visible reflex despite a matching fresh-session command: inspect `/hooks` for source, enabled/trusted state, matcher and runtime failure.
- Recovery lists several features: consult the current user request and checkpoint/task data rather than choosing the first.

## Sources

Runtime schema follows [official Codex hooks docs](https://learn.chatgpt.com/docs/hooks). Reused the local `.claude/scripts/reflex-check.mjs` implementation and notes; no external script or dependency was imported. The inspected upstream commits and license limitations are recorded in `.codex/README.md` and the feature research notes.
