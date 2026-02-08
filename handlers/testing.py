"""Хэндлеры тестирования.

Поддерживает 3 типа вопросов: number, choice, yesno.
Навигация вперёд/назад, прогресс-бар, сохранение ответов.
"""

import logging
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import sheets_manager
from states import Testing
from keyboards.user_kb import (
    question_choice_keyboard,
    question_yesno_keyboard,
    question_number_keyboard,
    website_button,
)
from utils.validators import validate_number_answer
from utils.formatters import format_question
import config

logger = logging.getLogger(__name__)
router = Router()


async def start_testing_flow(
    message: Message, state: FSMContext,
    telegram_id: int, resume: bool = False
):
    """Запустить процесс тестирования.

    Вызывается из start.py после завершения регистрации
    или при возобновлении.
    """
    try:
        questions = sheets_manager.get_all_questions()
    except Exception as e:
        logger.error(f'Ошибка загрузки вопросов: {e}', exc_info=True)
        await message.edit_text(
            '❌ Ошибка загрузки вопросов. Попробуйте позже.'
        )
        return

    if not questions:
        await message.edit_text(
            '❌ Нет доступных вопросов для тестирования.'
        )
        return

    # Определяем начальный индекс
    start_index = 0
    answers = {}

    if resume:
        # Загружаем существующие ответы
        user = sheets_manager.get_user_by_telegram_id(telegram_id)
        if user:
            for i, q in enumerate(questions):
                order = q['order_number']
                answer = user.get(f'question_{order}', '')
                if answer:
                    answers[order] = str(answer)
                    start_index = i + 1

            # Если все ответы уже даны — возвращаемся к последнему
            if start_index >= len(questions):
                start_index = len(questions) - 1

    # Записываем время начала тестирования (если не возобновление)
    if not resume:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheets_manager.update_user_field(telegram_id, 'test_start_time', now)

    # Сохраняем данные в FSM
    await state.update_data(
        questions=[q for q in questions],  # копия списка
        current_index=start_index,
        answers=answers,
        telegram_id=telegram_id,
    )
    await state.set_state(Testing.answering)

    # Показываем первый вопрос
    await _show_question(message, state, edit=True)


async def _show_question(
    message: Message, state: FSMContext, edit: bool = False
):
    """Показать текущий вопрос пользователю."""
    data = await state.get_data()
    questions = data['questions']
    current_index = data['current_index']
    answers = data.get('answers', {})

    if current_index >= len(questions):
        # Все вопросы отвечены — завершаем
        await _finish_testing(message, state, edit)
        return

    question = questions[current_index]
    total = len(questions)
    q_num = current_index + 1

    text = format_question(q_num, total, question['question_text'])

    # Если есть ранее сохранённый ответ, показываем
    order = question['order_number']
    if order in answers:
        text += f'\n\n💡 Ваш предыдущий ответ: {answers[order]}'

    show_back = current_index > 0
    q_type = question['question_type']

    if q_type == 'choice':
        options = [o.strip() for o in str(question['options']).split('|') if o.strip()]
        keyboard = question_choice_keyboard(options, show_back=show_back)
    elif q_type == 'yesno':
        keyboard = question_yesno_keyboard(show_back=show_back)
    else:  # number
        keyboard = question_number_keyboard(show_back=show_back)
        if q_type == 'number':
            text += '\n\n✏️ Введите число:'

    if edit:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


async def _save_and_advance(
    message_or_callback, state: FSMContext, answer: str
):
    """Сохранить ответ и перейти к следующему вопросу."""
    data = await state.get_data()
    questions = data['questions']
    current_index = data['current_index']
    telegram_id = data['telegram_id']
    answers = data.get('answers', {})

    question = questions[current_index]
    order = question['order_number']

    # Сохраняем ответ
    answers[order] = answer
    await state.update_data(
        answers=answers,
        current_index=current_index + 1,
    )

    # Записываем в Google Sheets
    try:
        sheets_manager.save_answer(telegram_id, order, answer)
    except Exception as e:
        logger.error(f'Ошибка сохранения ответа: {e}', exc_info=True)

    # Показываем следующий вопрос
    if isinstance(message_or_callback, CallbackQuery):
        await _show_question(message_or_callback.message, state, edit=True)
    else:
        await _show_question(message_or_callback, state, edit=False)


