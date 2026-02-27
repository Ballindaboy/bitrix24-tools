# Bitrix24 Tools

Сбор данных из Bitrix24 для работы с Claude Code.

---

## Установка (один раз)

### 1. Клонировать репозиторий

```bash
cd ~/Projects
git clone https://github.com/nailmusin/bitrix24-tools.git
cd bitrix24-tools
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Настроить Bitrix24 webhook

Создай файл `.env` (скопируй из примера):

```bash
cp .env.example .env
```

Открой `.env` и вставь свой webhook:

```
BITRIX_WEBHOOK_URL=https://ulyanovsk.bitrix24.ru/rest/ТВОЙ_USER_ID/ТВОЙ_WEBHOOK_CODE/
```

**Как получить webhook:**
1. Bitrix24 → Приложения → Вебхуки
2. Добавить вебхук → Входящий вебхук
3. Выбрать права: CRM, Задачи, Календарь, Чаты, Пользователи
4. Скопировать URL

### 4. Первый сбор данных

```bash
source venv/bin/activate
python collect.py --all
```

Данные появятся в папке `snapshots/`.

---

## Ежедневное использование

### Обновить данные

```bash
cd ~/Projects/bitrix24-tools
source venv/bin/activate
python collect.py --quick
```

### Обновить код (когда сказали)

```bash
cd ~/Projects/bitrix24-tools
git pull
```

---

## Работа с Claude Code

```bash
cd ~/Projects/bitrix24-tools
claude
```

Теперь можно спрашивать:
- "Какие сделки в работе?"
- "Что по задачам на этой неделе?"
- "Покажи активность по клиенту X"

---

## Автоматический сбор (опционально)

Чтобы данные обновлялись каждый час автоматически:

```bash
crontab -e
```

Добавить строку:
```
0 * * * * cd ~/Projects/bitrix24-tools && ./venv/bin/python collect.py --hourly >> /tmp/bitrix-collect.log 2>&1
```

---

## Структура

```
bitrix24-tools/
├── collect.py          # Скрипт сбора данных
├── snapshots/          # Данные Bitrix24 (JSON)
├── collectors/         # Модули сбора
├── shared/             # Общие библиотеки
├── .env                # Твой webhook (не в git!)
└── CLAUDE.md           # Инструкции для ассистента
```
