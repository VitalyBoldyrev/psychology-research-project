"""Административная панель.

Функции: управление вопросами, статистика, экспорт данных.
Доступ ограничен списком ADMIN_IDS из config.py.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import sheets_manager
from states import AdminPanel
from keyboards.admin_kb import (
    admin_main_menu,
    questions_menu,
    questions_list_keyboard,
    question_type_keyboard,
    edit_question_keyboard,
    confirm_delete_keyboard,
    back_to_admin,
)

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    return user_id in config.ADMIN_IDS


# ===== Команда /admin =====

@router.message(Command('admin'))
async def cmd_admin(message: Message, state: FSMContext):
    """Главное меню администратора."""
    if not _is_admin(message.from_user.id):
        await message.answer('❌ У вас нет доступа к админ-панели.')
        return

    await message.answer(
        '🔧 ПАНЕЛЬ АДМИНИСТРАТОРА',
        reply_markup=admin_main_menu(),
    )
    await state.set_state(AdminPanel.main_menu)


@router.callback_query(F.data == 'admin_main')
async def admin_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню админки."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()
    await callback.message.edit_text(
        '🔧 ПАНЕЛЬ АДМИНИСТРАТОРА',
        reply_markup=admin_main_menu(),
    )
    await state.set_state(AdminPanel.main_menu)


# ===== Статистика =====

@router.callback_query(F.data == 'admin_stats')
async def admin_stats(callback: CallbackQuery, state: FSMContext):
    """Показать статистику."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()

    try:
        stats = sheets_manager.get_statistics()
    except Exception as e:
        logger.error(f'Ошибка получения статистики: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка загрузки статистики.',
            reply_markup=back_to_admin(),
        )
        return

    text = (
        '📊 СТАТИСТИКА\n\n'
        f"Всего зарегистрировано: {stats['total_users']} человек\n"
        f"Завершили тест в боте: {stats['completed_test']} человек\n"
        f"Прошли тест на сайте: {stats['completed_site']} человек\n"
        f"Активных вопросов: {stats['active_questions']}"
    )

    await callback.message.edit_text(text, reply_markup=back_to_admin())


# ===== Экспорт данных =====

@router.callback_query(F.data == 'admin_export')
async def admin_export(callback: CallbackQuery, state: FSMContext):
    """Отправить ссылку на Google Sheets таблицу."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()
    url = f'https://docs.google.com/spreadsheets/d/{config.SPREADSHEET_ID}'
    await callback.message.edit_text(
        f'📥 Все данные доступны в таблице:\n{url}',
        reply_markup=back_to_admin(),
    )


# ===== Управление вопросами =====

@router.callback_query(F.data == 'admin_questions')
async def admin_questions(callback: CallbackQuery, state: FSMContext):
    """Меню управления вопросами."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()
    await callback.message.edit_text(
        '📝 УПРАВЛЕНИЕ ВОПРОСАМИ',
        reply_markup=questions_menu(),
    )


# ===== Список вопросов с пагинацией =====

@router.callback_query(F.data.startswith('admin_list_questions_'))
async def admin_list_questions(callback: CallbackQuery, state: FSMContext):
    """Список всех вопросов с пагинацией."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()

    page = int(callback.data.split('_')[-1])

    try:
        questions = sheets_manager.get_all_questions_admin()
    except Exception as e:
        logger.error(f'Ошибка загрузки вопросов: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка загрузки вопросов.',
            reply_markup=back_to_admin(),
        )
        return

    if not questions:
        await callback.message.edit_text(
            '📋 Список вопросов пуст.',
            reply_markup=questions_menu(),
        )
        return

    total_pages = max(1, (len(questions) + 4) // 5)
    text = f'📋 СПИСОК ВОПРОСОВ (страница {page + 1}/{total_pages})'

    await callback.message.edit_text(
        text,
        reply_markup=questions_list_keyboard(questions, page),
    )
    await state.set_state(AdminPanel.questions_list)


# ===== Добавление вопроса =====

@router.callback_query(F.data == 'admin_add_question')
async def admin_add_question(callback: CallbackQuery, state: FSMContext):
    """Начать добавление нового вопроса — запросить текст."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()
    await callback.message.edit_text(
        '➕ ДОБАВЛЕНИЕ НОВОГО ВОПРОСА\n\n'
        'Введите текст вопроса:'
    )
    await state.set_state(AdminPanel.adding_question_text)


@router.message(AdminPanel.adding_question_text)
async def admin_add_question_text(message: Message, state: FSMContext):
    """Получить текст нового вопроса."""
    text = (message.text or '').strip()
    if not text:
        await message.answer('❌ Текст вопроса не может быть пустым.')
        return

    await state.update_data(new_question_text=text)
    await message.answer(
        'Выберите тип вопроса:',
        reply_markup=question_type_keyboard(),
    )
    await state.set_state(AdminPanel.adding_question_type)


