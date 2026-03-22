"""Скрипт для установки/удаления webhook.

Использование:
    python set_webhook.py          — установить webhook
    python set_webhook.py delete   — удалить webhook (для возврата к long polling)
"""

import asyncio
import sys

from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
import config


async def main():
    session = AiohttpSession(proxy=config.PROXY_URL) if config.PROXY_URL else None
    bot = Bot(token=config.BOT_TOKEN, session=session)

    if len(sys.argv) > 1 and sys.argv[1] == 'delete':
        await bot.delete_webhook()
        print('Webhook удалён. Можно запускать bot.py (long polling).')
    else:
        if not config.WEBHOOK_URL:
            print('Ошибка: WEBHOOK_URL не задан в .env')
            print('Пример: WEBHOOK_URL=https://YOUR_USERNAME.pythonanywhere.com')
            sys.exit(1)

        webhook_url = f'{config.WEBHOOK_URL}/webhook/{config.BOT_TOKEN}'
        await bot.set_webhook(webhook_url)
        print(f'Webhook установлен: {webhook_url}')

    await bot.session.close()


if __name__ == '__main__':
    asyncio.run(main())
