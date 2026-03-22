"""Хэндлеры тестирования.

Поддерживает 2 типа вопросов: choice, text.
Навигация вперёд/назад, прогресс-бар, сохранение ответов.
"""

import asyncio
import logging
import os
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import sheets_manager
from states import Testing
from keyboards.user_kb import (
    question_choice_keyboard,
    question_text_keyboard,
    website_button,
    final_completed_keyboard,
)
from utils.formatters import format_question
from handlers.timers import start_timer
import config

logger = logging.getLogger(__name__)
router = Router()

# Мьютексы для защиты от быстрых повторных кликов
_answer_locks: dict[int, asyncio.Lock] = {}

# ===== Вводная часть «Стержни» (показывается перед вопросом 15) =====

RODS_INTRO_ORDER = 15

RODS_INTRO_TEXT = (
    'Я проводил(а) опыты с разными стержнями. '
    'Хочу рассказать тебе о результатах и узнать, что ты думаешь. '
    'Посмотри на первую карточку. Этот стержень гнётся легко.'
)

RODS_CARDS = [
    'Первый стержень гнётся легко. Он длинный, тонкий, с круглым основанием, сделан из латуни.',
    'Второй стержень гнётся плохо. Он длинный, тонкий, с круглым основанием, сделан из стали.',
    'Третий стержень гнётся легко. Он длинный, толстый, с квадратным основанием, сделан из латуни.',
    'Четвёртый стержень гнётся плохо. Он длинный, толстый, с круглым основанием, сделан из стали.',
    'Пятый стержень гнётся легко. Он короткий, толстый, с квадратным основанием, сделан из латуни.',
    'Шестой стержень тоже гнётся легко. Он короткий, тонкий, с квадратным основанием, сделан из латуни.',
    'Седьмой стержень гнётся плохо. Он короткий, тонкий, с круглым основанием, сделан из стали.',
    'Восьмой стержень тоже гнётся плохо. Он короткий, тонкий, с квадратным основанием, сделан из стали.',
]

RODS_OUTRO_TEXT = (
    'Теперь у меня есть ещё один стержень, который я пока не испытывал(а). '
    'Он длинный, тонкий, с квадратным основанием и сделан из стали.'
)

CARDS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'images', 'cards',
)

# ===== Вводная часть «Растения» (показывается перед вопросом 28) =====

FLOWERS_INTRO_ORDER = 28

FLOWERS_INTRO_TEXT = (
    'Я вырастил(а) растения. Мне бы хотелось показать их тебе '
    'и спросить, что ты думаешь. Посмотри на первое растение.'
)

FLOWERS_CARDS = [
    'Оно кажется здоровым, не так ли? Ему давали каждую неделю один большой стакан воды и немного светлой подкормки.',
    'Второе растение нездорово. Ему давали каждую неделю один большой стакан воды, немного темной подкормки и немного жидкости для листьев.',
    'Третье растение выглядит здоровым. Ему давали каждую неделю один маленький стакан воды, немного светлой подкормки и немного жидкости для листьев.',
    'Четвертое растение нездорово. Ему давали каждую неделю один маленький стакан воды и немного темной подкормки.',
    'Пятое растение нездорово. Ему давали каждую неделю один большой стакан воды и немного темной подкормки.',
    'Шестое растение здорово. Ему давали каждую неделю один большой стакан воды, немного светлой подкормки и немного жидкости для листьев.',
]

FLOWERS_OUTRO_TEXT = (
    'Сейчас у меня есть дома такое же растение, и я начал(а) за ним ухаживать. '
    'Каждую неделю я даю ему один маленький стакан воды, немного светлой подкормки '
    'и совсем не даю жидкости для листьев.'
)

FLOWERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'images', 'flowers',
)


