"""Система таймеров и напоминаний.

После нажатия кнопки "Перейти на сайт" запускаются 3 напоминания:
- через 30 мин — первое напоминание
- через 45 мин — последнее напоминание
- через 60 мин — финальное сообщение
"""

import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import sheets_manager
from keyboards.user_kb import reminder_keyboard, final_completed_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Глобальная ссылка на планировщик (устанавливается из bot.py)
scheduler: AsyncIOScheduler | None = None


def setup_scheduler(sched: AsyncIOScheduler):
    """Установить ссылку на планировщик."""
    global scheduler
    scheduler = sched


# ===== Запуск таймера =====

async def start_timer(bot: Bot, telegram_id: int, unique_id: str):
    """Запустить таймер и запланировать напоминания."""
    logger.info(f'start_timer вызван для {telegram_id}, scheduler={scheduler}')

    # Записываем таймер в Google Sheets
    try:
        await sheets_manager.async_create_timer(telegram_id, unique_id)
    except Exception as e:
        logger.error(f'Ошибка создания таймера: {e}', exc_info=True)

    now = datetime.now()

    # Планируем напоминания
    if scheduler:
        # Первое напоминание — через 30 минут
        scheduler.add_job(
            _send_first_reminder,
            'date',
            run_date=now + timedelta(minutes=config.FIRST_REMINDER),
            args=[bot, telegram_id],
            id=f'reminder_1_{telegram_id}',
            replace_existing=True,
        )

        # Второе напоминание — через 45 минут
        scheduler.add_job(
            _send_second_reminder,
            'date',
            run_date=now + timedelta(minutes=config.SECOND_REMINDER),
            args=[bot, telegram_id],
            id=f'reminder_2_{telegram_id}',
            replace_existing=True,
        )

        # Финальное сообщение — через 60 минут
        scheduler.add_job(
            _send_final_message,
            'date',
            run_date=now + timedelta(minutes=config.FINAL_MESSAGE),
            args=[bot, telegram_id],
            id=f'reminder_final_{telegram_id}',
            replace_existing=True,
        )

        logger.info(
            f'Таймеры запланированы для {telegram_id}: '
            f'{config.FIRST_REMINDER}мин, {config.SECOND_REMINDER}мин, {config.FINAL_MESSAGE}мин'
        )
    else:
        logger.error('scheduler is None — таймеры НЕ запланированы!')


# ===== Функции отправки напоминаний =====

async def _send_first_reminder(bot: Bot, telegram_id: int):
    """Отправить первое напоминание (через 30 мин)."""
    logger.info(f'Отправка 1-го напоминания для {telegram_id}')
    # Проверяем, не завершил ли пользователь уже
    timer = await sheets_manager.async_get_timer(telegram_id)
    if timer and str(timer.get('completed', '')).upper() == 'YES':
        logger.info(f'Пользователь {telegram_id} уже завершил — пропускаем')
        return

    try:
        await bot.send_message(
            telegram_id,
            '⏰⏰ Прошло 30 минут\n\n'
            'Пожалуйста, завершите исследование в ближайшее время, '
            'если вы еще этого не сделали.\n\n'
            'Нам очень важны ваши ответы!\n\n'
            'После завершения необходимо нажать кнопку ниже.',
            reply_markup=reminder_keyboard(),
        )
        await sheets_manager.async_update_timer_field(
            telegram_id, 'first_reminder_sent', 'YES'
        )
    except Exception as e:
        logger.error(
            f'Ошибка отправки 1-го напоминания для {telegram_id}: {e}',
            exc_info=True,
        )


async def _send_second_reminder(bot: Bot, telegram_id: int):
    """Отправить второе напоминание (через 45 мин)."""
    timer = await sheets_manager.async_get_timer(telegram_id)
    if timer and str(timer.get('completed', '')).upper() == 'YES':
        return

    try:
        await bot.send_message(
            telegram_id,
            '⏰⏰ ПОСЛЕДНЕЕ НАПОМИНАНИЕ\n\n'
            'Прошло 45 минут с начала тестирования на сайте.\n\n'
            'Пожалуйста, завершите исследование в ближайшее время. '
            'Спасибо вам большое.\n\n'
            'После завершения обязательно нажмите кнопку ниже!',
            reply_markup=reminder_keyboard(),
        )
        await sheets_manager.async_update_timer_field(
            telegram_id, 'second_reminder_sent', 'YES'
        )
    except Exception as e:
        logger.error(
            f'Ошибка отправки 2-го напоминания для {telegram_id}: {e}',
            exc_info=True,
        )


async def _send_final_message(bot: Bot, telegram_id: int):
    """Отправить финальное сообщение (через 60 мин)."""
    timer = await sheets_manager.async_get_timer(telegram_id)
    if timer and str(timer.get('completed', '')).upper() == 'YES':
        return

    try:
        await bot.send_message(
            telegram_id,
            '⏱ Время истекло\n\n'
            'Спасибо за участие в исследовании!\n\n'
            'Если вы еще не завершили тестирование на сайте, '
            'пожалуйста, сделайте это как можно скорее. '
            'Спасибо огромное за вашу помощь.\n\n'
            'После завершения нажмите:',
            reply_markup=final_completed_keyboard(),
        )
    except Exception as e:
        logger.error(
            f'Ошибка отправки финального сообщения для {telegram_id}: {e}',
            exc_info=True,
        )


# ===== Обработка ответов на напоминания =====

@router.callback_query(F.data == 'site_completed')
async def on_site_completed(callback: CallbackQuery, state: FSMContext):
    """Пользователь завершил тестирование на сайте."""
    await callback.answer('Спасибо! 🎉')

    telegram_id = callback.from_user.id

    # Обновляем статус в основной таблице
    try:
        await sheets_manager.async_mark_website_completed(telegram_id)
        await sheets_manager.async_update_timer_field(telegram_id, 'completed', 'YES')
    except Exception as e:
        logger.error(f'Ошибка обновления статуса: {e}', exc_info=True)

    # Отменяем все напоминания для этого пользователя
    if scheduler:
        for job_id in [
            f'reminder_1_{telegram_id}',
            f'reminder_2_{telegram_id}',
            f'reminder_final_{telegram_id}',
        ]:
            try:
                scheduler.remove_job(job_id)
            except Exception:
                pass  # Задача уже выполнена или не существует

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
