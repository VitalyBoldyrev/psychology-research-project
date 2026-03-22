"""Главный файл запуска Telegram-бота (long polling, для локальной разработки).

Запуск: python bot.py
Для PythonAnywhere используй webapp.py (webhook).
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import start, testing, admin, timers, common

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_errors.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    me = await bot.get_me()
    logger.info(f'Бот запущен: @{me.username} (id={me.id})')


async def on_shutdown(bot: Bot):
    logger.info('Бот остановлен')


async def main():
    if not config.BOT_TOKEN:
        logger.error('BOT_TOKEN не задан! Проверьте файл .env')
        sys.exit(1)

    if not config.SPREADSHEET_ID:
        logger.error('SPREADSHEET_ID не задан! Проверьте файл .env')
        sys.exit(1)

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(testing.router)
    dp.include_router(admin.router)
    dp.include_router(timers.router)
    dp.include_router(common.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info('Запуск polling...')
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
