"""Flask-приложение для работы бота через webhook на PythonAnywhere.

Вместо long polling (bot.py) используется webhook:
Telegram отправляет обновления POST-запросом на наш URL.
"""

import asyncio
import logging
import sys
import threading

from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

import config
from handlers import start, testing, admin, timers, common

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger(__name__)

session = AiohttpSession(proxy=config.PROXY_URL) if config.PROXY_URL else None
bot = Bot(token=config.BOT_TOKEN, session=session)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(testing.router)
dp.include_router(admin.router)
dp.include_router(timers.router)
dp.include_router(common.router)

_loop = asyncio.new_event_loop()
_loop_started = False
_loop_lock = threading.Lock()


def _ensure_loop_running():
    """Start the background event loop lazily (survives uWSGI fork)."""
    global _loop_started
    if _loop_started:
        return
    with _loop_lock:
        if _loop_started:
            return
        t = threading.Thread(target=_loop.run_forever, daemon=True)
        t.start()
        _loop_started = True
        logger.info('Background event loop started')


# Flask app
app = Flask(__name__)

WEBHOOK_PATH = f'/webhook/{config.BOT_TOKEN}'


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    _ensure_loop_running()
    data = request.json
    logger.info(f'Получен update: {data.get("update_id", "?")}')
    try:
        update = Update.model_validate(data, context={"bot": bot})
        future = asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, update), _loop
        )
        future.result(timeout=120)
    except Exception as e:
        logger.error(f'Ошибка обработки update: {e}', exc_info=True)
    return jsonify({'ok': True})


@app.route('/')
def index():
    return 'Bot is running'