async def start_testing_flow(
    message: Message, state: FSMContext,
    telegram_id: int, resume: bool = False
):
    """Запустить процесс тестирования.

    Вызывается из start.py после завершения регистрации
    или при возобновлении.
    """
    try:
        questions = await sheets_manager.async_get_all_questions()
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
        user = await sheets_manager.async_get_user_by_telegram_id(telegram_id)
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
        await sheets_manager.async_update_user_field(telegram_id, 'test_start_time', now)

    # Если при resume мы уже за интро — не показывать повторно
    rods_intro_shown = resume and RODS_INTRO_ORDER in answers
    flowers_intro_shown = resume and FLOWERS_INTRO_ORDER in answers

    # Сохраняем данные в FSM
    await state.update_data(
        questions=[q for q in questions],  # копия списка
        current_index=start_index,
        answers=answers,
        telegram_id=telegram_id,
        rods_intro_shown=rods_intro_shown,
        flowers_intro_shown=flowers_intro_shown,
    )
    await state.set_state(Testing.answering)

    # Показываем первый вопрос
    await _show_question(message, state, edit=True)


async def _show_rods_intro(message: Message):
    """Отправить вводную часть эксперимента со стержнями (8 карточек с фото)."""
    await message.answer(RODS_INTRO_TEXT)
    await asyncio.sleep(0.5)

    for i, caption in enumerate(RODS_CARDS, 1):
        photo_path = os.path.join(CARDS_DIR, f'photo{i}.JPG')
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo=photo, caption=caption)
        await asyncio.sleep(7)

    await message.answer(RODS_OUTRO_TEXT)
    await asyncio.sleep(0.3)


async def _show_flowers_intro(message: Message):
    """Отправить вводную часть эксперимента с растениями (6 карточек с фото)."""
    await message.answer(FLOWERS_INTRO_TEXT)
    await asyncio.sleep(0.5)

    for i, caption in enumerate(FLOWERS_CARDS, 1):
        photo_path = os.path.join(FLOWERS_DIR, f'photo{i}.PNG')
        photo = FSInputFile(photo_path)
        await message.answer_photo(photo=photo, caption=caption)
        await asyncio.sleep(7)

    await message.answer(FLOWERS_OUTRO_TEXT)
    await asyncio.sleep(0.3)


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

    # Вводная часть «Стержни» перед вопросом 15
    if (question['order_number'] == RODS_INTRO_ORDER
            and not data.get('rods_intro_shown')):
        await _show_rods_intro(message)
        await state.update_data(rods_intro_shown=True)
        edit = False

    # Вводная часть «Растения» перед вопросом 28
    if (question['order_number'] == FLOWERS_INTRO_ORDER
            and not data.get('flowers_intro_shown')):
        await _show_flowers_intro(message)
        await state.update_data(flowers_intro_shown=True)
        edit = False
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
    else:  # text
        keyboard = question_text_keyboard(show_back=show_back)
        text += '\n\n✏️ Введите ваш ответ:'

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
    total = len(questions)
    q_num = current_index + 1

    # Сохраняем ответ
    answers[order] = answer
    await state.update_data(
        answers=answers,
        current_index=current_index + 1,
    )

    # Записываем в Google Sheets
    try:
        await sheets_manager.async_save_answer(telegram_id, order, answer)
    except Exception as e:
        logger.error(f'Ошибка сохранения ответа: {e}', exc_info=True)

    # Фиксируем ответ на текущем сообщении (убираем кнопки, показываем ответ)
    answered_text = (
        f'📊 Вопрос {q_num} из {total}\n\n'
        f'{question["question_text"]}\n\n'
        f'✅ Ваш ответ: {answer}'
    )

    if isinstance(message_or_callback, CallbackQuery):
        msg = message_or_callback.message
        try:
            await msg.edit_text(answered_text)
        except Exception:
            pass
        # Следующий вопрос — новым сообщением
        await _show_question(msg, state, edit=False)
    else:
        # Текстовый ответ (number) — отправляем подтверждение и новый вопрос
        await message_or_callback.reply(f'✅ Ваш ответ: {answer}')
        await _show_question(message_or_callback, state, edit=False)


