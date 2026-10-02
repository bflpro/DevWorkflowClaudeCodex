# build-route — лёгкий маршрут `/build`

<!-- readme-check: skip — скилл-инструкция, ничего не исполняет сам; поток и проверки описаны в SKILL.md -->

Скилл команды `/build`: короткая разведка кода субагентами, порог размера из `ENGINEERING.md` §1a,
и либо oneshot (карточка `work/quick-<slug>/tasks/1.md`, код в той же сессии, quick-линза,
триаж лидом, квитанция `task-accept.py`), либо передача в `/new-user-spec` / `/new-tech-spec`
с сохранённой разведкой.

Файлы:

- `SKILL.md` — шаги маршрута;
- `references/plan-template.md` — карточка oneshot, совместимая с шаблоном задачи (квитанция без правки скриптов);
- `.claude/shared/review-lenses/quick.md` — промпт единственной ревью-линзы;
- `.claude/shared/review-lenses/triage.md` — как лид разбирает находки.

## Откуда взято

Маршрут «разведка → порог → oneshot / full», карточка с замороженным Intent, quick-линза без
серьёзности и триаж с вердиктами `high / medium / low / false / maybe-false` — из
[bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) @ `1cbcfa2`
(28.09.2026, MIT): `skills/bmad-build/{customize.toml,step-01-clarify-and-route.md,step-02-plan.md,step-oneshot.md,step-04-review.md,plan-template.md}`.
Код BMAD (`render_skill.py`, `tickets.py`, `uv`) не переносился.

Что изменено в этом workflow: пороги «запись наружу», «юнит на сервере», «промпт в проде», уровень L
(`ENGINEERING.md` §2); карточка в формате шаблона задачи этого workflow, чтобы работали `owns-check.py`,
`findings-sync.py`, `task-accept.py`; маршруты триажа сведены к `patch / ask / defer`
(у BMAD `intent_gap` и `bad_plan` переделывают код по плану — в oneshot план и есть карточка);
условная security-линза (у BMAD её нет); Prod Gate и закрывающий блок из `ENGINEERING.md` §2 и §6.5.
