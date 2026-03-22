"""Flask-приложение для работы бота через webhook на PythonAnywhere.

Вместо long polling (bot.py) используется webhook:
Telegram отправляет обновления POST-запросом на наш URL.
"""

import asyncio
import logging
import sys

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

# Flask app
app = Flask(__name__)

WEBHOOK_PATH = f'/webhook/{config.BOT_TOKEN}'


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    data = request.json
    logger.info(f'Получен update: {data.get("update_id", "?")}')
    try:
        update = Update.model_validate(data, context={"bot": bot})
        _loop.run_until_complete(dp.feed_update(bot, update))
    except Exception as e:
        logger.error(f'Ошибка обработки update: {e}', exc_info=True)
    return jsonify({'ok': True})


@app.route('/')
def index():
    return 'Bot is running'
