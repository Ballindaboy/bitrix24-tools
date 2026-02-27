# Bitrix24 Assistant

**Назначение:** Контекстный поиск и анализ данных Bitrix24 для принятия решений.

---

## Данные

Снапшоты Bitrix24 хранятся в `snapshots/`:

| Файл | Содержимое |
|------|------------|
| `deals.json` | Сделки CRM |
| `tasks.json` | Задачи |
| `task_comments.json` | Комментарии к задачам |
| `calendar.json` | События календаря |
| `activity.json` | Активность (звонки, письма, встречи) |
| `chats.json` | Чаты и сообщения |
| `calls.json` | Звонки (Voximplant) |
| `contacts.json` | Контакты CRM |
| `companies.json` | Компании |
| `users.json` | Сотрудники |

---

## Как работать

### Поиск информации

При вопросах о сделках, задачах, клиентах — читай соответствующий снапшот:

```
Пользователь: "Какие сделки сейчас в работе?"
→ Читай snapshots/deals.json, фильтруй по stage

Пользователь: "Что по задачам на этой неделе?"
→ Читай snapshots/tasks.json, фильтруй по deadline

Пользователь: "История общения с клиентом X"
→ Ищи в contacts.json, activity.json, chats.json
```

### Обновление данных

Данные обновляются автоматически каждый час. Для ручного обновления:

```bash
python collect.py --quick   # Быстрый сбор (~3 мин)
python collect.py --all     # Полный сбор (~10 мин)
```

---

## Ссылки на Bitrix24

При упоминании сделки/задачи — давай ссылку:

- Задача: `https://ulyanovsk.bitrix24.ru/company/personal/user/1/tasks/task/view/{ID}/`
- Сделка: `https://ulyanovsk.bitrix24.ru/crm/deal/details/{ID}/`
- Контакт: `https://ulyanovsk.bitrix24.ru/crm/contact/details/{ID}/`

---

## Правила

1. **Только факты** — данные из снапшотов, без домыслов
2. **Актуальность** — если данные важны, предложи обновить снапшоты
3. **Конкретика** — имена, суммы, даты, ссылки

---

**Компания:** TEXDAR | **Домен:** ulyanovsk.bitrix24.ru
