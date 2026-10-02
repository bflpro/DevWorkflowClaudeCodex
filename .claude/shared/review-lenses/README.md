# review-lenses — ревью-линзы и триаж

<!-- readme-check: skip — папка промптов, ничего не исполняет; консумер отчётов — .claude/scripts/findings-sync.py -->

Одна папка для всех, кто ревьюит код: `/build` (скилл `build-route`), `code-writing` Phase 3,
`feature-execution`, `/do-task`. Линза — субагент **без контекста сессии**, который читает дифф по
пути, не ставит серьёзность и пишет отчёт в общем конверте. Грейдит и закрывает **лид** по
`triage.md`.

## Наборы

| Набор | Когда | Линзы |
|---|---|---|
| **quick** | oneshot (`ENGINEERING.md` §1a), задачи размера S | `quick`; плюс `security` условно (auth / ввод / секреты) |
| **thorough** | задачи M/L, ad-hoc фиксы в конвейере | `blind-hunter`, `edge-case-hunter`, `verification-gap`, `intent-alignment`, `security`, `prod-readiness` (L1+) |

Все линзы набора запускаются **в одном ходу** (`run_in_background: false`), лид ждёт всех, читает
отчёты только после того, как запущены все. Диффа в промпте нет — только путь `{diff_file}`.

## Конверт отчёта

`{feature_dir}/logs/working/task-{N}/{lens}-{round}.json`:

```json
{"reviewer": "<lens id>", "round": 1, "status": "no_verdict",
 "findings": [{"file": "", "line": 0, "category": "", "summary": "", "evidence": "", "recommendation": ""}]}
```

Имена ключей — из `.claude/scripts/taskflow.py` (`parse_report`, `_normalise_finding`): `summary`
даёт текст находки, `file` + `category` + текст — отпечаток; находка без `severity` получает
`major`, `status: "no_verdict"` нормализуется в `unknown` — ни то, ни другое не блокирует квитанцию.

## Закрытие лидом

После триажа лид пишет `{lens}-2.json` с тем же `reviewer`, `round: 2`, `status: "triaged"`,
`findings: []` и `closures[]`: `{"fingerprint", "verdict": "closed" | "open", "evidence":
"<вердикт триажа>: <доказательство>"}`. Отпечатки — из `logs/receipts/task-{N}/FINDINGS.md` после
`findings-sync.py`. `closed` — для `patch` после фикса, `false`, отброшенных `low` и `defer`;
`open` — только для `ask`, пока человек не ответил. Это и есть «закрытие лидом с доказательством»:
скрипты не менялись, правило «закрывает тот же reviewer» выполняется буквально — тем же именем
линзы, раундом 2, от руки лида.

## Подстановки в промптах

`{diff_file}` — унифицированный дифф с `start_commit`, включая неотслеживаемые файлы, в scratchpad;
`{card}` — карточка задачи; `{report}` — путь отчёта; `{verbatim_intent}` — блок `## Intent`
карточки дословно (только `intent-alignment`). Заполняет лид до запуска.

## Откуда взято

`edge-case-hunter.md`, `verification-gap.md`, `claims-check.md`, `deletion-check.md` — дословно
из `bmad-code-org/BMAD-METHOD` @ `1cbcfa2` (28.09.2026, MIT), `skills/bmad-build/review-prompts/`
и `references/`; изменены только разделы вывода (наш конверт вместо JSON-массива и markdown-блоков),
пути ссылок и имена секций карточки (`## Acceptance Criteria` вместо `## Tasks & Acceptance`).
`blind-hunter.md`, `intent-alignment.md` и текст `quick.md` — из `customize.toml` того же скилла
(`thorough_lenses` / `quick_lenses`), обёрнуты в конверт. `triage.md` — по `step-oneshot.md` и
`step-04-review.md`. `security.md` и `prod-readiness.md` — наши; второй несёт критерии из книг, которые раньше жили в ролевых `code-reviewer` / `test-reviewer` / `prompt-reviewer`, и сработавшие блоки чеклиста prod-review.
