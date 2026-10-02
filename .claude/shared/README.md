# .claude/shared — общие шаблоны и ассеты скиллов

Здесь лежит всё, что скиллы и агенты этого workflow **читают, но не содержат в себе**:
шаблоны артефактов фичи (`user-spec`, `tech-spec`, `task`, `decisions`, `execution-plan`,
`checkpoint`), шаблоны интервью, скрипт создания папки фичи и шаблоны нового проекта.
Набор полный и едет вместе со скиллами: установки workflow в проект достаточно, домашняя
папка не нужна.

## Поток данных

```
/new-user-spec
  → skills/user-spec-planning
      → bash .claude/shared/scripts/init-feature-folder.sh <feature>
          скрипт определяет свой каталог через BASH_SOURCE и читает шаблоны РЯДОМ С СОБОЙ:
            work-templates/user-spec.md.template   → work/<feature>/user-spec.md
            work-templates/tech-spec.md.template   → work/<feature>/tech-spec.md
            work-templates/decisions.md.template   → work/<feature>/decisions.md
            work-templates/checkpoint.yml.template → work/<feature>/logs/checkpoint.yml
            interview-templates/feature.yml        → work/<feature>/logs/userspec/interview.yml
      → далее скилл правит user-spec.md по секциям

/new-tech-spec   → skills/tech-spec-planning   → work-templates/tech-spec.md.template
/decompose-tech-spec → skills/task-decomposition → work-templates/tasks/task.md.template
/do-feature      → skills/feature-execution    → work-templates/execution-plan.md.template
/do-task, /qa    → decisions.md.template
/init-project    → templates/new-project/       (копируется целиком в новый проект)
skill-master     → interview-templates/skill.yml
```

## Почему так

**Ассет едет в том же репозитории, что и скилл, который его читает.** Отвергнутый вариант —
держать шаблоны только в `~/.claude/shared/` и передавать папку между людьми: на машине, где
оба пути ведут в один файл, «в репозитории лежит часть набора» и «скилл ищет не там» дают
одну и ту же картину «всё работает», и дефект невидим ровно там, где его могли бы заметить.
Вместе с папкой передаётся ещё и та версия, которая случайно оказалась на диске: устаревшая
домашняя копия `tech-spec.md.template` может не иметь полей `level:`, `footprint:` и раздела
Evals, которые проверяет `check-techspec-readiness.py`.

**Проектная копия первой, домашняя — запасная.** В скиллах путь записан как
`` `.claude/shared/X` (fallback: `~/.claude/shared/X`) ``, в исполняемых местах — как
`cp .claude/... || cp ~/.claude/...`. Домашняя ветка нужна, когда скиллы установлены
глобально в `~/.claude/skills/` и вызываются из репозиториев, где `.claude/shared/` нет. Отвергнутый вариант — только проектный путь: сломал бы работу в
остальных репозиториях.

**Скрипт ищет шаблоны относительно себя, а не относительно `$HOME` и не относительно cwd.**
`$HOME` делал скрипт непереносимым; cwd — ломался бы при запуске из подкаталога.

## Что трогает снаружи

| Что | Координаты |
|---|---|
| Домашняя копия набора | `~/.claude/shared/` — запасной источник шаблонов при глобальной установке скиллов |
| `$HOME` в `init-feature-folder.sh` | только как fallback-каталог, ничего туда не пишет |
| `~/.claude/tmp/` | `skill-master` складывает туда файл интервью |
| `~/.claude/teams/<team>/config.json` | читает `post-compact-restore.sh` (в `.claude/scripts/`), чтобы понять, эта ли сессия — лид |
| Вложенный `.gitignore` | `templates/new-project/.gitignore` — шаблон для новых проектов; git применяет его и к этому подкаталогу |

Токены и доступы не нужны: всё локальные файлы.

## Инварианты

- `init-feature-folder.sh` **идемпотентен**: `mkdir -p`, и каждый файл пишется только если
  его ещё нет. Повторный запуск на существующей папке добавляет недостающее и **никогда не
  перезаписывает** уже написанный `user-spec.md`, `tech-spec.md`, `decisions.md`,
  `interview.yml`, `checkpoint.yml`.
- Файлы этого каталога — шаблоны, их не правят «под фичу»: правка шаблона меняет поведение
  всех будущих фич и идёт отдельным коммитом.
- `work-templates/tasks/task.md.template` — источник правды для `task-validator`; поля
  `owns_paths`, `reads`, `produces`, `authored_by` и секция TDD Anchor из него удалять нельзя
  (гейты `owns-check.py` и `wave-check.py` на карточках без этих полей деградируют молча,
  см. `ENGINEERING.md` §4d).

## Запуск, проверка, деплой

Деплоя нет — файлы читаются из рабочей копии. Проверки, каждая реально выполнена:

```bash
# 1. Скрипт самодостаточен: с пустым $HOME должен создать полную папку фичи
cd "$(mktemp -d)" && mkdir fakehome
REPO=/path/to/your/project   # корень проекта с установленным workflow
HOME="$PWD/fakehome" bash "$REPO/.claude/shared/scripts/init-feature-folder.sh" smoke
find work -type f        # ожидается 5 файлов: user-spec, tech-spec, decisions, interview.yml, checkpoint.yml

# 2. Идемпотентность: второй запуск ничего не перезаписывает
echo "МОЁ" >> work/smoke/user-spec.md
HOME="$PWD/fakehome" bash "$REPO/.claude/shared/scripts/init-feature-folder.sh" smoke
tail -1 work/smoke/user-spec.md   # ожидается МОЁ

# 3. Установка цела: хуки, скрипты, зеркало .codex
bash "$REPO/.claude/scripts/check-setup.sh"
```

## Как понять, что сломалось

- `/new-user-spec` пишет `Error: template not found: work-templates/user-spec.md.template` —
  каталог неполный; скрипт печатает, где именно искал.
- `diff -r .claude/shared ~/.claude/shared` показывает расхождения — домашняя копия
  разъехалась с проектной. **Не копировать одну поверх другой:** расхождение бывает
  двусторонним, сливать через `git merge-file`.
- `check-techspec-readiness.py` жалуется на отсутствие `level:` или пустую Prod-readiness у
  свежего техспека — техспек создан из устаревшей домашней копии шаблона, а не из
  репозиторной.
- Папка фичи создалась без `interview.yml`, в stderr `Warning: interview template not found` —
  нет `interview-templates/feature.yml`.

## Откуда взято

Шаблоны — часть этого workflow и поставляются вместе с ним. Что в них добавлено под гейты:
`tech-spec.md.template` — `level:`, `start_commit:`, `footprint:`, receipts-правило в критериях
приёмки, раздел Evals; `tasks/task.md.template` — `owns_paths`, `reads`, `produces`,
`authored_by`, секция TDD Anchor; `scripts/init-feature-folder.sh` — шаблоны ищутся
относительно скрипта, а не `$HOME`.
