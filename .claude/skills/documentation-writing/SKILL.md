---
name: documentation-writing
description: |
  Maintain project documentation in .claude/skills/project-knowledge/: audit, edit, check consistency, track status.

  Use when: "проверь документацию", "обнови документацию", "аудит документации",
  "check docs", "audit documentation", "update docs", "проверь базу знаний проекта"

  For creating documentation from scratch use project-planning skill.
  For reading docs or explaining concepts, read project-knowledge skill directly.
---

# Documentation Management

Maintain project documentation in `.claude/skills/project-knowledge/references/`. Audit for bloat, edit files, check consistency, track status.

For creating documentation from scratch (new project or empty docs), use `project-planning` skill.

## Documentation Principles

These rules apply to ALL documentation operations (audit, edit, create).

**Goal: open docs → understand the project without reading code.** What is this project, how it's structured, what it does, where to find key things, how to deploy, where are logs. A high-level navigation guide.

**Describe what exists, what it does, and why.** High-level overview of components, how they work together, decisions made (why this stack, why this architecture), operational details (server addresses, deploy procedures, log locations, env var names). Skip what's obvious from reading the code itself — function signatures, implementation details, generic framework behavior.

**No code blocks, no pseudocode.** Link to source files: `[auth.ts:45-67](src/auth/jwt.ts#L45-L67)`. Code in docs gets outdated and bloats context.

**No duplication between files.** Information lives in ONE place. Cross-reference: "See deployment.md for env vars."

**Every claim that can go stale carries the event that refreshes it.** Three shapes recur, and all
three are invisible at write time because the document stays internally consistent and well written
while becoming wrong:

- *A dated current-state block* ("as of <date> — read this first") acquires the document's authority
  and the changelog's decay rate, on two independent clocks. It may exist only alongside (a) a named
  refresh event — the concrete, tool-visible act that obliges an author to update it — and (b) a
  pointer to the faster-moving artefact it summarises (the work log, the changelog), so a reader can
  check the summary against the ledger in one step. Without both, write no status block: a document
  that admits it does not track state is safer than one that tracks it wrongly while telling the
  reader to trust it.
- *A scope limiter* (pilot allowlist, canary cohort, feature flag, "only for these N records") is
  described by the **layer at which it is applied** — not selected at all / not planned / not
  executed / not sent — never only by its observable effect. Two filters at different layers look
  identical from outside for as long as they hold, and diverge precisely at the moment they are
  lifted: a filter at the intake layer accumulates deferred work, a filter at the output layer does
  not. The check is cheap and mandatory: grep the variable's name and see which module reads it.
- *A negation in the introduction* ("does not send anything", "read-only", "no executors exist yet",
  "still manual") ages exactly when the system is extended — that is, while someone is editing a
  different part of the same document, so nobody thinks to re-read the intro. State such a claim only
  together with the condition under which it stops being true and the section that will cancel it, or
  leave the introduction describing purpose rather than current limits. Treat every negation in an
  intro as dated even when it carries no date; when a document gains a section about a new phase or
  capability, re-reading its introduction is part of that edit. Mechanical check: grep the intro for
  negations ("not", "no", "only", «не», «нет», «только») and reconcile each against what was added.

**patterns.md: only project-specific patterns.** Universal coding standards live in `.claude/skills/code-writing/references/universal-patterns.md` (fallback: `~/.claude/skills/code-writing/references/universal-patterns.md`). Project patterns.md contains only what's unique to THIS project.

## File Structure

**4 core files** in `.claude/skills/project-knowledge/references/`:

| File | Contains |
|------|----------|
| project.md | Overview, audience, problem, 3-5 key features, out of scope |
| architecture.md | Tech stack (with WHY), project structure, dependencies, integrations, data model |
| patterns.md | Project-specific code patterns, git workflow, testing methods, business rules |
| deployment.md | Platform, env var names, CI/CD triggers, rollback, monitoring |

