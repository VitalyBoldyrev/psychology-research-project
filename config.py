import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
CREDENTIALS_FILE = 'credentials.json'
WEBSITE_URL = os.getenv('WEBSITE_URL', 'https://example.com/test')

# Telegram ID администраторов
ADMIN_IDS = [
    123456789,  # замени на реальные ID
]

# Настройки таймеров (в минутах)
FIRST_REMINDER = 30
SECOND_REMINDER = 45
FINAL_MESSAGE = 60

# Настройки кэширования вопросов (в секундах)
QUESTIONS_CACHE_TTL = 300  # 5 минут
