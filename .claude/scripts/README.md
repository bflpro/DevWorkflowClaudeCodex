# `.claude/scripts/` — машинные проверки процесса разработки

Скрипты, которые превращают «готово» из утверждения модели в проверяемый файл. Работают поверх
флоу этого workflow (`/decompose-tech-spec` → `/do-task` / `/do-feature` → `/done`) и ничего в нём не
заменяют — только добавляют квитанции там, где раньше было слово исполнителя.

| Скрипт | Что делает | Кто вызывает |
|---|---|---|
| `wave-check.py work/<feature>` | Проверяет, что задачи одной волны можно запускать параллельно | `task-decomposition` (Cross-Task check), `task-validator` §F, `/do-feature` перед каждой волной |
| `owns-check.py work/<feature> N` | Проверяет, что исполнитель не вышел за `owns_paths` задачи | `task-accept.py` (сам), можно руками |
| `findings-sync.py work/<feature> N` | Находки ревьюеров → канонические файлы со статусом `open/closed` | `task-accept.py` (сам), `/do-task` перед каждым повторным раундом ревью |
| `task-accept.py work/<feature> N` | Квитанция приёмки задачи — единственное основание для `status: done` | `/do-task` Step 4, `/do-feature` Phase 3, `/done` (проверка наличия) |
| `check-techspec-readiness.py --changed` | Объявлен ли `level:` и заполнена ли Prod-readiness в техспеке | `tech-spec-planning`, перед ревьюерами |
| `check-readme.py --changed` | Обязательные разделы в тронутых README проектов | перед коммитом |
| `scan-staged-secrets.py` | Секреты и запрещённые файлы (`.env`, ключи) в индексе git | перед коммитом (свой pre-commit хук проекта) |
| `check-setup.sh` | Диагностика установки: node/python3, хуки в `settings.json`, наличие скриптов, сверка `.codex` | руками после установки |
| `reflex-check.mjs` | PreToolUse-хук: подсовывает урок из `.claude/reflexes/` перед совпавшим вызовом | `settings.json` |
| `post-compact-restore.sh` | PostCompact-хук: после сжатия контекста восстанавливает лиду контекст выполняемой фичи из `checkpoint.yml` | `settings.json` |

`taskflow.py` — общая библиотека для четырёх первых (парсинг frontmatter, пути, git, нормализация
отчётов ревьюеров). Не запускается сам.

## Поток данных

```text
tech-spec "Files to modify / Files to read"
        │  task-creator
        ▼
tasks/N.md  frontmatter: owns_paths, reads, never_touch, verify_cwd, start_commit
        │
        ├── wave-check.py ──► exit 1 = волну не запускать (write/write, read/write, depends_on)
        │
        │  исполнитель: start_commit = HEAD, правит только owns_paths, коммитит
        │  ревьюеры:    logs/working/task-N/{reviewer}-{round}.json   (gitignored)
        ▼
task-accept.py
   ├─ гоняет команды из "## Verification Steps → Automated / Smoke" (cwd = verify_cwd, таймаут 900 с)
   ├─ owns-check.py   → logs/receipts/task-N/owns-check.json
   ├─ findings-sync.py → logs/receipts/task-N/findings/<fp>.json + FINDINGS.md
   └─ пишет logs/receipts/task-N/acceptance.json  { accepted: true|false, reasons: [...] }
        │
        ▼
status: done  ⇐ только при accepted: true        /done: проверяет, что у каждой done-задачи есть квитанция
```

## Почему так

- **Квитанция, а не отчёт.** Типовые сбои — задачи одной волны читали то, что пишет сосед;
  «закрыто частично» выводило критическую находку из очереди на несколько раундов — нарушали
  правила, которые уже были написаны в скиллах и всё равно не срабатывали.
  Правило в тексте исполняется, когда о нём вспомнили; скрипт с ненулевым кодом — всегда.
- **Хешируется тело задачи, не весь файл.** Frontmatter меняется легально (`status`, `start_commit`);
  тело — контракт. `task_sha256` в квитанции ≠ текущий хеш → задачу переписали после приёмки,
  `/done` это увидит.
- **`logs/receipts/`, а не `logs/working/`.** `work/**/logs/working/` в `.gitignore` — отчёты
  ревьюеров туда и остаются. Квитанция, которой нет в истории, не доказательство, поэтому
  receipts живут отдельно и коммитятся вместе с волной.