@router.callback_query(
    AdminPanel.adding_question_type, F.data.startswith('qtype_')
)
async def admin_add_question_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа нового вопроса."""
    await callback.answer()

    type_map = {
        'qtype_choice': 'choice',
        'qtype_text': 'text',
    }
    q_type = type_map.get(callback.data)
    if not q_type:
        return

    await state.update_data(new_question_type=q_type)

    if q_type == 'choice':
        await callback.message.edit_text(
            'Введите варианты ответа через запятую\n'
            '(например: 2, 3, 4, 6):'
        )
        await state.set_state(AdminPanel.adding_question_options)
    else:
        # text — сохраняем вопрос сразу
        await _save_new_question(callback.message, state, edit=True)


@router.message(AdminPanel.adding_question_options)
async def admin_add_question_options(message: Message, state: FSMContext):
    """Получить варианты ответа для вопроса типа choice."""
    text = (message.text or '').strip()
    if not text:
        await message.answer('❌ Введите варианты ответа через запятую.')
        return

    # Преобразуем запятые в разделитель |
    options = '|'.join(o.strip() for o in text.split(',') if o.strip())
    await state.update_data(new_question_options=options)
    await _save_new_question(message, state, edit=False)


async def _save_new_question(
    message: Message, state: FSMContext, edit: bool
):
    """Сохранить новый вопрос в Google Sheets."""
    data = await state.get_data()
    q_text = data['new_question_text']
    q_type = data['new_question_type']
    options = data.get('new_question_options', '')

    try:
        order = sheets_manager.add_question(q_text, q_type, options)
        result_text = (
            f'✅ Вопрос добавлен!\n'
            f'Порядковый номер: {order}\n'
            f'Тип: {q_type}'
        )
    except Exception as e:
        logger.error(f'Ошибка добавления вопроса: {e}', exc_info=True)
        result_text = '❌ Ошибка при добавлении вопроса.'

    if edit:
        await message.edit_text(result_text, reply_markup=questions_menu())
    else:
        await message.answer(result_text, reply_markup=questions_menu())

    await state.set_state(AdminPanel.main_menu)


# ===== Редактирование вопроса =====

@router.callback_query(F.data.startswith('admin_edit_q_'))
async def admin_edit_question(callback: CallbackQuery, state: FSMContext):
    """Показать меню редактирования вопроса."""
    if not _is_admin(callback.from_user.id):
        await callback.answer('Нет доступа')
        return

    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    try:
        questions = sheets_manager.get_all_questions_admin()
        question = next(
            (q for q in questions if q['question_id'] == question_id), None
        )
    except Exception as e:
        logger.error(f'Ошибка загрузки вопроса: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка загрузки вопроса.', reply_markup=back_to_admin()
        )
        return

    if not question:
        await callback.message.edit_text(
            '❌ Вопрос не найден.', reply_markup=back_to_admin()
        )
        return

    await state.update_data(editing_question_id=question_id)

    status = '✅ Активен' if question['is_active'] else '❌ Неактивен'
    type_names = {'choice': '📋 Выбор', 'text': '✏️ Текст'}
    q_type_name = type_names.get(question['question_type'], question['question_type'])

    text = (
        f"✏️ РЕДАКТИРОВАНИЕ ВОПРОСА #{question['order_number']}\n\n"
        f"Статус: {status}\n"
        f"Тип: {q_type_name}\n\n"
        f"Текст: {question['question_text']}"
    )

    if question['question_type'] == 'choice' and question['options']:
        options = question['options'].replace('|', ', ')
        text += f'\n\nВарианты: {options}'

    await callback.message.edit_text(
        text, reply_markup=edit_question_keyboard(question)
    )
    await state.set_state(AdminPanel.editing_question)


# ===== Действия редактирования =====

@router.callback_query(F.data.startswith('editq_text_'))
async def editq_text(callback: CallbackQuery, state: FSMContext):
    """Начать изменение текста вопроса."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])
    await state.update_data(editing_question_id=question_id)
    await callback.message.edit_text(
        'Введите новый текст вопроса:'
    )
    await state.set_state(AdminPanel.editing_question_text)


@router.message(AdminPanel.editing_question_text)
async def editq_text_input(message: Message, state: FSMContext):
    """Сохранить новый текст вопроса."""
    text = (message.text or '').strip()
    if not text:
        await message.answer('❌ Текст не может быть пустым.')
        return

    data = await state.get_data()
    question_id = data['editing_question_id']

    try:
        sheets_manager.update_question(question_id, 'question_text', text)
        await message.answer(
            '✅ Текст вопроса обновлён!', reply_markup=back_to_admin()
        )
    except Exception as e:
        logger.error(f'Ошибка обновления текста: {e}', exc_info=True)
        await message.answer(
            '❌ Ошибка обновления.', reply_markup=back_to_admin()
        )

    await state.set_state(AdminPanel.main_menu)