**Optional:**
- **ux-guidelines.md** — only for projects with significant UI
- **{custom}.md** — domain-specific (bot.md, vault.md, api.md)

Templates with placeholder structure are in `.claude/shared/templates/new-project/.claude/skills/project-knowledge/references/ (fallback: ~/.claude/shared/templates/new-project/.claude/skills/project-knowledge/references/)`. The templates are self-documenting — each section has comments explaining what to write.

## Workflows

### 1. Audit

**Trigger:** User asks to audit, check quality, or find bloat.

1. Read all files from `.claude/skills/project-knowledge/references/` + CLAUDE.md + README.md
2. Flag issues:
   - Code blocks → replace with file references
   - Generic framework knowledge (belongs in official docs) → remove
   - Function-level details → suggest moving to code comments
   - Bloated sections (>3-5KB per file is suspicious) → condense
   - Duplication across files → consolidate to one place
   - Placeholder text (`[Project Name]`, `TODO`) → fill or remove
   - Inconsistent terminology → standardize
   - Outdated info (files/functions that no longer exist) → update or remove
   - Universal patterns in patterns.md → flag for removal (those belong in code-writing skill)
3. Preserve operational details: server addresses, SSH configs, deploy commands, log paths, env var names, monitoring URLs. These belong in docs even if they seem "obvious" — they can't be read from code.
4. Create audit report with issues by file
5. Ask user which to fix → apply approved changes → verify consistency

### 2. Edit

**Trigger:** User asks to edit or update specific documentation.

1. Identify target file/section (ask if unclear)
2. Read current content
3. Apply changes following documentation principles
4. **Re-derive every fact from the primary source before it lands in the file.** Every number,
   identifier, path, port, version and count that will appear in the document is checked once against
   the code or the live system — not against the summary that reported it, and not against another
   document. This applies hardest when the material came from delegated research: subagent reports
   arrive in the register of established fact, and a document assembled straight from them inherits
   every error invisibly. Prefer claims anchored with `file:line` (cheap to re-check) and treat
   unanchored ones as unverified. Where two documents in the repo disagree about a fact, the document
   being written says which one wins and why, rather than silently picking one — a stale handover doc
   left unmarked keeps costing every reader the same hour. Delegation moves the reading, not the
   responsibility for the claim; after publication a wrong fact and a right one are typographically
   identical.
5. **A structural edit obliges a reference re-resolution pass.** Whenever a numbered heading is
   inserted, removed or reordered, grep the whole document for by-number references (`section N`,
   `раздел N`, `п. N`, `см. N`) and re-resolve each against the new numbering, then grep the sibling
   documents of the same package for references to the edited document's section numbers. Renumbering
   leaves every positional reference syntactically valid and textually unchanged, so the defect it
   creates is invisible to every check that reads the document instead of resolving its references —
   including a verification that lists the new headings. Preventively: when authoring a
   cross-reference, name the section rather than number it; a name survives renumbering, a number does
   not.
6. **A term with a non-obvious definition has exactly one owning document and section**, named in the
   package index; every other document refers to it by name plus that pointer and does not restate the
   definition. Where restating is unavoidable for readability, mark the restatement as derived and
   carry the pointer, so a later revision can enumerate the copies instead of hoping the wording
   stayed similar enough to grep. Before editing a definition, grep the package for the term, enumerate
   the sites, and report the count with the edit. A definition copied into each of its consumers is not
   documentation of a concept but N independent assertions about it, agreeing by coincidence and only
   until the first revision.
7. Check if changes affect other files (e.g., tech stack mentioned elsewhere) → update related files

### 3. Check Consistency

**Trigger:** User asks to verify terminology or check for mismatches.

1. Read all project-knowledge files
2. Extract: tech stack names/versions, service names, DB names, env var names, platform names
3. Find inconsistencies (e.g., "PostgreSQL" vs "Postgres" vs "postgres")
4. Report → ask user for correct terminology → standardize across all files