def _calculate_scores(
    questions: list[dict], answers: dict
) -> tuple[dict, dict]:
    """Подсчитать баллы по двум группам вопросов.

    Возвращает (group1_result, group2_result).
    group1_result: {'score': int, 'max': 14}
    group2_result: {'score': int, 'max': 16, 'scales': {name: {'score': int, 'max': 4}}}
    """
    G1_SCALE = 'Количество верно решенных задач'
    G2_SCALES = {
        'Обнаружение фактов, аргументов, гипотез и опровержений',
        'Анализ и критика аргументов',
        'Оценка противоречий и альтернатив',
        'Формулировка вывода',
    }

    g1_score = 0
    g1_max = 0
    g2_score = 0
    g2_max = 0
    scales: dict[str, dict] = {}

    for q in questions:
        correct = q.get('correct_answer', '')
        if not correct:
            continue

        order = q['order_number']
        user_answer = answers.get(order, '')
        is_correct = user_answer.strip().lower() == correct.strip().lower()
        scale_name = q.get('scale', '')

        if scale_name == G1_SCALE:
            g1_max += 1
            if is_correct:
                g1_score += 1
        elif scale_name in G2_SCALES:
            g2_max += 1
            if is_correct:
                g2_score += 1
            if scale_name not in scales:
                scales[scale_name] = {'score': 0, 'max': 0}
            scales[scale_name]['max'] += 1
            if is_correct:
                scales[scale_name]['score'] += 1

    return (
        {'score': g1_score, 'max': g1_max},
        {'score': g2_score, 'max': g2_max, 'scales': scales},
    )


def _format_group1_message(score: int) -> str:
    if score >= 10:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 14. '
            f'Это свидетельствует о том, что вы демонстрируете высокую эффективность '
            f'при решении задач данного типа: справляетесь с ними уверенно и последовательно, '
            f'с минимальным количеством ошибок. Подобный результат указывает на то, что '
            f'предложенный формат заданий не вызывает у вас существенных затруднений.'
        )
    elif score >= 5:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 14. '
            f'Это говорит о том, что задания данного типа выполняются вами в целом успешно, '
            f'однако в ряде случаев возникают определённые затруднения. Часть задач решается '
            f'уверенно, тогда как другие требуют большего времени или приводят к неточностям. '
            f'Подобный результат является распространённым и отражает типичный диапазон '
            f'выполнения для данного формата.'
        )
    else:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 14. '
            f'Результат показывает, что задания данного формата в большинстве случаев '
            f'вызывали значительные затруднения. Это может быть связано с рядом факторов: '
            f'непривычной структурой задач, особенностями восприятия условий или степенью '
            f'знакомости с подобным типом заданий. Полученные данные представляют для нас '
            f'важную исследовательскую ценность.'
        )


def _format_group2_message(score: int, scales: dict) -> str:
    s1 = scales.get('Обнаружение фактов, аргументов, гипотез и опровержений', {'score': 0, 'max': 4})
    s2 = scales.get('Анализ и критика аргументов', {'score': 0, 'max': 4})
    s3 = scales.get('Оценка противоречий и альтернатив', {'score': 0, 'max': 4})
    s4 = scales.get('Формулировка вывода', {'score': 0, 'max': 4})

    scale_text = (
        f'По шкале «Обнаружение фактов, аргументов, гипотез и опровержений» '
        f'вы набрали {s1["score"]} из {s1["max"]} баллов, '
        f'по шкале «Анализ и критика аргументов» — {s2["score"]} из {s2["max"]}, '
        f'по шкале «Оценка противоречий и альтернатив» — {s3["score"]} из {s3["max"]}, '
        f'по шкале «Формулировка вывода» — {s4["score"]} из {s4["max"]}.'
    )

    if score >= 13:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 16. '
            f'Это высокий результат, отражающий уверенное владение навыками '
            f'критического мышления в данном формате. {scale_text} '
            f'Вы успешно справились с задачами разного типа: выявляли факты и аргументы, '
            f'анализировали критику, искали альтернативные гипотезы, обнаруживали '
            f'противоречия и формулировали обоснованные выводы. '
            f'Полученные данные представляют для нас важную исследовательскую ценность.'
        )
    elif score >= 7:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 16. '
            f'{scale_text} '
            f'В ряде случаев возникали определённые затруднения. Часть задач решалась '
            f'уверенно, тогда как другие аспекты могли требовать большего времени или '
            f'приводить к неточностям. Подобный результат является распространённым '
            f'и отражает типичный диапазон выполнения для данного формата. '
            f'Полученные данные представляют для нас важную исследовательскую ценность.'
        )
    else:
        return (
            f'Благодарим вас за участие в исследовании! '
            f'По итогам выполнения заданий вы набрали {score} баллов из 16. '
            f'{scale_text} '
            f'Задания данного формата в большинстве случаев вызывали значительные '
            f'затруднения. Это может быть связано с рядом факторов: непривычной структурой '
            f'задач, сложностью разграничения понятий, трудностями при анализе критики '
            f'аргументации, поиске альтернатив и противоречий, а также при формулировке '
            f'точных и обоснованных выводов. '
            f'Полученные данные представляют для нас важную исследовательскую ценность.'
        )


