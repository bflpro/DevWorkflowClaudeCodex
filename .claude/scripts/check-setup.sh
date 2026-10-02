#!/usr/bin/env bash
# Диагностика установленного workflow в проекте.
# Ничего НЕ меняет — только сообщает о расхождениях. Запускать после установки
# и когда «правило из репо почему-то не срабатывает».
#
#   bash .claude/scripts/check-setup.sh
#
# Зачем: хуки, рефлексы и гейты срабатывают молча или не срабатывают вовсе —
# без node хук рефлексов не запустится, без файла скрипта хук упадёт.

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ok=0; warn=0; err=0

green() { printf '  \033[32m✅\033[0m %s\n' "$1"; ok=$((ok+1)); }
yellow() { printf '  \033[33m⚠️\033[0m  %s\n' "$1"; warn=$((warn+1)); }
red() { printf '  \033[31m❌\033[0m %s\n' "$1"; err=$((err+1)); }

echo
echo "Диагностика workflow — $REPO_DIR"
echo

echo "1. Интерпретаторы"
if command -v node >/dev/null 2>&1; then
  green "node $(node --version) — рефлексы будут срабатывать"
else
  red "node не найден — рефлексы (.claude/reflexes/) НЕ будут срабатывать. Поставь Node.js"
fi
if command -v python3 >/dev/null 2>&1; then
  green "$(python3 --version 2>&1) — гейты и проверки запускаются"
else
  red "python3 не найден — check-readme, task-accept, owns-check и другие гейты не запустятся"
fi

echo
echo "2. Хуки в .claude/settings.json"
SETTINGS="$REPO_DIR/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  green "settings.json на месте"
  for hook in reflex-check.mjs post-compact-restore.sh; do
    if grep -q "$hook" "$SETTINGS" 2>/dev/null; then
      if [ -f "$REPO_DIR/.claude/scripts/$hook" ]; then
        green "хук $hook настроен, файл на месте"
      else
        red "settings.json ссылается на .claude/scripts/$hook, а файла нет — хук будет падать"
      fi
    else
      yellow "хук $hook не настроен в settings.json"
    fi
  done
else
  red "нет .claude/settings.json — хуки не настроены"
fi

echo
echo "3. Скрипты и правила"
for f in .claude/scripts/check-readme.py .claude/scripts/check-techspec-readiness.py \
         .claude/scripts/task-accept.py .claude/scripts/owns-check.py \
         .claude/scripts/wave-check.py .claude/scripts/findings-sync.py \
         .claude/scripts/scan-staged-secrets.py; do
  if [ -f "$REPO_DIR/$f" ]; then green "$f"; else red "$f — отсутствует, переустанови workflow"; fi
done
if [ -f "$REPO_DIR/ENGINEERING.md" ]; then
  green "ENGINEERING.md"
elif [ -f "$REPO_DIR/templates/ENGINEERING.md" ]; then
  yellow "ENGINEERING.md только в templates/ — это репозиторий самого workflow, а не проект"
else
  red "ENGINEERING.md — отсутствует, скопируй templates/ENGINEERING.md в корень проекта"
fi
n_reflexes="$(ls "$REPO_DIR"/.claude/reflexes/*.md 2>/dev/null | grep -v '/README\.md$' | wc -l | tr -d ' ')"
green "рефлексов: $n_reflexes"

echo
echo "4. Зеркало для Codex"
if [ -d "$REPO_DIR/.codex" ] && [ -f "$REPO_DIR/.codex/sync-workflow.py" ]; then
  if (cd "$REPO_DIR" && python3 .codex/sync-workflow.py --check >/dev/null 2>&1); then
    green ".codex совпадает с .claude"
  else
    yellow ".codex расходится с .claude — подробности:
        python3 .codex/sync-workflow.py --check"
  fi
else
  green ".codex не установлен — пропуск"
fi

echo
printf 'Итого: ✅ %d   ⚠️  %d   ❌ %d\n' "$ok" "$warn" "$err"
[ "$err" -gt 0 ] && echo "Красные пункты чинить обязательно — без них правила workflow не работают."
echo
exit 0
