"""Скрипт для начального заполнения листа Questions примерами вопросов.

Запуск: python seed_questions.py

Перед запуском убедитесь, что:
1. Файл credentials.json существует
2. В .env указан SPREADSHEET_ID
3. В Google Sheets создан лист "Questions" с заголовками:
   question_id | question_text | question_type | options | is_active | order_number
"""

import gspread
from google.oauth2.service_account import Credentials
import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Примеры вопросов разных типов
SAMPLE_QUESTIONS = [
    {
        'question_id': 1,
        'question_text': 'Даны 3 шара разного цвета. Сколько пар шаров разного цвета можно составить?',
        'question_type': 'choice',
        'options': '2|3|4|6',
        'is_active': 'TRUE',
        'order_number': 1,
    },
    {
        'question_id': 2,
        'question_text': 'Если все розы — цветы, а все цветы — растения, верно ли, что все розы — растения?',
        'question_type': 'yesno',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 2,
    },
    {
        'question_id': 3,
        'question_text': 'В комнате 4 угла. В каждом углу сидит кошка. Напротив каждой кошки сидят по 3 кошки. Сколько всего кошек в комнате?',
        'question_type': 'number',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 3,
    },
    {
        'question_id': 4,
        'question_text': 'Какое число продолжает последовательность: 2, 6, 12, 20, ...?',
        'question_type': 'choice',
        'options': '24|28|30|32',
        'is_active': 'TRUE',
        'order_number': 4,
    },
    {
        'question_id': 5,
        'question_text': 'Некоторые студенты являются спортсменами. Все спортсмены здоровы. Верно ли, что некоторые студенты здоровы?',
        'question_type': 'yesno',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 5,
    },
    {
        'question_id': 6,
        'question_text': 'У Пети есть 5 пар носков. Сколько минимум носков нужно достать из ящика в темноте, чтобы гарантированно получить пару одного цвета?',
        'question_type': 'number',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 6,
    },
    {
        'question_id': 7,
        'question_text': 'Все металлы проводят электричество. Медь — металл. Что можно заключить?',
        'question_type': 'choice',
        'options': 'Медь проводит электричество|Медь не проводит электричество|Нельзя сделать вывод|Медь — не металл',
        'is_active': 'TRUE',
        'order_number': 7,
    },
    {
        'question_id': 8,
        'question_text': 'Если А больше Б, а Б больше В, верно ли, что А больше В?',
        'question_type': 'yesno',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 8,
    },
    {
        'question_id': 9,
        'question_text': 'Сколько треугольников на рисунке, если большой треугольник разделён на 4 маленьких треугольника одной горизонтальной линией и одной вертикальной?',
        'question_type': 'number',
        'options': '',
        'is_active': 'TRUE',
        'order_number': 9,
    },
    {
        'question_id': 10,
        'question_text': 'Какой из выводов логически следует из утверждения: "Ни один кот не умеет летать"?',
        'question_type': 'choice',
        'options': 'Все летающие — не коты|Некоторые коты умеют летать|Все коты умеют летать|Некоторые летающие — коты',
        'is_active': 'TRUE',
        'order_number': 10,
    },
]


def seed():
    """Заполнить лист Questions начальными данными."""
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(config.SPREADSHEET_ID)

    # Получаем или создаём лист Questions
    try:
        sheet = spreadsheet.worksheet('Questions')
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(
            title='Questions', rows=100, cols=6
        )

    # Устанавливаем заголовки
    headers = [
        'question_id', 'question_text', 'question_type',
        'options', 'is_active', 'order_number',
    ]
    sheet.update(values=[headers], range_name='A1:F1', value_input_option='USER_ENTERED')

    # Добавляем вопросы
    rows = []
    for q in SAMPLE_QUESTIONS:
        rows.append([
            q['question_id'],
            q['question_text'],
            q['question_type'],
            q['options'],
            q['is_active'],
            q['order_number'],
        ])

    if rows:
        sheet.update(
            values=rows,
            range_name=f'A2:F{len(rows) + 1}',
            value_input_option='USER_ENTERED',
        )

    print(f'✅ Загружено {len(rows)} вопросов в лист "Questions"')

    # Создаём лист Main (если не существует)
    try:
        spreadsheet.worksheet('Main')
        print('Лист "Main" уже существует')
    except gspread.exceptions.WorksheetNotFound:
        main_sheet = spreadsheet.add_worksheet(
            title='Main', rows=1000, cols=50
        )
        # Заголовки основного листа
        main_headers = [
            'unique_id', 'telegram_id', 'telegram_login', 'telegram_phone',
            'name', 'age', 'education',
        ]
        # Добавляем колонки question_1 ... question_30
        for i in range(1, 31):
            main_headers.append(f'question_{i}')
        main_headers.extend([
            'website_completed', 'registration_date',
            'test_start_time', 'test_end_time',
        ])

        col_letter = chr(ord('A') + len(main_headers) - 1)
        if len(main_headers) > 26:
            first = chr(ord('A') + (len(main_headers) - 1) // 26 - 1)
            second = chr(ord('A') + (len(main_headers) - 1) % 26)
            col_letter = first + second

        main_sheet.update(
            f'A1:{col_letter}1',
            [main_headers],
            value_input_option='USER_ENTERED',
        )
        print(f'✅ Создан лист "Main" с {len(main_headers)} колонками')

    # Создаём лист Timers (если не существует)
    try:
        spreadsheet.worksheet('Timers')
        print('Лист "Timers" уже существует')
    except gspread.exceptions.WorksheetNotFound:
        timers_sheet = spreadsheet.add_worksheet(
            title='Timers', rows=1000, cols=6
        )
        timer_headers = [
            'telegram_id', 'unique_id', 'site_start_time',
            'first_reminder_sent', 'second_reminder_sent', 'completed',
        ]
        timers_sheet.update(
            'A1:F1', [timer_headers], value_input_option='USER_ENTERED'
        )
        print('✅ Создан лист "Timers"')


if __name__ == '__main__':
    seed()
