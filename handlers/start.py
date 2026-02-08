"""Хэндлер /start и регистрация пользователя.

Сценарий:
1. Приветствие
2. Получение username или запрос телефона
3. Запрос имени
4. Запрос возраста (14-100)
5. Выбор образования
6. Переход к тестированию
"""

import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

import sheets_manager
from states import Registration, Testing
from keyboards.user_kb import (
    phone_keyboard,
    education_keyboard,
    back_button_keyboard,
    resume_testing_keyboard,
    website_button,
    EDUCATION_MAP,
    REMOVE_KEYBOARD,
)
from utils.validators import validate_name, validate_age
import config

logger = logging.getLogger(__name__)
router = Router()

# Мьютексы для защиты от параллельных /start от одного пользователя
_user_locks: dict[int, asyncio.Lock] = {}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start."""
    telegram_id = message.from_user.id
    username = message.from_user.username

    # Защита от параллельных запросов от одного пользователя
    if telegram_id not in _user_locks:
        _user_locks[telegram_id] = asyncio.Lock()
    lock = _user_locks[telegram_id]

    if lock.locked():
        return

    async with lock:
        await message.answer('⏳ Подождите, готовлю задачи...')
        await _handle_start(message, state, telegram_id, username)


async def _handle_start(message: Message, state: FSMContext, telegram_id: int, username: str | None):
    """Основная логика /start (выполняется под мьютексом)."""
    # Проверяем, есть ли пользователь в таблице
    try:
        progress = sheets_manager.get_user_progress(telegram_id)
    except Exception as e:
        logger.error(f'Ошибка при проверке пользователя: {e}', exc_info=True)
        await message.answer(
            '❌ Произошла ошибка при подключении к базе данных. '
            'Попробуйте позже.'
        )
        return

    stage = progress.get('stage', 'new')

    if stage == 'new':
        # Новый пользователь — начинаем регистрацию
        await _start_registration(message, state, telegram_id, username)

    elif stage == 'registration':
        # Незавершённая регистрация — продолжаем
        missing = progress.get('missing_fields', [])
        await message.answer(
            '👋 С возвращением! Давайте продолжим регистрацию.',
            reply_markup=REMOVE_KEYBOARD,
        )
        await state.update_data(unique_id=progress['unique_id'])
        await _continue_registration(message, state, missing)

    elif stage == 'testing':
        # Незавершённое тестирование
        last_q = progress.get('last_answered_question', 0)
        await message.answer(
            f'👋 С возвращением! Вы остановились на вопросе {last_q}.\n'
            f'Хотите продолжить тестирование?',
            reply_markup=resume_testing_keyboard(),
        )
        await state.update_data(unique_id=progress['unique_id'])

    elif stage == 'completed':
        # Всё пройдено — показываем логин
        unique_id = progress['unique_id']
        await message.answer(
            f'👋 Вы уже прошли тестирование!\n\n'
            f'🔑 Ваш логин для сайта: {unique_id}\n\n'
            f'Перейдите на сайт для прохождения второй части:',
            reply_markup=website_button(config.WEBSITE_URL),
        )


async def _start_registration(
    message: Message, state: FSMContext,
    telegram_id: int, username: str | None
):
    """Начать регистрацию нового пользователя."""
    await message.answer(
        '👋 Здравствуйте! Добро пожаловать в исследование '
        'логического мышления!\n\n'
        'Вам предстоит:\n'
        '1️⃣ Заполнить краткую анкету\n'
        '2️⃣ Ответить на вопросы по логическому мышлению\n'
        '3️⃣ Пройти тестирование на сайте\n\n'
        'Давайте начнём! ✨',
        reply_markup=REMOVE_KEYBOARD,
    )

    # Создаём запись в Google Sheets
    try:
        if username:
            unique_id = sheets_manager.create_new_user(
                telegram_id, username, None
            )
            await state.update_data(unique_id=unique_id)
            # У пользователя есть username — переходим к запросу имени
            await message.answer(
                'Пожалуйста, введите ваше имя:',
                reply_markup=back_button_keyboard(),
            )
            await state.set_state(Registration.waiting_for_name)
        else:
            # Нет username — запрашиваем телефон
            unique_id = sheets_manager.create_new_user(
                telegram_id, None, None
            )
            await state.update_data(unique_id=unique_id)
            await message.answer(
                'У вас не указан username в Telegram.\n'
                'Пожалуйста, поделитесь номером телефона для идентификации:',
                reply_markup=phone_keyboard(),
            )
            await state.set_state(Registration.waiting_for_phone)

    except Exception as e:
        logger.error(f'Ошибка при создании пользователя: {e}', exc_info=True)
        await message.answer(
            '❌ Произошла ошибка при регистрации. Попробуйте позже.'
        )


async def _continue_registration(
    message: Message, state: FSMContext, missing_fields: list[str]
):
    """Продолжить незавершённую регистрацию."""
    if 'name' in missing_fields:
        await message.answer(
            'Пожалуйста, введите ваше имя:',
            reply_markup=back_button_keyboard(),
        )
        await state.set_state(Registration.waiting_for_name)
    elif 'age' in missing_fields:
        await message.answer(
            'Пожалуйста, введите ваш возраст:',
            reply_markup=back_button_keyboard(),
        )
        await state.set_state(Registration.waiting_for_age)
    elif 'education' in missing_fields:
        await message.answer(
            'Выберите ваш уровень образования:',
            reply_markup=education_keyboard(),
        )
        await state.set_state(Registration.waiting_for_education)


# ===== Обработка телефона =====

@router.message(Registration.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    """Получение номера телефона через кнопку 'Поделиться'."""
    phone = message.contact.phone_number
    telegram_id = message.from_user.id

    # Форматируем номер
    if not phone.startswith('+'):
        phone = '+' + phone

    try:
        sheets_manager.update_user_field(telegram_id, 'telegram_phone', phone)
    except Exception as e:
        logger.error(f'Ошибка сохранения телефона: {e}', exc_info=True)
        await message.answer('❌ Произошла ошибка. Попробуйте ещё раз.')
        return

    await message.answer(
        f'Спасибо! Номер {phone} сохранён. ✨\n\n'
        'Теперь введите ваше имя:',
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Registration.waiting_for_name)


@router.message(Registration.waiting_for_phone)
async def process_phone_invalid(message: Message, state: FSMContext):
    """Неверный формат — повторный запрос телефона."""
    await message.answer(
        '❌ Пожалуйста, нажмите кнопку "📱 Поделиться номером телефона" ниже.',
        reply_markup=phone_keyboard(),
    )


# ===== Обработка имени =====

@router.message(Registration.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Получение имени пользователя."""
    name = message.text.strip() if message.text else ''
    is_valid, error = validate_name(name)

    if not is_valid:
        await message.answer(error)
        return

    telegram_id = message.from_user.id

    try:
        sheets_manager.update_user_field(telegram_id, 'name', name)
    except Exception as e:
        logger.error(f'Ошибка сохранения имени: {e}', exc_info=True)
        await message.answer(
            '❌ Произошла ошибка при сохранении данных. Попробуйте ещё раз.'
        )
        return

    await message.answer(
        f'Отлично, {name}! 🎯\n\n'
        'Теперь введите ваш возраст:',
        reply_markup=back_button_keyboard(),
    )
    await state.set_state(Registration.waiting_for_age)


