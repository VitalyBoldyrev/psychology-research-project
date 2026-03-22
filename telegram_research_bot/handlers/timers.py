"""Система напоминаний.

После завершения тестирования и перехода на сайт
через 15 минут отправляется одно напоминание.
"""

import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

import config
import sheets_manager
from keyboards.user_kb import reminder_keyboard, final_completed_keyboard

logger = logging.getLogger(__name__)
router = Router()


async def start_timer(bot: Bot, telegram_id: int, unique_id: str):
    """Записать таймер в Sheets и запланировать напоминание через 15 минут."""
    try:
        await sheets_manager.async_create_timer(telegram_id, unique_id)
    except Exception as e:
        logger.error(f'Ошибка создания таймера: {e}', exc_info=True)

    asyncio.create_task(_delayed_reminder(bot, telegram_id))
    logger.info(f'Напоминание запланировано для {telegram_id} через {config.REMINDER_DELAY} мин')


async def _delayed_reminder(bot: Bot, telegram_id: int):
    """Подождать REMINDER_DELAY минут и отправить напоминание."""
    await asyncio.sleep(config.REMINDER_DELAY * 60)

    timer = await sheets_manager.async_get_timer(telegram_id)
    if timer and str(timer.get('completed', '')).upper() == 'YES':
        logger.info(f'Пользователь {telegram_id} уже завершил — пропускаем')
        return

    try:
        await bot.send_message(
            telegram_id,
            f'⏰ Прошло {config.REMINDER_DELAY} минут\n\n'
            'Пожалуйста, завершите исследование на сайте, '
            'если вы ещё этого не сделали.\n\n'
            'Нам очень важны ваши ответы!\n\n'
            'После завершения нажмите кнопку ниже.',
            reply_markup=final_completed_keyboard(),
        )
        await sheets_manager.async_update_timer_field(
            telegram_id, 'first_reminder_sent', 'YES'
        )
        logger.info(f'Напоминание отправлено для {telegram_id}')
    except Exception as e:
        logger.error(f'Ошибка отправки напоминания для {telegram_id}: {e}', exc_info=True)


# ===== Обработка ответов на напоминания =====

@router.callback_query(F.data == 'site_completed')
async def on_site_completed(callback: CallbackQuery, state: FSMContext):
    """Пользователь завершил тестирование на сайте."""
    await callback.answer('Спасибо! 🎉')

    telegram_id = callback.from_user.id

    try:
        await sheets_manager.async_mark_website_completed(telegram_id)
        await sheets_manager.async_update_timer_field(telegram_id, 'completed', 'YES')
    except Exception as e:
        logger.error(f'Ошибка обновления статуса: {e}', exc_info=True)

    await callback.message.edit_text(
        '🎉 Спасибо за участие в исследовании!\n\n'
        'Ваши данные сохранены. Удачи! ✨'
    )


@router.callback_query(F.data == 'site_in_progress')
async def on_site_in_progress(callback: CallbackQuery, state: FSMContext):
    """Пользователь ещё проходит тестирование."""
    await callback.answer()
    await callback.message.edit_text(
        'Хорошо, продолжайте! Я напомню позже. 📝'
    )
