# Skills and Reviewers Catalog

Single source of truth for selecting skills and reviewers in Implementation Tasks.
Used by: tech-spec-planning (Phase 4), task-decomposition (Phase 1).

## Execution Skills

| Skill | What it's for | Typical tasks |
|-------|--------------|---------------|
| `code-writing` | Writing/modifying code, TDD cycle | API endpoints, models, services, components, migrations, tests |
| `infrastructure-setup` | Framework init, folder structure, Docker, pre-commit hooks, testing setup | Dockerfile, pre-commit hooks, folder structure, .gitignore, smoke tests |
| `deploy-pipeline` | CI/CD pipelines, deployment config, automated deploy | GitHub Actions, deploy scripts, platform config, secrets management |
| `documentation-writing` | Documentation, Project Knowledge updates | Architecture docs, API docs, conventions, patterns |
| `skill-master` | Creating/updating skills and agents | New skills, skill modifications |
| `pre-deploy-qa` | Acceptance testing before deploy (tests + acceptance criteria) | QA task in Final Wave |
| `post-deploy-qa` | Live environment verification after deploy via MCP tools | Post-deploy task in Final Wave |
| `prompt-master` | Writing/improving LLM prompts, prompt engineering | System prompts, user prompt templates, few-shot examples, prompt optimization |

| `code-reviewing` | Full-feature code quality audit | Code Audit in Audit Wave |
| `security-auditor` | Full-feature security audit | Security Audit in Audit Wave |
| `test-master` | Full-feature test quality audit | Test Audit in Audit Wave |

Tasks without skill (user instructions) — skill not specified, description is in the task itself. Example: "ask user to register a bot in BotFather".

Prompt tasks (LLM system prompts, user templates) use `prompt-master` skill — they are NOT code-writing tasks. TDD Anchor is replaced by manual verification on sample data.

## Review Lenses (since 2026-09-30)

Review is run by the lead through **lenses** — context-free subagents that read the diff by path
and grade nothing; the lead verifies and grades every finding (`.claude/shared/review-lenses/`).
The `reviewers` field of a task names a **set**, not people:

| Value | Meaning |
|-------|---------|
| `[quick]` | one `quick` lens; `security` added by the lead only when the diff touches auth / input / secrets |
| `[thorough]` | `blind-hunter`, `edge-case-hunter`, `verification-gap`, `intent-alignment`, `security`, `prod-readiness` (L1+ only) |
| `[none]` | self-verifying task (QA, deploy, audit) — no lenses |
| `[]` | default = `[thorough]` |
| role list (`code-reviewer`, …) | legacy cards only; the lead runs `thorough`. Not written on new cards |

Role agents still exist for non-code work and run as a lens with their own methodology:
`prompt-reviewer` (prompts), `skill-checker` (skills), `deploy-reviewer`, `infrastructure-reviewer`,
`documentation-reviewer`. Name them explicitly: `reviewers: [prompt-reviewer]`.

## Skill → Reviewers Mapping

| Skill | Default reviewers |
|-------|------------------|
| `code-writing` | `[thorough]`; `[quick]` when `executor: codex` (size S: ≤100 lines, ≤5 files, no external write) |
| `infrastructure-setup` | `[thorough]` + `infrastructure-reviewer` |
| `deploy-pipeline` | `[thorough]` + `deploy-reviewer` |
| `documentation-writing` | `[quick]` |
| `skill-master` | `[skill-checker]` |
| `pre-deploy-qa` | `[none]` — QA is its own verification |
| `post-deploy-qa` | `[none]` — verification result is the review |
| `prompt-master` | `[prompt-reviewer]` |
| `code-reviewing` | `[none]` — auditor IS the review (Audit Wave) |
| `security-auditor` | `[none]` — auditor IS the review (Audit Wave) |
| `test-master` | `[none]` — auditor IS the review (Audit Wave) |

When `reviewers` is `[]` in a task — the lead treats it as `[thorough]`.

## Executor Assignment

Assign `executor` in task frontmatter to route work to the right model/agent and conserve Claude Opus quota.

### Provider-aware resources (2026-10-30)

Read `.claude/shared/workflow-resources/README.md`; `policy.json` is authoritative for
model/effort by role, including research, specifications, cards, validators and lenses.
Legacy executor names below are capability hints, not an instruction to switch provider
or force an inherited model. Resolve the current runtime, role and risk before launch.
Routine tasks use GLM-5.3/high in ZCode; critical risks use GLM-5.3/max in ZCode. Existing
stronger explicit assignments remain valid. Inline stages use the actual parent model.

### Executors

| Executor | Resources | Best for |
|----------|-----------|----------|
| `glm-max` | GLM-5.3 / thoughtLevel max | Complex reasoning: prompt-master, architecture design, L-size tasks with non-obvious decisions |
| `glm-high` | GLM-5.3 / high (default) | Standard work: code-writing S/M/L, reviews, QA, documentation, infrastructure-setup, deploy-pipeline, mechanical and large-scale refactoring |
| `glm-flash` | GLM-5.3-Flash / low | Extraction/summarization only — never semantic approval, review, security or acceptance |

### Assignment rules

**Use `glm-max` when:**
- skill = `prompt-master`
- Task requires architectural decisions with multiple trade-offs (L-size + design-heavy)
- No clear single right answer — task needs deep reasoning

**Use `glm-high` (default) when:**
- Any code-writing size, review, QA, documentation, infrastructure or deploy task
- Mechanical changes (add field, rename, boilerplate) and large-scale refactoring/migrations
- Anything not covered by the glm-max rules

**Use `glm-flash` only for extraction** — fetching facts, counting, summarizing existing
material. It never approves, reviews or closes findings.

### Skill → Executor default

| Skill | Default executor |
|-------|-----------------|
| `prompt-master` | `glm-max` |
| `code-writing` (S/M/L) | `glm-high` |
| `code-reviewing` | `glm-high` |
| `security-auditor` | `glm-max` (critical tier) |
| `test-master` | `glm-high` |
| `infrastructure-setup` | `glm-high` |
| `deploy-pipeline` | `glm-high` |
| `documentation-writing` | `glm-high` |
| `skill-master` | `glm-high` |
| `pre-deploy-qa` | `glm-max` (critical tier) |
| `post-deploy-qa` | `glm-max` (critical tier) |
| large-scale refactoring / 10+ files | `glm-high` |

## Examples

### Code task (most common)
```yaml
skills: [code-writing]
reviewers: [thorough]        # [quick] for executor: codex
```

### Infrastructure setup task
```yaml
skills: [infrastructure-setup]
reviewers: [thorough, infrastructure-reviewer]
```

### Deploy pipeline task
```yaml
skills: [deploy-pipeline]
reviewers: [thorough, deploy-reviewer]
```

### Task handling user input or auth
```yaml
skills: [code-writing]
reviewers: [thorough]
```
The `security` lens is part of `thorough`; for `[quick]` the lead adds it when the diff touches auth or input.

### Documentation task
```yaml
skills: [documentation-writing]
reviewers: [quick]
```

### Audit task (Audit Wave)
```yaml
skills: [code-reviewing]  # or security-auditor, test-master
reviewers: []
```

### QA task (Final Wave)
```yaml
skills: [pre-deploy-qa]
reviewers: []
```

### Post-deploy verification (Final Wave)
```yaml
skills: [post-deploy-qa]
reviewers: []
```

### Prompt task
```yaml
skills: [prompt-master]
reviewers: [prompt-reviewer]
```
