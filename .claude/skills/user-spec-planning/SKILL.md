---
name: user-spec-planning
description: |
  Creates user-spec.md through adaptive interview with codebase scanning and dual validation.

  Use when: "сделай юзер спек", "проведи интервью для юзер спека",
  "создай юзерспек", "user spec", "detailed planning", "хочу продумать фичу",
  "опиши требования к фиче", "сделай описание фичи", "/new-user-spec"

  For tech planning use tech-spec-planning. For project planning use project-planning.
---

# User Spec Planning

Thorough adaptive interview → codebase scan → user-spec.md → dual validation → user approval.
Output: `work/{feature}/user-spec.md` with status `approved`.

## Interview Style

Conduct interview in Russian. Be thorough and opinionated — an engaged co-thinker who actively proposes solutions and challenges weak answers.

**How to interview:**
- 3-4 questions per batch. Run as many batches as needed until the cycle's items are fully covered.
- Propose solutions based on Project Knowledge: "В architecture.md описан паттерн X — думаю, здесь нужно Y. Согласен?"
- Challenge with substance — concrete counterexamples, code references, unexplored scenarios: "А что если пользователь сделает Z? В коде модуль Q не обрабатывает этот случай."
- Accept the answer after one substantive challenge and move on to the next gap.
- When user says "не знаю": help think through it (examples, common patterns). Optional item → mark TBD. Required item → break into simpler questions.

**Interview depth** depends on feature size (S/M/L in interview metadata):
- S (1-3 files, local fix): focused interview, core behavior
- M (several components): moderate depth, integration questions
- L (new architecture): deep interview, thorough edge cases and risk analysis

## Process

### Phase 0: Init

1. Check for existing interview: look in `work/*/logs/userspec/interview.yml` for `metadata.status: in_progress`. If found — load, show discussed topics summary, resume. If multiple found — show list, let user choose.
2. Get task description: "Опиши, что хочешь сделать."
3. Determine work_type (feature / bug / refactoring) from description.
4. Propose feature name (kebab-case), get user confirmation.
5. Run the folder initialiser — project copy first, personal copy as fallback; the script resolves its
   own templates relative to itself, so the project copy needs nothing from `$HOME`:

   ```bash
   bash .claude/shared/scripts/init-feature-folder.sh {name} \
     || bash ~/.claude/shared/scripts/init-feature-folder.sh {name}
   ```

   Creates folder structure with interview.yml.
6. Update interview.yml: set metadata.started, metadata.status: in_progress, phase1_feature_overview.feature_name, phase1_feature_overview.work_type.

**Checkpoint:** interview.yml exists with status in_progress, feature name confirmed.

### Phase 1: Study Project Knowledge

Read ALL files from `.claude/skills/project-knowledge/references/`. If directory missing or empty — warn user, suggest running project-planning skill (or `/init-project-knowledge` command).

These files are your context for the entire interview. Reference them when asking questions and proposing solutions.

### Phase 2: Cycle 1 — General Understanding

**Scope:** `phase1_feature_overview` items in interview.yml.

1. Score user's initial description against all items (detailed 80-95%, brief 50-70%, vague 20-40%, not mentioned 0%).
2. Run interview loop (see below) on phase1_feature_overview items.
3. During this cycle — determine feature size S/M/L and agree on testing strategy:
   - S: integration/E2E usually not needed — state why
   - M: propose whether integration tests make sense, explain reasoning
   - L: propose specific integration and E2E scope with justification

### Phase 3: Code Scanning

Launch `code-researcher` subagent (Task tool, opus) with feature path and feature description from Cycle 1.

After subagent completes — read `{feature_path}/code-research.md`. Use findings in Cycle 2 questions.

If during later phases a gap is discovered — launch `code-researcher` again with the specific question to investigate.

### Phase 4: Cycle 2 — Code-Informed Refinement

**Scope:** `phase2_user_experience` + `phase3_integration` items.

