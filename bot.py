"""Главный файл запуска Telegram-бота для психологического исследования.

Запуск: python bot.py
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from handlers import start, testing, admin, timers, common

# Настройка логирования
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
    """Действия при запуске бота."""
    me = await bot.get_me()
    logger.info(f'Бот запущен: @{me.username} (id={me.id})')


async def on_shutdown(bot: Bot):
    """Действия при остановке бота."""
    logger.info('Бот остановлен')


async def main():
    """Главная функция запуска."""
    if not config.BOT_TOKEN:
        logger.error('BOT_TOKEN не задан! Проверьте файл .env')
        sys.exit(1)

    if not config.SPREADSHEET_ID:
        logger.error('SPREADSHEET_ID не задан! Проверьте файл .env')
        sys.exit(1)

    # Инициализация бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация планировщика задач
    scheduler = AsyncIOScheduler()
    timers.setup_scheduler(scheduler)
    scheduler.start()
    logger.info('Планировщик задач запущен')

    # Подключение роутеров (порядок важен!)
    dp.include_router(start.router)
    dp.include_router(testing.router)
    dp.include_router(admin.router)
    dp.include_router(timers.router)
    dp.include_router(common.router)  # должен быть последним

    # Регистрация обработчиков жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск polling
    logger.info('Запуск polling...')
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
