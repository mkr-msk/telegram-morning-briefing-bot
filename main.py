import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
from aiohttp import web

from handlers.settings import router as settings_router
from services.currency import get_usd_change
from services.news import get_top_news
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE, DOMAIN, USE_WEBHOOK

# пути и URL для webhook
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8000))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def send_briefing(bot: Bot, db):
    rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
    now = asyncio.get_event_loop().time()  # можно заменить на сравнение по времени из БД
    for chat_id, t, modules in rows:
        texts = []
        if "currency" in modules:
            texts.append(await get_usd_change())
        if "news" in modules:
            texts.append(get_top_news())
        if texts:
            await bot.send_message(chat_id, "\n\n".join(texts))

async def main():
    # 1) Создаём бот и диспетчер
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    dp.include_routers(settings_router)

    # 2) Подключаемся к БД
    db = await asyncpg.create_pool(DATABASE_URL)
    dp["db"] = db

    # 3) Настраиваем планировщик
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, "cron", hour="*", minute=0, args=(bot, db))
    scheduler.start()

    # 4) Режим запуска
    if USE_WEBHOOK.lower() == "true":
        # Webhook
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(WEBHOOK_URL)

        app = web.Application()
        configure_app(app, dp, bot=bot, path=WEBHOOK_PATH)
        print(f"Запускаем webhook на {WEBHOOK_URL}")
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    else:
        # Long polling (локально)
        print("Запускаем polling (для локальной отладки)")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())