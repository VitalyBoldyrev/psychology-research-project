"""Клавиатуры для пользователей."""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def phone_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса номера телефона."""
    button = KeyboardButton(
        text='📱 Поделиться номером телефона',
        request_contact=True
    )
    return ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def education_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопки для выбора уровня образования."""
    buttons = [
        [InlineKeyboardButton(
            text='Среднее общее', callback_data='edu_secondary')],
        [InlineKeyboardButton(
            text='Среднее специальное', callback_data='edu_vocational')],
        [InlineKeyboardButton(
            text='Неполное высшее', callback_data='edu_incomplete_higher')],
        [InlineKeyboardButton(
            text='Высшее', callback_data='edu_higher')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Маппинг callback_data → текст образования
EDUCATION_MAP = {
    'edu_secondary': 'Среднее общее',
    'edu_vocational': 'Среднее специальное',
    'edu_incomplete_higher': 'Неполное высшее',
    'edu_higher': 'Высшее',
}


def gender_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопки для выбора пола."""
    buttons = [
        [InlineKeyboardButton(text='Мужской', callback_data='gender_male')],
        [InlineKeyboardButton(text='Женский', callback_data='gender_female')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


GENDER_MAP = {
    'gender_male': 'Мужской',
    'gender_female': 'Женский',
}


def financial_keyboard() -> InlineKeyboardMarkup:
    """Inline-кнопки для оценки финансового положения."""
    buttons = [
        [InlineKeyboardButton(
            text='Денег не хватает даже на питание',
            callback_data='fin_1')],
        [InlineKeyboardButton(
            text='На питание хватает, но покупка одежды затруднительна',
            callback_data='fin_2')],
        [InlineKeyboardButton(
            text='На питание и одежду хватает, но покупка крупной бытовой техники затруднительна',
            callback_data='fin_3')],
        [InlineKeyboardButton(
            text='Можем позволить крупную бытовую технику, но не новый автомобиль',
            callback_data='fin_4')],
        [InlineKeyboardButton(
            text='Можем позволить себе всё, кроме дорогих приобретений (квартира, дом)',
            callback_data='fin_5')],
        [InlineKeyboardButton(
            text='Можем позволить себе всё, что захотим',
            callback_data='fin_6')],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


FINANCIAL_MAP = {
    'fin_1': 'Денег не хватает даже на питание',
    'fin_2': 'На питание хватает, но покупка одежды затруднительна',
    'fin_3': 'На питание и одежду хватает, но покупка крупной бытовой техники затруднительна',
    'fin_4': 'Можем позволить крупную бытовую технику, но не новый автомобиль',
    'fin_5': 'Можем позволить себе всё, кроме дорогих приобретений (квартира, дом)',
    'fin_6': 'Можем позволить себе всё, что захотим',
}


def confirmation_keyboard() -> InlineKeyboardMarkup:
    """Кнопки подтверждения / изменения данных регистрации."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='✅ Подтвердить', callback_data='reg_confirm')],
        [InlineKeyboardButton(
            text='✏️ Изменить', callback_data='reg_edit')],
    ])


def back_button_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Назад' для навигации при регистрации."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='◀️ Назад', callback_data='reg_back')],
    ])


def question_choice_keyboard(
    options: list[str], show_back: bool = True
) -> InlineKeyboardMarkup:
    """Inline-кнопки с вариантами ответа на вопрос."""
    buttons = []
    for i, option in enumerate(options):
        buttons.append([InlineKeyboardButton(
            text=option, callback_data=f'ans_c_{i}'
        )])

    if show_back:
        buttons.append([InlineKeyboardButton(
            text='◀️ Изменить предыдущий ответ',
            callback_data='test_back'
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def question_text_keyboard(show_back: bool = True) -> InlineKeyboardMarkup:
    """Кнопка 'Назад' при вводе текстового ответа."""
    if not show_back:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='◀️ Изменить предыдущий ответ',
            callback_data='test_back'
        )],
    ])


def website_button(url: str) -> InlineKeyboardMarkup:
    """Кнопка перехода на сайт."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='🌐 Перейти на сайт', url=url)],
    ])


def reminder_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для напоминания (Завершил / Ещё прохожу)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text='✅ Завершил', callback_data='site_completed'),
            InlineKeyboardButton(
                text='⏳ Еще прохожу', callback_data='site_in_progress'),
        ],
    ])


def final_completed_keyboard() -> InlineKeyboardMarkup:
    """Кнопка 'Завершил' для финального сообщения."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='✅ Завершил', callback_data='site_completed')],
    ])


def resume_testing_keyboard() -> InlineKeyboardMarkup:
    """Кнопки для возобновления тестирования."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='✅ Продолжить', callback_data='resume_test')],
        [InlineKeyboardButton(
            text='🔄 Начать заново', callback_data='restart_test')],
    ])


REMOVE_KEYBOARD = ReplyKeyboardRemove()