1. Summarize understanding: "Я понял задачу так: [X]. Делать планирую так: [Y, based on code]."
2. Questions based on code findings: "Нашёл модуль X, который делает Y — переиспользуем?"
3. Cover deploy and user actions (items `deploy_approach`, `manual_user_actions`):
   - "Нужны ли ручные шаги для запуска? (создать бота, получить API ключи, настроить сервис, зарегистрироваться где-то)"
   - "Как деплоить? Что нужно настроить? (уже есть CI/CD, нужно настроить, ручной деплой)"
   - "Как проверить что работает после деплоя? (MCP-инструменты, curl, ручная проверка)"
   - "Что можно проверить прямо во время разработки, без деплоя? (вызвать внешний API, запустить локально, проверить конфиг, потыкать UI на localhost, протестировать промпт)"
4. Run interview loop on phase2 + phase3 items.

### Phase 5: Cycle 3 — Review & Finalize

**Scope:** ALL items across all phases still below threshold.

Cleanup pass: revisit anything not fully covered in Cycles 1-2. Deepen edge cases and error scenarios — probe for scenarios user hasn't considered, even if items formally passed threshold.

Run interview loop on remaining gaps.

### Phase 6: Completeness Check

Launch `interview-completeness-checker` subagent (Task tool, sonnet) with feature path. It reviews interview.yml against PK files and code-research.md.

- `needs_more` → ask the suggested questions, re-run checker
- `complete` → proceed to Phase 7

**Carry the gap list forward — a gate whose output nothing re-verifies is a gate in name only.** When the checker returns a numbered gap list, persist it under `{feature}/logs/userspec/` and treat that file as a mandatory input to Phase 8. For every numbered gap, the validation phase reports exactly one of: **closed** (the content is in the user-spec), **consciously deferred** (written into the spec as an accepted limitation or a labelled assumption), **dropped** (neither). A dropped critical or major gap fails the corresponding check, the same as any other critical finding. It must never depend on a validator noticing the leftover gate file by chance while reading the folder for something else — the moment attention moves to writing the artefact, a numbered gap list becomes optional advice.

### Phase 7: Create User Spec

1. Copy template to working file:
   - Copy `.claude/shared/work-templates/user-spec.md.template (fallback: ~/.claude/shared/work-templates/user-spec.md.template)` → `work/{feature}/user-spec.md`
   - Edit sections one by one using Edit tool, replacing placeholders with interview data
   Reason: agent sees template structure and comments while editing each section, preventing drift from template format.
2. Content rules:
   - "Что делаем" — self-contained, understandable without the interview
   - "Зачем" — concrete user value, not "улучшить UX"
   - Acceptance criteria — testable, no "работает корректно"
   - Every discussed topic from interview must appear in the spec
   - "Не делаем" and "Сигнал успеха" are filled from the interview, never left as template text — the
     five-field core (что / зачем / как / не делаем / сигнал успеха) is what a tech-spec and a task card
     are allowed to quote; everything else in the spec is appendix (since 2026-09-30)
3. If feature seems large (>10 criteria, >3 user flows, >5 integrations) — suggest splitting.

Git commit: `draft(userspec): create user-spec for {feature}`

### Phase 8: Validation

Run 2 validators in parallel (Task tool):
- `userspec-quality-validator` (sonnet) — document structure, template compliance, formal completeness. Returns JSON with per-check pass/fail and findings list.
- `userspec-adequacy-validator` (opus) — feasibility, over/underengineering, better alternatives. Returns JSON with findings by category and severity.

**Pass to both validators:** `user-spec.md`, and `code-research.md` when it exists — a feasibility verdict reached without the research artefact re-derives it from the spec's own claims.

**Premises vs requirements — check before approving, not after.** A spec is two genres in one document. A requirement states what must become true and cannot be falsified. A **premise** states what is already true — "that integration is already configured", "the field is already filled", "it gets picked up automatically", "it works like X already does". A premise can be false, and a false premise silently invalidates every requirement standing on it while leaving no mark on the document. Before Phase 9:

1. Extract every statement about the current state of the system into one short written list — from the spec text and from the user's own wording, on paper, not from memory.
2. Mark each: **confirmed** (`file:line`, or the code-research finding it rests on), **refuted**, **not checkable** (and why). "Not checkable" is a result and is written down as one; an unverified premise is never presented as a verified one.
3. A refuted premise is never routed around in silence: the requirement standing on it either changes, or acquires an explicit item that makes the premise true. Either way the change is stated to the user in the approval message, not absorbed into the text.
4. **An exemplar reference is a premise.** "Like X", "same as already built", "by analogy with" — resolve it to a file and line and write out what the exemplar actually does. If it does something else, the spec says so and defines the mechanism itself; the reference cannot stand in for the definition, because every later reader sees a reference that resolves and none of them sees the divergence.