- **Закрыть находку может только тот же ревьюер, только в следующем раунде, только явным
  `closures[]`.** Отчёт, который просто перестал упоминать находку, её не закрывает; `partially` = `open`;
  серьёзность не понижается, пока вопрос не отвечен. Это ровно то, чего раньше не было.
- **Команды верификации запускаются через shell** (`subprocess.run(..., shell=True)`) — осознанно.
  Команды приходят из наших же task-файлов и уже используют пайпы (`| grep -qx`), а `/done`
  и так гоняет их через Bash. Это не песочница для чужого кода; ценность — в записанном exit-коде
  с привязкой к хешу задачи. Чужие команды сюда не попадают.
- **Старые фичи не ломаются.** Нет `owns_paths` → `wave-check` пишет `skipped`, `owns-check`
  выходит с кодом 3, `/done` пишет «feature predates task receipts». Ничего не блокируется задним числом.

## Откуда взято

Идея трёх механизмов — `owns_paths`/`never_touch` с проверкой границ, квитанция приёмки,
привязанная к хешам, находки как канонические файлы со статусом закрытия — из
[VKirill/claude-lane-stack](https://github.com/VKirill/claude-lane-stack) @ `e01145e` (v1.27.0, MIT).
Код написан с нуля под layout `work/<feature>/tasks/N.md`; из репозитория ничего не копировалось,
ставить его целиком сочли избыточным.

## Форматы

**Frontmatter задачи (новые поля):**

```yaml
owns_paths: [src/api/users.ts, src/models/user.ts]   # каталог = всё под ним; glob допустим
reads: [src/api/index.ts]
never_touch: [".env*", "**/data/**"]
verify_cwd: .
start_commit: 3f2a9c1…                                # ставит исполнитель при in_progress
```

**Команда верификации** — строго `` - `команда` → ожидание ``. Один backtick-блок на строку;
`exit N` в ожидании задаёт код, иначе ожидается 0; пояснения — отдельными строками без дефиса.

**`acceptance.json`** — `task_sha256`, `start_commit`, `end_commit`, `attempt`, `verification[]`
(команда, cwd, exit_code, ok, хвост вывода), `owns_check`, `reviews[]` (последний раунд каждого
ревьюера), `findings.open / open_critical`, `accepted`, `reasons[]`.

**Закрытие находки в отчёте ревьюера** (только на повторном раунде):

```json
"closures": [{"fingerprint": "90b9bcd71e7d", "verdict": "closed", "evidence": "contract.py:283 …"}]
```

**Закрытие лидом — `status: "triaged"`** (build-route шаг 6, `review-lenses/README.md`): лид пишет
`{lens}-2.json` под именем линзы, `closures[]` — вердикт триажа с доказательством. Это не вердикт
ревьюера, поэтому `task-accept` принимает `triaged` только при `findings.open == 0`: находка с
маршрутом `ask` (closure `open`) держит задачу, пока человек не ответил.

## Общий чекаут нескольких сессий

`owns-check` считает файлами задачи: изменения из коммитов между `start_commit` и `HEAD`,
**чьё сообщение начинается с типа без скоупа и содержит `task N`** (конвенция исполнителя:
`feat: task N — …`, `fix: address review round M for task N`); служебные коммиты ведущего
со скоупом (`chore(tasks): …`) не считаются, даже если называют задачу, плюс всё незакоммиченное. Коммиты без метки —
чужие лейны в том же чекауте, они не считаются утечкой. Чужие незакоммиченные файлы
(`git ls-files --others`) отбрасываются только флагом `--ignore-untracked` у `owns-check`
и `task-accept`; в однолейновом репозитории флаг не нужен. Чужой **незакоммиченный** файл
исключается только явно: `--ignore <путь>` (повторяемый), и путь попадает в квитанцию как
`ignored_by_lead` — исключение видно, а не растворено в правиле. Причина: без этого квитанция
в общем чекауте падает с десятками «утечек» из коммитов и черновиков других сессий.

## `check-techspec-readiness.py` — уровень и Prod-readiness

Проверяет результат, а не шаблон: объявлен ли `level:` (L0–L3) и заполнена ли таблица
Prod-readiness в техспеке. Появился потому, что правило «пустых ячеек быть не должно»
(`ENGINEERING.md` §2) держалось на дисциплине модели, а шаблон существует в двух копиях —
проектной и личной, и личная перекрывает проектную.

```bash
python3 .claude/scripts/check-techspec-readiness.py --changed        # в гейтах: только изменённые
python3 .claude/scripts/check-techspec-readiness.py work/<f>/tech-spec.md
```

Для LLM-фич дополнительно требует строку про лимит стоимости и гейт автозапуска и раздел
Evals в Testing Strategy. Ненулевой код — пробел закрывать до ревьюеров.

## `check-readme.py` — обязательные разделы README

Правило «README — часть результата»: всё, что программируется (сервис, обработчик, скрипт,
интеграция, cron), не готово, пока рядом нет `README.md` с семью разделами. Список ниже — источник
правила; если в проекте свои конвенции документации (например, в `CLAUDE.md` или `ENGINEERING.md`
проекта), они ссылаются сюда или переопределяют `REQUIRED` в скрипте. Скрипт ищет по заголовкам
вне блоков кода: вступление под H1, поток данных, почему так, что трогает снаружи, инварианты,
запуск и деплой, как понять, что сломалось. README проекта — `projects/<проект>/README.md`;
`--changed` смотрит только `projects/` (изменённые против HEAD и новые неотслеживаемые).
Формулировки заголовков в README разные, поэтому сравнение
идёт по основам слов (`REQUIRED` в скрипте). Зелёный результат значит «вопрос задавали», а не
«ответ верный».

```bash
python3 .claude/scripts/check-readme.py --changed                  # гейт: README, тронутые против HEAD
python3 .claude/scripts/check-readme.py projects/X/README.md
python3 .claude/scripts/check-readme.py --all                      # инвентаризация, легаси даст пробелы
```

- **Почему `--changed`, а не `--all`.** На существующем корпусе большинство старых README полными
  не проходят, даже хорошие. Гейт на весь корпус упал бы в первый день и стал бы шумом; по
  `ENGINEERING.md` §4d легаси чинится при возврате к проекту.
- **Пометка `<!-- readme-check: skip — <причина> -->`** для папок, которые сами ничего не
  исполняют (индекс, база знаний). Пропуск печатается и считается в итоге отдельно,
  чтобы исключение было видно, а не растворялось в правиле.
- **Вердикт над размером выборки.** `--changed` без тронутых README печатает «проверено 0 …
  пустая выборка», а не «всё хорошо» (то же правило, что у `wave-check`).
- **Больше 800 строк** — предупреждение без смены кода возврата: деление README делается при
  следующей правке файла.
- **`git -c core.quotePath=false`** обязателен: без него git экранирует кириллические имена
  папок, и README вроде `projects/Аналитика продаж/` молча выпадает из выборки.

Тесты: `python3 .claude/scripts/tests/test_check_readme.py` (8 тестов). Мутанты «пустой список
разделов», «заголовки в блоке кода считаются», «вступление не проверяется» тестами убиваются.

## Коды возврата

| Скрипт | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| wave-check | волны чистые | есть нарушения | нет задач / не читается | — |
| owns-check | внутри границ | утечка или `never_touch` | нет `start_commit` / задачи | нет `owns_paths` (skipped) |
| findings-sync | нет открытых critical | есть открытые critical | нет отчётов | — |
| task-accept | `accepted: true` | `accepted: false` | нет задачи | — |
| check-readme | все проверенные README полные (или выборка пуста — печатается явно) | есть пробелы | файл не найден / нет аргументов | — |

## Запуск и тесты

```bash
python3 -m unittest discover -s .claude/scripts/tests -t .claude/scripts/tests   # 45 тестов
python3 .claude/scripts/wave-check.py work/<feature>
python3 .claude/scripts/task-accept.py work/<feature> 3
```

Нужен только Python 3 с PyYAML (`pip install pyyaml`). Сеть не используется.

## Как понять, что сломалось

- Задача со `status: done` без `logs/receipts/task-N/acceptance.json` — флоу обошли:
  `for t in work/*/tasks/*.md; do grep -q '^status: done' $t && ...` — проще: `/done` перечислит.
- `acceptance.json` с `accepted: false`, но задача `done` — квитанцию проигнорировали.
- `FINDINGS.md` с блоком «Open for more than one round» — находка едет через раунды без вердикта.
- `wave-check` молчит про волну, в которой явно есть зависимость → у задач пустые `owns_paths`
  (смотреть `skipped_no_owns_paths`), это находка `task-validator` §A.
