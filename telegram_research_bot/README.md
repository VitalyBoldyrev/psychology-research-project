# Telegram-бот для психологического исследования логического мышления

Бот для проведения психологического исследования среди студентов. Собирает демографические данные, проводит тестирование с задачами на логику, сохраняет все данные в Google Sheets и выдаёт логин для прохождения второй части на внешнем сайте.

## Возможности

- Регистрация пользователей с сохранением в Google Sheets
- Тестирование с 3 типами вопросов (числовой ввод, выбор варианта, да/нет)
- Административная панель для управления вопросами и просмотра статистики
- Система таймеров и напоминаний (30, 45, 60 минут)
- Генерация уникальных ID в формате `km001`, `km002` и т.д.

## Установка

### 1. Создание Telegram-бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Введите имя бота и username
4. Скопируйте токен бота (формат: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Настройка Google Sheets API

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект (или выберите существующий)
3. Включите **Google Sheets API**:
   - Перейдите в APIs & Services → Library
   - Найдите "Google Sheets API" и нажмите Enable
4. Создайте **Service Account**:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Заполните имя и нажмите Create
   - Пропустите шаги 2 и 3, нажмите Done
5. Создайте **JSON-ключ**:
   - Нажмите на созданный Service Account
   - Keys → Add Key → Create New Key → JSON
   - Скачайте файл и переименуйте в `credentials.json`
   - Поместите в корневую папку проекта (`telegram_research_bot/`)
6. Создайте **Google Sheets таблицу**:
   - Создайте новую таблицу в Google Sheets
   - Скопируйте ID таблицы из URL: `https://docs.google.com/spreadsheets/d/ЭТОТ_ID/edit`
   - Предоставьте доступ (редактор) для email Service Account (находится в JSON-ключе, поле `client_email`)

### 3. Установка зависимостей

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### 4. Настройка конфигурации

```bash
# Скопируйте пример .env
cp .env.example .env
```

Отредактируйте файл `.env`:
```env
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
SPREADSHEET_ID=ваш_id_google_sheets_таблицы
WEBSITE_URL=https://example.com/test
```

Отредактируйте `config.py` — укажите Telegram ID администраторов:
```python
ADMIN_IDS = [
    123456789,  # ваш Telegram ID
]
```

> Узнать свой Telegram ID можно через бота [@userinfobot](https://t.me/userinfobot)

### 5. Начальное заполнение данных

```bash
python seed_questions.py
```

Этот скрипт:
- Создаст листы "Main", "Questions" и "Timers" в таблице (если не существуют)
- Заполнит лист "Questions" 10 примерами вопросов разных типов
- Настроит заголовки всех листов

### 6. Запуск бота

```bash
python bot.py
```

## Структура проекта

```
telegram_research_bot/
├── bot.py                  # Главный файл запуска
├── config.py               # Конфигурация
├── sheets_manager.py       # Работа с Google Sheets API
├── states.py               # FSM состояния
├── seed_questions.py       # Скрипт заполнения вопросов
├── handlers/
│   ├── start.py            # Регистрация (/start)
│   ├── testing.py          # Тестирование
│   ├── admin.py            # Админ-панель (/admin)
│   ├── timers.py           # Таймеры и напоминания
│   └── common.py           # Общие хэндлеры
├── keyboards/
│   ├── user_kb.py          # Клавиатуры пользователей
│   └── admin_kb.py         # Клавиатуры админов
├── utils/
│   ├── validators.py       # Валидация данных
│   └── formatters.py       # Форматирование сообщений
├── credentials.json        # JSON-ключ (НЕ коммитить!)
├── .env                    # Переменные окружения (НЕ коммитить!)
├── .env.example            # Шаблон .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Команды бота

### Для пользователей
- `/start` — начать регистрацию и тестирование

### Для администраторов
- `/admin` — открыть панель администратора
  - Управление вопросами (добавление, редактирование, деактивация)
  - Статистика (количество зарегистрированных, завершивших тест)
  - Экспорт данных (ссылка на Google Sheets)

## Примеры вопросов

| # | Текст вопроса | Тип |
|---|--------------|-----|
| 1 | Даны 3 шара разного цвета. Сколько пар шаров разного цвета можно составить? | Выбор (2, 3, 4, 6) |
| 2 | Если все розы — цветы, а все цветы — растения, верно ли, что все розы — растения? | Да/Нет |
| 3 | В комнате 4 угла. В каждом углу сидит кошка... Сколько всего кошек? | Число |
| 4 | Какое число продолжает последовательность: 2, 6, 12, 20, ...? | Выбор (24, 28, 30, 32) |
| 5 | Некоторые студенты являются спортсменами... | Да/Нет |

## Структура Google Sheets

### Лист "Main"
Основные данные пользователей: `unique_id`, `telegram_id`, `telegram_login`, `telegram_phone`, `name`, `age`, `education`, `question_1`...`question_30`, `website_completed`, `registration_date`, `test_start_time`, `test_end_time`

### Лист "Questions"
Вопросы: `question_id`, `question_text`, `question_type`, `options`, `is_active`, `order_number`

### Лист "Timers"
Таймеры: `telegram_id`, `unique_id`, `site_start_time`, `first_reminder_sent`, `second_reminder_sent`, `completed`
