"""Модуль для работы с Google Sheets API.

Все данные исследования хранятся в Google Sheets.
Основной лист "Main" — данные пользователей и ответы.
Лист "Questions" — вопросы для тестирования.
Лист "Timers" — активные таймеры напоминаний.
"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Кэш вопросов
_questions_cache: list[dict] | None = None
_questions_cache_time: float = 0


def _get_client() -> gspread.Client:
    """Создать и вернуть авторизованный клиент gspread.

    Читает credentials из переменной окружения GOOGLE_CREDENTIALS (JSON-строка)
    или из файла credentials.json если переменная не задана.
    """
    google_creds_json = os.getenv('GOOGLE_CREDENTIALS')
    if google_creds_json:
        creds_dict = json.loads(google_creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            config.CREDENTIALS_FILE, scopes=SCOPES
        )
    return gspread.authorize(creds)


def _get_spreadsheet() -> gspread.Spreadsheet:
    """Получить объект таблицы."""
    client = _get_client()
    return client.open_by_key(config.SPREADSHEET_ID)


def _get_main_sheet() -> gspread.Worksheet:
    """Получить основной лист с данными пользователей."""
    return _get_spreadsheet().worksheet('Main')


def _get_questions_sheet() -> gspread.Worksheet:
    """Получить лист с вопросами."""
    return _get_spreadsheet().worksheet('Questions')


def _get_timers_sheet() -> gspread.Worksheet:
    """Получить лист с таймерами."""
    return _get_spreadsheet().worksheet('Timers')


# ===================== ПОЛЬЗОВАТЕЛИ =====================

def get_user_by_telegram_id(telegram_id: int) -> Optional[dict]:
    """Найти пользователя по telegram_id.

    Возвращает словарь с данными пользователя или None.
    telegram_id хранится в колонке unique_id рядом — ищем по отдельной колонке.
    Для идентификации используем telegram_login или telegram_phone.
    """
    sheet = _get_main_sheet()
    all_records = sheet.get_all_records()

    for i, record in enumerate(all_records):
        if str(record.get('telegram_id', '')) == str(telegram_id):
            record['_row_number'] = i + 2  # +2: заголовок + индекс с 0
            return record
    return None


def _generate_next_unique_id(sheet: gspread.Worksheet) -> str:
    """Сгенерировать следующий unique_id в формате km001, km002..."""
    all_values = sheet.col_values(1)  # колонка unique_id

    max_num = 0
    for val in all_values[1:]:  # пропускаем заголовок
        if val.startswith('km'):
            try:
                num = int(val[2:])
                if num > max_num:
                    max_num = num
            except ValueError:
                continue

    next_num = max_num + 1
    return f'km{next_num:03d}'


def create_new_user(telegram_id: int, username: Optional[str],
                    phone: Optional[str]) -> str:
    """Создать нового пользователя в таблице.

    Возвращает присвоенный unique_id.
    """
    sheet = _get_main_sheet()
    unique_id = _generate_next_unique_id(sheet)

    telegram_login = f'@{username}' if username else ''
    telegram_phone = phone or ''
    registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Получаем заголовки для определения количества колонок
    headers = sheet.row_values(1)
    row = [''] * len(headers)

    # Заполняем известные поля
    field_map = {
        'unique_id': unique_id,
        'telegram_id': str(telegram_id),
        'telegram_login': telegram_login,
        'telegram_phone': telegram_phone,
        'registration_date': registration_date,
        'website_completed': 'NO',
    }

    for field, value in field_map.items():
        if field in headers:
            row[headers.index(field)] = value

    # Находим первую пустую строку после заголовков
    first_col = sheet.col_values(1)  # колонка unique_id
    next_row = len(first_col) + 1
    # Проверяем, что не вставляем в строку с данными
    if next_row < 2:
        next_row = 2

    col_letter = _col_num_to_letter(len(headers))
    sheet.update(
        values=[row],
        range_name=f'A{next_row}:{col_letter}{next_row}',
        value_input_option='USER_ENTERED',
    )
    logger.info(f'Создан пользователь {unique_id} (telegram_id={telegram_id}) в строке {next_row}')
    return unique_id


def _col_num_to_letter(col: int) -> str:
    """Преобразовать номер колонки (1-based) в буквенное обозначение (A, B, ..., Z, AA, AB...)."""
    result = ''
    while col > 0:
        col, remainder = divmod(col - 1, 26)
        result = chr(65 + remainder) + result
    return result


def update_user_field(telegram_id: int, field_name: str, value: str) -> bool:
    """Обновить конкретное поле пользователя.

    Возвращает True при успехе.
    """
    sheet = _get_main_sheet()
    headers = sheet.row_values(1)

    if field_name not in headers:
        logger.error(f'Поле {field_name} не найдено в заголовках таблицы')
        return False

    col_index = headers.index(field_name) + 1  # gspread использует 1-based

    # Ищем строку по telegram_id
    all_records = sheet.get_all_records()
    for i, record in enumerate(all_records):
        if str(record.get('telegram_id', '')) == str(telegram_id):
            row_index = i + 2  # +2: заголовок + 0-based
            sheet.update_cell(row_index, col_index, value)
            logger.info(
                f'Обновлено поле {field_name}={value} '
                f'для telegram_id={telegram_id}'
            )
            return True

    logger.error(f'Пользователь с telegram_id={telegram_id} не найден')
    return False


def save_answer(telegram_id: int, question_number: int, answer: str) -> bool:
    """Сохранить ответ на вопрос.

    question_number — номер вопроса (1-30), ответ записывается в колонку question_N.
    """
    field_name = f'question_{question_number}'
    return update_user_field(telegram_id, field_name, answer)


def mark_website_completed(telegram_id: int) -> bool:
    """Установить website_completed = YES."""
    return update_user_field(telegram_id, 'website_completed', 'YES')


def get_user_progress(telegram_id: int) -> dict:
    """Определить прогресс пользователя.

    Возвращает словарь:
    - stage: 'new' | 'registration' | 'testing' | 'completed'
    - missing_fields: список незаполненных полей регистрации
    - last_answered_question: номер последнего отвеченного вопроса (0 если не начал)
    - unique_id: ID пользователя
    """
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return {'stage': 'new'}

    result = {'unique_id': user.get('unique_id', '')}

    # Проверяем заполненность полей регистрации
    reg_fields = ['name', 'age', 'gender', 'education', 'financial', 'region']
    missing = [f for f in reg_fields if not user.get(f)]

    if missing:
        result['stage'] = 'registration'
        result['missing_fields'] = missing
        return result

    # Все поля заполнены, но тестирование ещё не начато — нужно подтверждение
    if not user.get('test_start_time'):
        result['stage'] = 'registration'
        result['missing_fields'] = []
        return result

    # Проверяем прогресс тестирования
    last_answered = 0
    for i in range(1, 31):
        if user.get(f'question_{i}'):
            last_answered = i

    # Проверяем, завершён ли тест (есть test_end_time)
    if user.get('test_end_time'):
        result['stage'] = 'completed'
        result['last_answered_question'] = last_answered
        return result

    result['stage'] = 'testing'
    result['last_answered_question'] = last_answered
    return result


# ===================== ВОПРОСЫ =====================

def get_all_questions(force_refresh: bool = False) -> list[dict]:
    """Получить все активные вопросы из листа Questions.

    Использует кэширование (TTL = QUESTIONS_CACHE_TTL секунд).
    """
    global _questions_cache, _questions_cache_time

    now = time.time()
    if (not force_refresh and _questions_cache is not None
            and now - _questions_cache_time < config.QUESTIONS_CACHE_TTL):
        return _questions_cache

    sheet = _get_questions_sheet()
    all_records = sheet.get_all_records()

    questions = []
    for record in all_records:
        if str(record.get('is_active', '')).upper() == 'TRUE':
            questions.append({
                'question_id': record.get('question_id', ''),
                'question_text': record.get('question_text', ''),
                'question_type': record.get('question_type', ''),
                'options': record.get('options', ''),
                'order_number': int(record.get('order_number', 0)),
            })

    # Сортировка по order_number
    questions.sort(key=lambda q: q['order_number'])

    _questions_cache = questions
    _questions_cache_time = now
    logger.info(f'Загружено {len(questions)} активных вопросов')
    return questions


def get_all_questions_admin() -> list[dict]:
    """Получить ВСЕ вопросы (включая неактивные) для админки."""
    sheet = _get_questions_sheet()
    all_records = sheet.get_all_records()

    questions = []
    for i, record in enumerate(all_records):
        questions.append({
            'question_id': record.get('question_id', ''),
            'question_text': record.get('question_text', ''),
            'question_type': record.get('question_type', ''),
            'options': record.get('options', ''),
            'is_active': str(record.get('is_active', '')).upper() == 'TRUE',
            'order_number': int(record.get('order_number', 0)),
            '_row_number': i + 2,
        })

    questions.sort(key=lambda q: q['order_number'])
    return questions


def add_question(text: str, q_type: str, options: str = '') -> int:
    """Добавить новый вопрос.

    Возвращает присвоенный order_number.
    """
    global _questions_cache
    _questions_cache = None  # сбросить кэш

    sheet = _get_questions_sheet()
    all_records = sheet.get_all_records()

    # Определяем следующий question_id и order_number
    max_id = 0
    max_order = 0
    for record in all_records:
        try:
            qid = int(record.get('question_id', 0))
            if qid > max_id:
                max_id = qid
        except (ValueError, TypeError):
            pass
        try:
            order = int(record.get('order_number', 0))
            if order > max_order:
                max_order = order
        except (ValueError, TypeError):
            pass

    new_id = max_id + 1
    new_order = max_order + 1

    sheet.append_row(
        [new_id, text, q_type, options, 'TRUE', new_order],
        value_input_option='USER_ENTERED'
    )
    logger.info(f'Добавлен вопрос #{new_id}, order={new_order}')
    return new_order


def update_question(question_id: int, field: str, value: str) -> bool:
    """Обновить поле вопроса по question_id."""
    global _questions_cache
    _questions_cache = None

    sheet = _get_questions_sheet()
    headers = sheet.row_values(1)

    if field not in headers:
        return False

    col_index = headers.index(field) + 1
    all_records = sheet.get_all_records()

    for i, record in enumerate(all_records):
        if str(record.get('question_id', '')) == str(question_id):
            sheet.update_cell(i + 2, col_index, value)
            return True

    return False


def delete_question(question_id: int) -> bool:
    """Деактивировать вопрос (is_active = FALSE)."""
    return update_question(question_id, 'is_active', 'FALSE')


def activate_question(question_id: int) -> bool:
    """Активировать вопрос (is_active = TRUE)."""
    return update_question(question_id, 'is_active', 'TRUE')


def swap_question_order(question_id: int, direction: str) -> bool:
    """Переместить вопрос вверх или вниз.

    direction: 'up' или 'down'
    """
    global _questions_cache
    _questions_cache = None

    questions = get_all_questions_admin()

    # Найти текущий вопрос
    current = None
    current_idx = None
    for i, q in enumerate(questions):
        if str(q['question_id']) == str(question_id):
            current = q
            current_idx = i
            break

    if current is None:
        return False

    # Найти соседний вопрос
    if direction == 'up' and current_idx > 0:
        neighbor = questions[current_idx - 1]
    elif direction == 'down' and current_idx < len(questions) - 1:
        neighbor = questions[current_idx + 1]
    else:
        return False

    # Поменять order_number местами
    sheet = _get_questions_sheet()
    headers = sheet.row_values(1)
    order_col = headers.index('order_number') + 1

    sheet.update_cell(current['_row_number'], order_col, neighbor['order_number'])
    sheet.update_cell(neighbor['_row_number'], order_col, current['order_number'])

    return True


# ===================== ТАЙМЕРЫ =====================

def create_timer(telegram_id: int, unique_id: str) -> bool:
    """Создать запись таймера при переходе на сайт."""
    sheet = _get_timers_sheet()
    site_start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    sheet.append_row(
        [str(telegram_id), unique_id, site_start_time, 'NO', 'NO', 'NO'],
        value_input_option='USER_ENTERED'
    )
    return True


def get_timer(telegram_id: int) -> Optional[dict]:
    """Получить активный таймер пользователя."""
    sheet = _get_timers_sheet()
    all_records = sheet.get_all_records()

    for i, record in enumerate(all_records):
        if (str(record.get('telegram_id', '')) == str(telegram_id)
                and str(record.get('completed', '')).upper() != 'YES'):
            record['_row_number'] = i + 2
            return record
    return None


def update_timer_field(telegram_id: int, field: str, value: str) -> bool:
    """Обновить поле таймера."""
    sheet = _get_timers_sheet()
    headers = sheet.row_values(1)

    if field not in headers:
        return False

    col_index = headers.index(field) + 1
    all_records = sheet.get_all_records()

    for i, record in enumerate(all_records):
        if (str(record.get('telegram_id', '')) == str(telegram_id)
                and str(record.get('completed', '')).upper() != 'YES'):
            sheet.update_cell(i + 2, col_index, value)
            return True
    return False


# ===================== СТАТИСТИКА =====================

def get_statistics() -> dict:
    """Получить статистику для админ-панели."""
    sheet = _get_main_sheet()
    all_records = sheet.get_all_records()

    total = len(all_records)
    completed_test = sum(1 for r in all_records if r.get('test_end_time'))
    completed_site = sum(
        1 for r in all_records
        if str(r.get('website_completed', '')).upper() == 'YES'
    )

    questions = get_all_questions()
    active_questions = len(questions)

    return {
        'total_users': total,
        'completed_test': completed_test,
        'completed_site': completed_site,
        'active_questions': active_questions,
    }