async def _finish_testing(message: Message, state: FSMContext, edit: bool):
    """Завершить тестирование: подсчитать баллы, показать результат, перенаправить на сайт."""
    data = await state.get_data()
    telegram_id = data['telegram_id']
    questions = data['questions']
    answers = data.get('answers', {})

    # Записываем время завершения
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        await sheets_manager.async_update_user_field(telegram_id, 'test_end_time', now)
    except Exception as e:
        logger.error(f'Ошибка записи test_end_time: {e}', exc_info=True)

    # Подсчёт баллов
    g1, g2 = _calculate_scores(questions, answers)

    # Результаты группы 1 (вопросы 1–14)
    await message.answer(f'📊 РЕЗУЛЬТАТЫ (часть 1)\n\n{_format_group1_message(g1["score"])}')
    await asyncio.sleep(1)

    # Результаты группы 2 (вопросы 38–53)
    await message.answer(f'📊 РЕЗУЛЬТАТЫ (часть 2)\n\n{_format_group2_message(g2["score"], g2["scales"])}')
    await asyncio.sleep(1)

    # Получаем unique_id и отправляем на сайт
    user = await sheets_manager.async_get_user_by_telegram_id(telegram_id)
    unique_id = user.get('unique_id', '???') if user else '???'

    text = (
        f'🔑 Ваш логин для сайта: {unique_id}\n\n'
        '📋 ИНСТРУКЦИЯ:\n'
        '1. Перейдите на сайт по ссылке ниже\n'
        f'2. Введите ваш логин: {unique_id}\n'
        '3. Пройдите вторую часть исследования\n\n'
        'Я буду отправлять вам напоминания о необходимости завершения исследования.'
    )

    keyboard = website_button(config.WEBSITE_URL)
    await message.answer(text, reply_markup=keyboard)

    await start_timer(message.bot, telegram_id, unique_id)

    await message.answer(
        'После завершения тестирования на сайте нажмите кнопку ниже:',
        reply_markup=final_completed_keyboard(),
    )
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

def _get_answer_lock(telegram_id: int) -> asyncio.Lock:
    """Получить мьютекс для пользователя."""
    if telegram_id not in _answer_locks:
        _answer_locks[telegram_id] = asyncio.Lock()
    return _answer_locks[telegram_id]


@router.callback_query(Testing.answering, F.data.startswith('ans_c_'))
async def on_answer_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа через inline-кнопки (choice) — по индексу."""
    lock = _get_answer_lock(callback.from_user.id)
    if lock.locked():
        await callback.answer()
        return

    async with lock:
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


@router.message(Testing.answering)
async def on_answer_text(message: Message, state: FSMContext):
    """Обработка текстового ответа."""
    lock = _get_answer_lock(message.from_user.id)
    if lock.locked():
        return

    async with lock:
        data = await state.get_data()
        questions = data['questions']
        current_index = data['current_index']

        if current_index >= len(questions):
            return

        answer = (message.text or '').strip()
        if not answer:
            await message.answer('❌ Пожалуйста, введите ответ.')
            return

        await _save_and_advance(message, state, answer)


# ===== Кнопка "Назад" при тестировании =====

@router.callback_query(Testing.answering, F.data == 'test_back')
async def on_test_back(callback: CallbackQuery, state: FSMContext):
    """Вернуться к предыдущему вопросу."""
    lock = _get_answer_lock(callback.from_user.id)
    if lock.locked():
        await callback.answer()
        return

    async with lock:
        data = await state.get_data()
        current_index = data['current_index']

        if current_index <= 0:
            await callback.answer('Это первый вопрос')
            return

        await callback.answer()
        await state.update_data(current_index=current_index - 1)
        await _show_question(callback.message, state, edit=False)
