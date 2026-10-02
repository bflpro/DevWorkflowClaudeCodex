# CLAUDE.md — правила проекта

> Шаблон из DevWorkflowClaudeCodex. Допишите сюда описание своего проекта, структуру и
> конвенции. Правила процесса ниже — минимум, на который опираются скиллы workflow.

## TL;DR

1. **Читать перед записью.** Никогда не перезаписывать вслепую; не удалять файлы без подтверждения.
2. **Секреты — только в `.env` / переменных окружения.** Не коммитить, не печатать.
3. **План до кода** для нетривиальных задач. Размер процесса выбирает `/build` (`ENGINEERING.md` §1a).
4. **Уровень зрелости — до кода** (`ENGINEERING.md` §0): L0 / **L1 по умолчанию** / L2 / L3.
5. **Prod Gate для L1+** перед ревью и коммитом (`ENGINEERING.md` §2); перед деплоем — `/prod-review`.
6. **Готовность задачи — квитанция, а не слова** (`ENGINEERING.md` §4c): `status: done` только
   после `python3 .claude/scripts/task-accept.py work/<feature> N` с exit 0.
7. **README — часть результата.** Всё запрограммированное описано в `README.md` своей папки:
   что делает, поток данных, почему так, что трогает снаружи, инварианты, как запустить и
   проверить, как понять, что сломалось. Проверка: `python3 .claude/scripts/check-readme.py --changed`.
8. **Verify, don't guess.** Перед использованием API — прочитать доки или проверить эндпоинт.
9. **Runtime-данные не в git:** логи, state, БД, `work/*/logs/working/`.

## Структура проекта (заполнить)

```
/
├── CLAUDE.md, AGENTS.md, ENGINEERING.md   ← правила
├── work/<feature>/                        ← спеки, решения, задачи, квитанции фичи
└── …
```

## Команды workflow

| Хочу… | Команда |
|---|---|
| Выбрать размер процесса по разведке кода | `/build <задача>` |
| Быстрый план без кода | `/plan <задача>` |
| Описать фичу через интервью | `/new-user-spec` |
| Техспек + задачи из user-spec | `/new-tech-spec` → `/decompose-tech-spec` |
| Проверить план жёсткими вопросами | `/grill-me` |
| Выполнить одну задачу / всю фичу | `/do-task` / `/do-feature` |
| Написать код с TDD и ревью | `/write-code` |
| Ревью кода / проверить, что работает | `/review` / `/verify` |
| Продакшн-ревью перед деплоем | `/prod-review` |
| Закрыть фичу, обновить доки | `/done` |
| Ревью документа «свежим глазом» | `/prose-review <файл>` |
| Восстановить документацию по коду | `/ground-docs <путь>` |
| Новый проект / база знаний проекта | `/init-project` / `/init-project-knowledge` |

Типичная цепочка: `/new-user-spec` → `/new-tech-spec` → `/decompose-tech-spec` → `/do-feature` → `/done`.

## Коммиты

Semantic commits (`feat` / `fix` / `chore` / `refactor` / `docs`). Перед коммитом:

```bash
python3 .claude/scripts/check-readme.py --changed
python3 .claude/scripts/check-techspec-readiness.py --changed
```
