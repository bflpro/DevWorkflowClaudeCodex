# technical-writer — набор скиллов для технической документации

Вендоренный набор из 11 скиллов, 2 агентов и 2 команд: единый «домашний стиль» для
технических документов (спеки, README, ADR, ранбуки, постмортемы, changelog, тикеты,
API-референс, документирование легаси-кода) и ревью прозы.

## Что установлено

| Где | Что |
|---|---|
| `.claude/skills/technical-writing/` | ядро: стиль, правила достоверности (`references/truth.md`), запрещённые конструкции (`references/style.md`); остальные скиллы требуют его как фон |
| `.claude/skills/writing-design-docs/` | предложения, RFC, техспеки, планы миграции |
| `.claude/skills/recording-decisions/` | ADR и журнал решений |
| `.claude/skills/writing-changelogs/` | changelog, release notes, handover-сводка |
| `.claude/skills/writing-runbooks/` | ранбуки, инструкции по запуску, миграционные гайды |
| `.claude/skills/writing-issues/` | эпики, истории, баг-репорты, критерии приёмки |
| `.claude/skills/writing-postmortems/` | постмортемы и разборы инцидентов |
| `.claude/skills/documenting-legacy-codebases/` | реконструкция документации по коду |
| `.claude/skills/documenting-contracts/` | HTTP API, вебхуки, DTO, форматы файлов |
| `.claude/skills/reviewing-technical-prose/` | ревью и переписывание чужого текста, чеклист сдачи |
| `.claude/agents/doc-grounder.md` | read-only агент: сверяет документ с кодом на HEAD |
| `.claude/agents/prose-reviewer.md` | read-only агент: ревью документа «свежим глазом», вердикт привязан к SHA-256 |
| `.claude/commands/ground-docs.md` | `/ground-docs [path]` — кампания документирования легаси-кода |
| `.claude/commands/prose-review.md` | `/prose-review [file ...]` — ревью изменённых `.md` агентом `prose-reviewer` |

## Как соотносится с остальным workflow

- Правила написаны по-английски, но документ сохраняет свой язык: русский README
  пишется и ревьюится по-русски, английские словари запрещённых слов к нему не
  применяются.
- Пересечения: `documentation-writing` ведёт `project-knowledge`, этот набор —
  стиль любого документа. При конфликте побеждает `CLAUDE.md` проекта: например,
  `CHANGELOG.md` сервиса в формате «одна датированная строка на изменение» не
  переводится в формат `writing-changelogs`, если проект так решил.
- Жёсткое правило набора «никаких длинных тире» к уже существующим документам проекта
  задним числом не применяется — только к документам, которые пишутся с этим скиллом.

## Откуда взято

- Репозиторий: https://github.com/riekelt/technical-writer (каталог skills.sh:
  `riekelt/technical-writer`)
- Тег `v1.8.4`, коммит `85e53729dd959a2795d593d6769068e342cf3486` (2026-09-13)
- Лицензия: MIT, текст — `LICENSE` в этой папке
- Взято: `plugins/technical-writer/skills/*`, `agents/*`, `commands/*`.
- Изменено локально (26.09.2026), при обновлении из апстрима **перенести заново**:
  - `technical-writing/SKILL.md`, «Hard rules»: исключение для длинного тире (—) в русских
    документах; среднее тире и ` -- ` запрещены по-прежнему;
  - `reviewing-technical-prose/SKILL.md`, чеклист сдачи: ссылка на это исключение;
  - `.claude/agents/prose-reviewer.md`, шаг 4: механическая проверка учитывает исключение.
  Причина: без исключения `/prose-review` выносит BLOCKER любому русскому документу.
- Не взято: манифесты плагинов (`.claude-plugin`, `.codex-plugin`, `.cursor-plugin`),
  `evals/`, `test/`, `package.json` (dev-зависимости semantic-release), CI.
- Проверка перед установкой (2026-09-26): только Markdown, исполняемого кода нет;
  grep по сетевым вызовам, `eval`/`exec`/base64, `.ssh`/`.env`/`.aws` — пусто;
  текст прочитан целиком, вшитых инструкций нет. Коллизий имён с остальными
  скиллами, агентами и командами workflow нет.

## Обновление

```bash
git clone https://github.com/riekelt/technical-writer /tmp/tw
diff -r /tmp/tw/plugins/technical-writer/skills .claude/skills   # смотреть только 11 папок выше
```

Перед заменой — прочитать дифф целиком, обновить тег и коммит в разделе выше.
