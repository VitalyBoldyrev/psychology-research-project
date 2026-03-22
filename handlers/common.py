"""Общие хэндлеры — обработка неизвестных сообщений, rate limiting."""

import logging
import time
from collections import defaultdict

from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()

# Rate limiting: {telegram_id: timestamp последнего сообщения}
_last_message_time: dict[int, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 1.0


@router.message()
async def unknown_message(message: Message):
    """Обработка неизвестных сообщений (вне состояний FSM)."""
    telegram_id = message.from_user.id
    now = time.time()

    # Rate limiting
    if now - _last_message_time[telegram_id] < RATE_LIMIT_SECONDS:
        return  # Игнорируем слишком частые сообщения

    _last_message_time[telegram_id] = now

    await message.answer(
        'Используйте команду /start для начала работы с ботом.\n'
        'Для доступа к панели администратора: /admin'
    )