### 4. Show Status

**Trigger:** User asks about documentation completeness.

1. Check each file: exists? filled or template? size? last modified?
2. Classify: filled / partially filled / template / missing
3. Show status report with recommendations

## Root Project Files

**Scope of this section:** the rules below assume a repo organised around **one** project-knowledge
store, with thin entry points pointing into it. Check that assumption before applying them.

**Counter-case — monorepo / multi-deliverable repo.** When a repo hosts several independently
deployed units (services, agents, packages), each in its own folder, with no shared
`project-knowledge/`, the **per-unit README is itself the durable documentation surface** and must
carry full depth: what it does, the step-by-step flow, why it is built this way, what it touches
externally, its invariants, how to run/test/deploy it, and how to tell it broke — the same content
this skill would otherwise push into `architecture.md`, `patterns.md` and friends. A thin README
that "points to project-knowledge" which does not exist is not a build error, not a missing file and
not a test failure: it looks exactly like finished conventional work.

**A repo with this workflow installed is usually such a repo.** Its per-unit README standard
(required sections, access coordinates, the inverse pass, the ~800-line split) lives in the
project's root instructions (`CLAUDE.md` / `ENGINEERING.md`), and is checked by
`python3 .claude/scripts/check-readme.py --changed`.
Code blocks with run/deploy/rollback commands are required there, not banned. Prose style and
truth rules for any document come from the `technical-writing` skill and its document-type
siblings; this skill keeps the `project-knowledge` store.

**Detection step, first in any README-authoring workflow:** read the repo's own root CLAUDE.md (or
equivalent) and check whether it states a stronger or more specific README requirement than this
skill's default. A repo-level convention always overrides the skill default — it does not coexist
with it unreconciled.

CLAUDE.md and README.md are entry points, not documentation. Keep them minimal — they point to project-knowledge, not contain information.

**CLAUDE.md** (for AI agents): project name, one-line description, reference to project-knowledge skill, backlog path, default branch. Template: `.claude/shared/templates/new-project/CLAUDE.md (fallback: ~/.claude/shared/templates/new-project/CLAUDE.md)`.

**README.md** (for humans, in Russian): project title, purpose, folder structure overview, link to references/. Template: `.claude/shared/templates/new-project/README.md (fallback: ~/.claude/shared/templates/new-project/README.md)`.

When auditing, verify that CLAUDE.md and README.md stay minimal — detailed info belongs in project-knowledge.

## Custom Domain Files

Add when project has a significant domain not covered by 4 core files (bot.md, vault.md, trading.md).

Process: create in `references/` → update project-knowledge SKILL.md to list it → update CLAUDE.md and README.md if they list doc files.

## Authoring a Documentation Rule

Writing a rule that says "every X must be documented in Y" is the visible half. The half that
decides whether the rule survives is invisible at authoring time. A documentation rule is a claim
that a file will keep matching reality, and the claim is worth exactly as much as the mechanism that
detects divergence. Prose stating an obligation, with no trigger at the moment of action and no
command that fails when the obligation was skipped, decays into a description of what someone once
intended.

Ship all three alongside the rule text:

1. **A home the environment cannot shadow.** Name the file the rule lives in and say why that file
   cannot be silently overridden here. Where personal skills override project skills, a rule placed
   in a skill applies to some people and not others — and nothing reports the difference. A rule that
   must hold for everyone goes in the file that travels with the repository.
2. **A trigger at the moment of action** — a hook, a reflex, a checklist step, a pre-commit gate —
   not only a paragraph read at session start.
3. **An executable drift check**: a command that answers "is this document still true?" and exits
   non-zero on drift. Run it against the current repo before shipping, in both directions — a clean
   pass **and** a deliberately broken case — so the check is known to fire rather than believed to.

Portfolio-level events (a new project, a status change, a host move, a retirement) belong in the
registry/index row, which is a different destination from a per-project changelog; route them
explicitly so neither absorbs the other.