@router.callback_query(F.data.startswith('editq_type_'))
async def editq_type(callback: CallbackQuery, state: FSMContext):
    """Начать изменение типа вопроса."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])
    await state.update_data(editing_question_id=question_id)
    await callback.message.edit_text(
        'Выберите новый тип вопроса:',
        reply_markup=question_type_keyboard(),
    )
    await state.set_state(AdminPanel.editing_question_type)


@router.callback_query(
    AdminPanel.editing_question_type, F.data.startswith('qtype_')
)
async def editq_type_save(callback: CallbackQuery, state: FSMContext):
    """Сохранить новый тип вопроса."""
    await callback.answer()
    type_map = {
        'qtype_choice': 'choice',
        'qtype_text': 'text',
    }
    q_type = type_map.get(callback.data)
    if not q_type:
        return

    data = await state.get_data()
    question_id = data['editing_question_id']

    try:
        sheets_manager.update_question(question_id, 'question_type', q_type)

        if q_type == 'choice':
            await callback.message.edit_text(
                'Введите варианты ответа через запятую:'
            )
            await state.set_state(AdminPanel.editing_question_options)
            return

        await callback.message.edit_text(
            '✅ Тип вопроса обновлён!', reply_markup=back_to_admin()
        )
    except Exception as e:
        logger.error(f'Ошибка обновления типа: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка обновления.', reply_markup=back_to_admin()
        )

    await state.set_state(AdminPanel.main_menu)


@router.callback_query(F.data.startswith('editq_options_'))
async def editq_options(callback: CallbackQuery, state: FSMContext):
    """Начать изменение вариантов ответа."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])
    await state.update_data(editing_question_id=question_id)
    await callback.message.edit_text(
        'Введите новые варианты ответа через запятую\n'
        '(например: 2, 3, 4, 6):'
    )
    await state.set_state(AdminPanel.editing_question_options)


@router.message(AdminPanel.editing_question_options)
async def editq_options_save(message: Message, state: FSMContext):
    """Сохранить новые варианты ответа."""
    text = (message.text or '').strip()
    if not text:
        await message.answer('❌ Введите варианты через запятую.')
        return

    options = '|'.join(o.strip() for o in text.split(',') if o.strip())
    data = await state.get_data()
    question_id = data['editing_question_id']

    try:
        sheets_manager.update_question(question_id, 'options', options)
        await message.answer(
            '✅ Варианты обновлены!', reply_markup=back_to_admin()
        )
    except Exception as e:
        logger.error(f'Ошибка обновления вариантов: {e}', exc_info=True)
        await message.answer(
            '❌ Ошибка обновления.', reply_markup=back_to_admin()
        )

    await state.set_state(AdminPanel.main_menu)


# ===== Перемещение вопросов =====

@router.callback_query(F.data.startswith('editq_up_'))
async def editq_move_up(callback: CallbackQuery, state: FSMContext):
    """Переместить вопрос выше."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    try:
        success = sheets_manager.swap_question_order(question_id, 'up')
        if success:
            await callback.answer('Вопрос перемещён вверх ⬆️')
        else:
            await callback.answer('Невозможно переместить')
    except Exception as e:
        logger.error(f'Ошибка перемещения: {e}', exc_info=True)
        await callback.answer('Ошибка')

    # Обновляем список
    await admin_list_questions(
        callback, state
    )


@router.callback_query(F.data.startswith('editq_down_'))
async def editq_move_down(callback: CallbackQuery, state: FSMContext):
    """Переместить вопрос ниже."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    try:
        success = sheets_manager.swap_question_order(question_id, 'down')
        if success:
            await callback.answer('Вопрос перемещён вниз ⬇️')
        else:
            await callback.answer('Невозможно переместить')
    except Exception as e:
        logger.error(f'Ошибка перемещения: {e}', exc_info=True)
        await callback.answer('Ошибка')

    await admin_list_questions(callback, state)


# ===== Активация/Деактивация =====

@router.callback_query(F.data.startswith('editq_deactivate_'))
async def editq_deactivate(callback: CallbackQuery, state: FSMContext):
    """Деактивировать вопрос — запросить подтверждение."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    await callback.message.edit_text(
        '⚠️ Вы уверены, что хотите деактивировать этот вопрос?',
        reply_markup=confirm_delete_keyboard(question_id),
    )
    await state.set_state(AdminPanel.confirm_delete)


@router.callback_query(F.data.startswith('confirm_del_'))
async def confirm_deactivate(callback: CallbackQuery, state: FSMContext):
    """Подтвердить деактивацию вопроса."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    try:
        sheets_manager.delete_question(question_id)
        await callback.message.edit_text(
            '✅ Вопрос деактивирован.',
            reply_markup=questions_menu(),
        )
    except Exception as e:
        logger.error(f'Ошибка деактивации: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка деактивации.', reply_markup=back_to_admin()
        )

    await state.set_state(AdminPanel.main_menu)


@router.callback_query(F.data.startswith('editq_activate_'))
async def editq_activate(callback: CallbackQuery, state: FSMContext):
    """Активировать вопрос."""
    if not _is_admin(callback.from_user.id):
        return
    await callback.answer()
    question_id = int(callback.data.split('_')[-1])

    try:
        sheets_manager.activate_question(question_id)
        await callback.message.edit_text(
            '✅ Вопрос активирован!',
            reply_markup=questions_menu(),
        )
    except Exception as e:
        logger.error(f'Ошибка активации: {e}', exc_info=True)
        await callback.message.edit_text(
            '❌ Ошибка.', reply_markup=back_to_admin()
        )

    await state.set_state(AdminPanel.main_menu)
