---
use-when:
  - bash:/crontab|pm2 start .*cron|schedule\.(every|add_job)|systemctl (enable|start|restart|reload|edit) .*\.timer/i
  - edit:**/cron*.py
  - edit:**/scheduler*.py
  - edit:**/*.timer
# Контроль: ловит и таймеры systemd (`systemctl enable --now x.timer`, правка `deploy/*.timer`) —
# расписание часто живёт именно там, а не в crontab.
---
Cron/фоновый цикл: лок от параллельного запуска (flock / файл-лок / строка с TTL) + таймаут на итерацию. Прошлый прогон мог не завершиться — без лока два процесса дублируют действия наружу. Детали: ENGINEERING.md §2. Перезапуск по расписанию как лечение утечки или гонки — маскировка дефекта: чини причину.
