---
use-when:
  - bash:/(tasks?\.(task\.)?(add|create|update)|crm\.[a-z]+\.(add|update|set)|timeline\.comment\.add|sendMessage|messages\/send)/i
  - edit:**/*crm*.py
  - edit:**/*messag*.py
  - edit:**/*telegram*.py
# Контроль: срабатывает на crm.item.update, crm.deal.add, tasks.task.update, sendMessage;
# молчит на crm.item.get, crm.item.list. Перечислите здесь имена клиентов своих внешних API.
---
Запись наружу (задача/сделка/комментарий в CRM, сообщение клиенту через мессенджер) обязана быть идемпотентной: natural key или таблица/файл `processed_*` с уникальным ограничением, статус в БД, а не в памяти процесса — рестарт процесса и повторная доставка вебхука иначе дают дубль клиенту. Ретраить такое без ключа дедупа нельзя. Детали: ENGINEERING.md §2.
