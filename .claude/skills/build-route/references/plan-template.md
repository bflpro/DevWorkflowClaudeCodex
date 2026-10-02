---
status: in_progress                # in_progress -> done (только по квитанции)
depends_on: []
wave: 1
produces: [work/quick-{slug}/logs/receipts/task-1/acceptance.json]
skills: [build-route]
verify: [smoke]                    # smoke — если есть раздел Smoke; иначе []
reviewers: [quick]                 # quick | [quick, security-auditor] — вторая линза только при auth/вводе/секретах
teammate_name:
executor: main                     # oneshot исполняется в основной сессии, субагент-исполнитель не спавнится
owns_paths: []                     # ← из разведки. Правим ТОЛЬКО эти пути; выход = blocked (owns-check.py)
reads: []
never_touch: [".env*", "**/data/**"]
verify_cwd: .
start_commit:                      # `git rev-parse HEAD` до первой правки; без него нет ни owns-check, ни квитанции
authored_by: build-route
level: L1                          # L0 | L1 (L2+ в oneshot не бывает — см. ENGINEERING.md §1a)
route: oneshot
sizing:                            # результат порога, дословно — чтобы приёмка видела основание
  lines_estimate:
  files: 0
  external_write: false
  server_unit: false
  prod_prompt: false
---

# Task 1: {название одной строкой}

<!-- Потолок карточки — два экрана (~1600 токенов). Не влезает — это не oneshot: остановиться
     и уйти в конвейер спек (ENGINEERING.md §1a). Разведку не переписывать в прозу — только Code Map. -->

## Intent

<frozen-after-approval>
<!-- Что должно стать правдой, когда работа сделана; что не должно измениться; что вне рамок.
     Заполняется после разведки. Открытые вопросы задаются человеку ОДНИМ сообщением до заморозки;
     ответы записываются сюда как решения. После первой правки кода блок меняет только человек. -->

**Сделать:** …
**Не менять:** …
**Вне рамок:** …
**Решения:** (ответы человека на открытые вопросы; «нет» — если вопросов не было)
</frozen-after-approval>

## Code Map

<!-- Из разведки. Только то, что нужно для правки: файл → символ/строки → что переиспользовать →
     что не трогать. Не пересказывать исследование. -->

- `path/file.py` — `func()` строки N–M: … ; переиспользовать … ; не трогать …

## Acceptance Criteria

<!-- Given/When/Then, эффект, а не акт. Меряет только owns_paths этой карточки. -->

- [ ] Given … When … Then …

## TDD Anchor

<!-- Тест до кода, где применимо. Для не-кода — одна строка `Не применимо: <почему>`. -->

- `tests/test_x.py::test_y` — …

## Verification Steps

### Automated
- `pytest tests/test_x.py -v` → all pass

### Smoke
<!-- Опустить раздел, если проверок нет; тогда verify: [] в шапке. -->

## Implementation Notes

<!-- Заполняется по ходу: решения, сюрпризы, пробелы намерения (пробел → вопрос человеку, не догадка). -->

## Review Triage Log

<!-- Одна строка на находку: `<линза> | <file:line> | <вердикт> | <доказательство> | <маршрут>`.
     Вердикт ставит лид после проверки в коде; серьёзность из отчёта линзы не учитывается.
     Ни одна находка не пропадает: false — с опровержением, defer — со ссылкой на deferred-work.md. -->

## Reviewers

- **quick** → `work/quick-{slug}/logs/working/task-1/quick-{round}.json`
- **security-auditor** (условно) → `work/quick-{slug}/logs/working/task-1/security-auditor-{round}.json`

Приёмка цитирует `work/quick-{slug}/logs/receipts/task-1/acceptance.json`
(пишет `python3 .claude/scripts/task-accept.py work/quick-{slug} 1`).

## Post-completion

- [ ] Квитанция: exit 0 и `accepted: true`
- [ ] Закрывающий блок в ответе (L1): `Риски:` / `Отложено:` / `Наблюдаемость:`
- [ ] Отложенное — в `work/quick-{slug}/deferred-work.md`
