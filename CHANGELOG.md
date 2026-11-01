# Changelog

- 2026-11-02 — ZCode (GLM) runtime: `install.sh --zcode` installs `.zcode/` — natively discovered skills, slash commands (same names as Claude Code) and GLM subagents (model/thoughtLevel from the shared policy), plus reflex/recovery hooks wired in `.zcode/config.json`. `.zcode/adapt-zcode.py` generates the full adapted copies from `.claude/` (`--check` guards drift in CI); policy tiers gained a `zcode` column (GLM-5.3 high/max, GLM-5.3-Flash low) and `workflow-route.py` accepts `--runtime zcode`.
- 2026-10-30 — Shared Claude/Codex resource routing for all workflow roles, bounded context, lightweight acceptance metrics and periodic local reporting. Installer now adds the policy to existing project rules and merges missing Codex defaults while preserving explicit settings.
