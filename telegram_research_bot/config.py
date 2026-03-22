import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

BOT_TOKEN = os.getenv('BOT_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
CREDENTIALS_FILE = 'credentials.json'
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://example.com/test')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # https://USERNAME.pythonanywhere.com

# PythonAnywhere free tier требует proxy для исходящих запросов
PROXY_URL = os.getenv('PROXY_URL', '')  # http://proxy.server:3128

# Telegram ID администраторов
ADMIN_IDS = [
    123456789,  # замени на реальные ID
]

# Задержка напоминания после завершения теста (в минутах)
REMINDER_DELAY = 15

# Настройки кэширования вопросов (в секундах)
QUESTIONS_CACHE_TTL = 300  # 5 минут
