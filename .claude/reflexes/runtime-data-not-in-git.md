---
use-when:
  - bash:/git add (.*(data\/|\.log\b|state\.json|\.env\b)|(-A|--all|\.)(\s|$))/
# Контроль: ловит и `git add -A` / `git add .` — runtime-данные попадают в индекс именно через них,
# а не через явный путь.
---
Runtime-данные (data/, логи, state-файлы) и .env в git не коммитим — им место в .gitignore. Проверь состав `git add`: только код, конфиг-шаблоны (.env.example) и доки.