async def _finish_testing(message: Message, state: FSMContext, edit: bool):
    """Завершить тестирование и выдать логин для сайта."""
    data = await state.get_data()
    telegram_id = data['telegram_id']

    # Записываем время завершения
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        sheets_manager.update_user_field(telegram_id, 'test_end_time', now)
    except Exception as e:
        logger.error(f'Ошибка записи test_end_time: {e}', exc_info=True)

    # Получаем unique_id
    user = sheets_manager.get_user_by_telegram_id(telegram_id)
    unique_id = user.get('unique_id', '???') if user else '???'

    text = (
        '✅ ТЕСТИРОВАНИЕ В БОТЕ ЗАВЕРШЕНО!\n\n'
        'Отличная работа! Вы ответили на все вопросы '
        'по логическому мышлению.\n\n'
        f'🔑 Ваш логин для сайта: {unique_id}\n\n'
        '📋 ИНСТРУКЦИЯ:\n'
        '1. Перейдите на сайт по ссылке ниже\n'
        f'2. Введите ваш логин: {unique_id}\n'
        '3. Пройдите тестирование по критическому мышлению\n\n'
        '⏰ После перехода на сайт у вас будет 60 минут '
        'на прохождение второй части исследования. '
        'Я буду отправлять вам напоминания.\n\n'
        '❗️ Важно: нажмите кнопку "Я перешёл на сайт", '
        'чтобы начать таймер'
    )

    keyboard = website_button(config.WEBSITE_URL)

    if edit:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

    await state.set_state(None)


# ===== Обработка кнопки "Начать тестирование" =====

@router.callback_query(F.data == 'start_testing')
async def on_start_testing(callback: CallbackQuery, state: FSMContext):
    """Нажатие кнопки 'Начать тестирование' после регистрации."""
    await callback.answer()
    await start_testing_flow(
        callback.message, state, callback.from_user.id, resume=False
    )


# ===== Обработка ответов на вопросы =====

@router.callback_query(Testing.answering, F.data.startswith('ans_c_'))
async def on_answer_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа через inline-кнопки (choice) — по индексу."""
    await callback.answer()

    # Формат: ans_c_{index}
    idx = int(callback.data.split('_')[-1])
    data = await state.get_data()
    question = data['questions'][data['current_index']]
    options = [o.strip() for o in str(question['options']).split('|') if o.strip()]

    if idx < 0 or idx >= len(options):
        return

    answer = options[idx]
    await _save_and_advance(callback, state, answer)


@router.callback_query(Testing.answering, F.data.startswith('answer_'))
async def on_answer_yesno(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа Да/Нет."""
    await callback.answer()
    answer = 'Да' if callback.data == 'answer_yes' else 'Нет'
    await _save_and_advance(callback, state, answer)


@router.message(Testing.answering)
async def on_answer_text(message: Message, state: FSMContext):
    """Обработка текстового ответа (number)."""
    data = await state.get_data()
    questions = data['questions']
    current_index = data['current_index']

    if current_index >= len(questions):
        return

    question = questions[current_index]

    if question['question_type'] == 'number':
        is_valid, error = validate_number_answer(message.text or '')
        if not is_valid:
            await message.answer(error)
            return
        answer = message.text.strip()
    else:
        # Для choice/yesno — текстовый ввод тоже принимаем
        answer = (message.text or '').strip()
        if not answer:
            await message.answer('❌ Пожалуйста, выберите вариант ответа.')
            return

    await _save_and_advance(message, state, answer)


# ===== Кнопка "Назад" при тестировании =====

@router.callback_query(Testing.answering, F.data == 'test_back')
async def on_test_back(callback: CallbackQuery, state: FSMContext):
    """Вернуться к предыдущему вопросу."""
    data = await state.get_data()
    current_index = data['current_index']

    if current_index <= 0:
        await callback.answer('Это первый вопрос')
        return

    await callback.answer()
    await state.update_data(current_index=current_index - 1)
    await _show_question(callback.message, state, edit=True)