# ===== Обработка возраста =====

@router.message(Registration.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    """Получение возраста пользователя."""
    is_valid, error, age = validate_age(message.text or '')

    if not is_valid:
        await message.answer(error)
        return

    telegram_id = message.from_user.id

    try:
        sheets_manager.update_user_field(telegram_id, 'age', str(age))
    except Exception as e:
        logger.error(f'Ошибка сохранения возраста: {e}', exc_info=True)
        await message.answer(
            '❌ Произошла ошибка при сохранении данных. Попробуйте ещё раз.'
        )
        return

    await message.answer(
        'Супер! 🙏\n\n'
        'Выберите ваш уровень образования:',
        reply_markup=education_keyboard(),
    )
    await state.set_state(Registration.waiting_for_education)


# ===== Обработка образования =====

@router.callback_query(Registration.waiting_for_education, F.data.startswith('edu_'))
async def process_education(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора уровня образования."""
    education = EDUCATION_MAP.get(callback.data, '')
    if not education:
        await callback.answer('Неизвестный вариант')
        return

    telegram_id = callback.from_user.id

    try:
        sheets_manager.update_user_field(telegram_id, 'education', education)
    except Exception as e:
        logger.error(f'Ошибка сохранения образования: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Произошла ошибка при сохранении данных. Попробуйте ещё раз.'
        )
        return

    await callback.answer('Сохранено!')
    await callback.message.edit_text(
        f'✅ Регистрация завершена!\n\n'
        f'Образование: {education}\n\n'
        f'Теперь перейдём к тестированию. '
        f'Вам будет предложено ответить на вопросы по логическому мышлению.\n\n'
        f'Готовы начать? Нажмите кнопку ниже.',
        reply_markup=_start_testing_keyboard(),
    )
    await state.set_state(None)


def _start_testing_keyboard():
    """Кнопка начала тестирования."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text='🚀 Начать тестирование', callback_data='start_testing'
        )],
    ])


# ===== Кнопка "Назад" при регистрации =====

@router.callback_query(F.data == 'reg_back')
async def registration_back(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Назад' при регистрации."""
    current_state = await state.get_state()

    if current_state == Registration.waiting_for_age.state:
        await callback.message.edit_text('Введите ваше имя:')
        await state.set_state(Registration.waiting_for_name)
    elif current_state == Registration.waiting_for_education.state:
        await callback.message.edit_text(
            'Введите ваш возраст:',
            reply_markup=back_button_keyboard(),
        )
        await state.set_state(Registration.waiting_for_age)
    elif current_state == Registration.waiting_for_name.state:
        await callback.answer('Это первый шаг регистрации')
    else:
        await callback.answer()


# ===== Возобновление тестирования =====

@router.callback_query(F.data == 'resume_test')
async def resume_testing(callback: CallbackQuery, state: FSMContext):
    """Продолжить тестирование с места остановки."""
    from handlers.testing import start_testing_flow
    await callback.answer()
    await start_testing_flow(callback.message, state, callback.from_user.id, resume=True)


@router.callback_query(F.data == 'restart_test')
async def restart_testing(callback: CallbackQuery, state: FSMContext):
    """Начать тестирование заново."""
    from handlers.testing import start_testing_flow
    await callback.answer()
    await start_testing_flow(callback.message, state, callback.from_user.id, resume=False)
