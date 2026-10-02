---
use-when:
  - bash:/deploy(-[a-z0-9_-]+)?\.sh|pm2 (restart|reload)|systemctl (restart|reload|start|enable)/i
# Контроль: ловит `deploy.sh` и `deploy-<name>.sh`, `pm2 restart|reload`, `systemctl restart`
# (сервисы на systemd).
---
Деплой в прод: перед выкаткой прогнать `/prod-review` по диффу и чеклист `ENGINEERING.md` §8 (идемпотентность повторного запуска, лок cron, метрика на поломку, бэкап, откат). Проверить, что очередь пуста (`in_progress == 0`) — рестарт в середине pipeline рвёт работу между доставкой результата и маркером «готово».