**Handling findings:**
- Obvious issue → fix silently
- Borderline → discuss with user
- Disagree with finding → reject with reasoning
- Conflict between validators → userspec-adequacy-validator takes priority (substance over form)

After the validation round (validators wrote reports + you applied fixes), git commit: `chore(userspec): validation round {N} — {summary of fixes}`. **One full round by default (since 2026-09-30).** Re-run only the validator(s) that reported a `critical` finding, and only on that finding's section; a second full pass is not run. Max 2 rounds in total, then show remaining issues to user. Reason: the second full pass mostly rephrased the first one's findings (work/etalon-razrabotki retro Р7) while costing as much.

### Phase 9: User Approval

Show user-spec.md link + validation summary. If changes requested — edit and show again.

When approved:
1. Set user-spec.md frontmatter `status: approved`
2. Set interview.yml `metadata.status: completed`
3. Git commit: `chore(userspec): approve user-spec for {feature}`
4. For M/L features — offer grill-me before tech-spec: "Хочешь прогрилить user-spec перед техническим проектированием? Задам жёсткие вопросы по ключевым решениям — выловим дыры до того как писать tech-spec."
5. Suggest `/new-tech-spec {feature-name}`

## Interview Loop

Runs inside each cycle. Repeats until the cycle's scope is fully covered.

```
1. Find gaps: required items in current scope with score < 85%. Lowest first.
2. Ask 3-4 questions about different gaps. Reference PK and code findings.
3. User responds.
4. Update interview.yml:
   - conversation_history: add full Q&A entry
   - Item: score, value, gaps, status
   - metadata: last_updated, current_question_num
   - Save immediately
5. Check stop criteria (BOTH must be true):
   a) All required items in scope score >= 85%
   b) Structural: every required item has non-empty value,
      no TBD in value, gaps empty or only conscious limitations
6. Not done → step 1. Done → exit cycle.
```

Scoring: detailed answer 80-95%, brief 50-70%, vague 20-40%, not mentioned 0%.

**The loop assumes a user who is present. When they are not, do not block — score from the record and label the remainder.** This is the normal case for a follow-on phase of an existing feature, and whenever the user has explicitly delegated ("answer later if it is not critical"). Running the loop as written then leaves two bad options: stall the session on a batch of questions nobody will answer for hours, or invent scores for items the user never answered.

1. Score every item from the record FIRST — prior phases' specs, `decisions.md`, shipped code — and cite the source document in the item's `value`. An item answered by the record is answered.
2. Put the true residual gaps into ONE `conversation_history` entry with `user_answer: ""`.
3. Write the spec now. Resolve each residual gap with a defensible default, marked `[ASSUMPTION]` in a dedicated section, and state for each one what a different answer would change — usually a paragraph, not the architecture.
4. Hand the questions to the user in the closing message, with the defaults already applied.

A labelled assumption counts as covered-with-caveat, not as a gap: the completeness checker and the validators then run against a full document instead of a placeholder.

Optional items: cover when user mentions relevant context or when naturally connected to required items.

## Work Type Adaptations

All three cycles apply to any work_type, but focus shifts:

**Bug:** Cycle 1 → reproduction steps, expected vs actual, severity, when it broke. Code scanning → find bug location and root cause. Cycle 2 → fix approach, regression risks.

**Refactoring:** Cycle 1 → current problems, target architecture, stability guarantees. Code scanning → current structure, dependencies, test coverage. Cycle 2 → migration path, backward compatibility.

## Scope Changes

If understanding changes significantly during interview:
- Update affected scores downward, add new gaps
- Reassess feature size (S/M/L)
- If work_type changes (was feature, actually bug) — pivot items accordingly
- Note the change in interview.yml notes section

## Self-Verification

- [ ] All cycles completed, completeness checker passed
- [ ] user-spec.md filled with real content (no placeholders)
- [ ] Both validators passed (or issues resolved with user)
- [ ] User approved, frontmatter status: approved
- [ ] interview.yml metadata.status: completed
- [ ] Suggested `/new-tech-spec` as next step
