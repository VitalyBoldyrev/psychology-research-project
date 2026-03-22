"""Flask-приложение для работы бота через webhook на PythonAnywhere.

Вместо long polling (bot.py) используется webhook:
Telegram отправляет обновления POST-запросом на наш URL.
"""

import asyncio
import logging
import queue
import sys
import threading

from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers import start, testing, admin, timers, common

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(testing.router)
dp.include_router(admin.router)
dp.include_router(timers.router)
dp.include_router(common.router)

# Фоновый поток с asyncio event loop для обработки обновлений.
# Worker использует бесконечную корутину, что позволяет asyncio.create_task
# (например, отложенное напоминание через 15 мин) работать параллельно
# с обработкой очереди.
_update_queue: queue.Queue = queue.Queue()


def _worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _main():
        while True:
            data = await loop.run_in_executor(None, _update_queue.get)
            try:
                update = Update.model_validate(data, context={"bot": bot})
                await dp.feed_update(bot, update)
            except Exception as e:
                logger.error(f'Ошибка обработки update: {e}', exc_info=True)

    loop.run_until_complete(_main())


_worker_thread = threading.Thread(target=_worker, daemon=True)
_worker_thread.start()

# Flask app
app = Flask(__name__)

WEBHOOK_PATH = f'/webhook/{config.BOT_TOKEN}'


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    _update_queue.put(request.json)
    return jsonify({'ok': True})


@app.route('/')
def index():
    return 'Bot is running'
