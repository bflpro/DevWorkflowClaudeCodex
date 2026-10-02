---
name: infrastructure-setup
description: |
  Sets up dev infrastructure for new projects: framework init, folder structure,
  Docker, pre-commit hooks (gitleaks), testing infrastructure, .gitignore.

  Use when: "настрой инфраструктуру", "подготовь проект", "настрой тесты",
  "настрой проверки при коммите", "настрой проверки при пуше", "setup infrastructure"
---

# Infrastructure Setup

## Project Documentation Autosync

Project documentation source of truth is Claude-side: `CLAUDE.md` and `.claude/**`.
Codex-side `.agents/skills/**` and `.codex/agents/**` are generated entrypoints.

After changing any project-local `.claude/skills/**`, `.claude/commands/**` or `.claude/agents/**`
file, immediately run:

```bash
python3 .codex/sync-workflow.py --write
```

If sync reports a conflict, stop and report it. Include the generated Codex entrypoints and the
manifest in the same commit as the `.claude/**` source change (details: `.codex/README.md`).

## Gathering Project Context

Read project-knowledge references:
- `.claude/skills/project-knowledge/references/architecture.md` — tech stack, framework
- `.claude/skills/project-knowledge/references/patterns.md` — code conventions, branching strategy, testing
- `.claude/skills/project-knowledge/references/deployment.md` — deployment strategy

If files lack needed info, search other project-knowledge references — info may exist under different names. If missing entirely, ask the user and immediately update the relevant doc.

**Autonomous decisions** (based on project-knowledge):
- Framework init commands, folder structure, test framework, .gitignore patterns

**Ask user:**
- Docker: needed? Local dev, production, or both?
- Pre-commit strictness: gitleaks only, or add lint/format?

## Phase 1: Framework Initialization

Init framework from `architecture.md`. Use Context7 for up-to-date init commands and flags. Verify it starts.

**Checkpoint:** dev server starts successfully.

## Phase 2: Folder Structure

Convention — separate concerns by purpose:

- **Web Apps:** `src/{components, services, lib, config}` + `tests/{unit, integration, e2e}`
- **APIs:** `src/{routes, services, models, middleware, config}` + `tests/{unit, integration}`
- **CLI tools:** `src/{commands, services, config}` + `tests/{unit, integration}`

Add `src/prompts/` if project uses LLM prompts. Add `src/messages/` if project uses i18n.

**Checkpoint:** structure created, matches project type.

## Phase 3: Docker (conditional)

Set up only if specified in project-knowledge or user confirms.

**Checkpoint:** `docker build` succeeds, container starts.

## Phase 4: .gitignore

Security patterns (always add):
```
.env
.env.*
!.env.example
*.key
*.pem
credentials.json
secrets/
```

Add framework-specific patterns from `architecture.md`.
Create `.env.example` with required variable names (no values).

**Checkpoint:** `git check-ignore .env` returns `.env`.

## Phase 5: Pre-commit Hooks

Convention: gitleaks for secret scanning. Target: total pre-commit time under 10 seconds.

Pre-commit scope (fast, staged files only):
- gitleaks (~2-5 seconds)
- Lint staged files
- Format check

Full test suites, integration tests, builds belong in CI.

**Checkpoint:** commit a file containing `AKIA1234567890EXAMPLE` — gitleaks blocks it.

## Phase 6: Testing Infrastructure

Set up test framework, create smoke test: 1-2 tests verifying setup works (import main module, check environment).

A runner reports on the tests it **collected**, not on the tests that **exist** — so "the test
command passes" is compatible with the runner having found nothing at all, or having silently
skipped a file that sits outside its discovery pattern. Any check written as a standalone script,
or named against the runner's convention, is invisible forever and its failure never surfaces.
Fix that here, while the conventions are being set: record the discovery pattern in `patterns.md`
and make the runner's collected count part of the checkpoint.

**Checkpoint:** test command passes **and** the run reports a non-zero collected count that matches
the test files on disk (`pytest --collect-only -q | wc -l` vs `find tests -name 'test_*.py' | wc -l`,
or the equivalent for the chosen runner). A green run that collected 0 tests is a failed checkpoint.

## Phase 7: Documentation & Commit

Update project-knowledge references (append, don't overwrite):
- `deployment.md` — required environment variables
- `patterns.md` (Git Workflow section) — pre-commit hooks and what they check

Commit:
```
chore: setup project infrastructure

- Initialize [framework] project
- Setup pre-commit hooks (gitleaks)
- Create folder structure
- Add testing infrastructure
- Configure .gitignore and .env.example
[- Setup Docker (if applicable)]
```

Verify before commit: `git status` shows no `.env` files (only `.env.example`).

## Final Validation

- [ ] Framework runs locally
- [ ] Folder structure matches convention
- [ ] gitleaks blocks test secret
- [ ] `.gitignore` covers `.env`, `*.key`, secrets
- [ ] `.env.example` exists (if project uses env vars)
- [ ] Smoke test passes, and the runner reports it as collected (not a green run over zero tests)
- [ ] Documentation updated
- [ ] All infrastructure committed
- [ ] Docker works (if applicable)
