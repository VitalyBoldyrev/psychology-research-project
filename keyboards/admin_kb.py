"""Клавиатуры для административной панели."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_menu() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='📝 Управление вопросами', callback_data='admin_questions')],
        [InlineKeyboardButton(
            text='📊 Статистика', callback_data='admin_stats')],
        [InlineKeyboardButton(
            text='⬇️ Экспорт данных', callback_data='admin_export')],
    ])


def questions_menu() -> InlineKeyboardMarkup:
    """Меню управления вопросами."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='➕ Добавить новый вопрос',
            callback_data='admin_add_question')],
        [InlineKeyboardButton(
            text='📋 Список всех вопросов',
            callback_data='admin_list_questions_0')],
        [InlineKeyboardButton(
            text='◀️ Назад в главное меню',
            callback_data='admin_main')],
    ])


def questions_list_keyboard(
    questions: list[dict], page: int = 0, per_page: int = 5
) -> InlineKeyboardMarkup:
    """Список вопросов с пагинацией и кнопками управления."""
    total_pages = max(1, (len(questions) + per_page - 1) // per_page)
    start = page * per_page
    end = min(start + per_page, len(questions))

    buttons = []

    for q in questions[start:end]:
        status = '✅' if q['is_active'] else '❌'
        text_preview = q['question_text'][:40]
        if len(q['question_text']) > 40:
            text_preview += '...'

        buttons.append([InlineKeyboardButton(
            text=f"{q['order_number']}. {status} {text_preview}",
            callback_data=f"admin_edit_q_{q['question_id']}"
        )])

    # Навигация по страницам
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text='⬅️ Пред', callback_data=f'admin_list_questions_{page - 1}'
        ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text='➡️ След', callback_data=f'admin_list_questions_{page + 1}'
        ))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(
        text='◀️ Назад', callback_data='admin_questions'
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def question_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа вопроса при добавлении."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🔢 Число', callback_data='qtype_number')],
        [InlineKeyboardButton(
            text='📋 Выбор варианта', callback_data='qtype_choice')],
        [InlineKeyboardButton(
            text='✅❌ Да/Нет', callback_data='qtype_yesno')],
        [InlineKeyboardButton(
            text='◀️ Отмена', callback_data='admin_questions')],
    ])


def edit_question_keyboard(question: dict) -> InlineKeyboardMarkup:
    """Кнопки редактирования вопроса."""
    buttons = [
        [InlineKeyboardButton(
            text='✏️ Изменить текст',
            callback_data=f"editq_text_{question['question_id']}")],
        [InlineKeyboardButton(
            text='🔄 Изменить тип',
            callback_data=f"editq_type_{question['question_id']}")],
    ]

    if question['question_type'] == 'choice':
        buttons.append([InlineKeyboardButton(
            text='📝 Изменить варианты',
            callback_data=f"editq_options_{question['question_id']}"
        )])

    buttons.extend([
        [InlineKeyboardButton(
            text='⬆️ Переместить выше',
            callback_data=f"editq_up_{question['question_id']}")],
        [InlineKeyboardButton(
            text='⬇️ Переместить ниже',
            callback_data=f"editq_down_{question['question_id']}")],
    ])

    if question['is_active']:
        buttons.append([InlineKeyboardButton(
            text='❌ Деактивировать',
            callback_data=f"editq_deactivate_{question['question_id']}"
        )])
    else:
        buttons.append([InlineKeyboardButton(
            text='✅ Активировать',
            callback_data=f"editq_activate_{question['question_id']}"
        )])

    buttons.append([InlineKeyboardButton(
        text='◀️ Назад', callback_data='admin_list_questions_0'
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_delete_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления (деактивации) вопроса."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Да', callback_data=f'confirm_del_{question_id}'),
            InlineKeyboardButton(
                text='Нет', callback_data=f'admin_edit_q_{question_id}'),
        ],
    ])


def back_to_admin() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню админки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='◀️ Назад', callback_data='admin_main')],
    ])
