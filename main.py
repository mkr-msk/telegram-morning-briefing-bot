# main.py
import os
import asyncio
from aiohttp import web
import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers.base import router as base_router
from handlers.settings import router as settings_router
from services.currency import get_usd_change
from services.news import get_top_news
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE, DOMAIN, USE_WEBHOOK, WEBHOOK_SECRET

# Webhook settings
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8000))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def send_briefing(bot: Bot, db: asyncpg.Pool):
    rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
    for chat_id, t, modules in rows:
        texts = []
        if "currency" in modules:
            texts.append(await get_usd_change())
        if "news" in modules:
            texts.append(await get_top_news())
        if texts:
            await bot.send_message(chat_id, "\n\n".join(texts))

async def init_app_components():
    # Initialize bot, dispatcher, database, and scheduler
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_routers(base_router, settings_router)

    db = await asyncpg.create_pool(DATABASE_URL)
    bot.db = db

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, "cron", hour="*", minute="0", args=(bot, db))
    scheduler.start()

    return bot, dp

async def on_startup(app: web.Application):
    bot: Bot = app["bot"]
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    bot: Bot = app["bot"]
    dp: Dispatcher = app["dp"]
    await bot.delete_webhook()
    await dp.storage.close()

def start_webhook():
    # Set up components in async context
    bot, dp = asyncio.run(init_app_components())

    # Create aiohttp app and register handlers
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    print(f"Запускаем webhook-сервер на {WEBHOOK_URL}")
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

async def start_polling():
    bot, dp = await init_app_components()
    print("Запускаем polling (отладка локально)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if USE_WEBHOOK.lower() == "true":
        start_webhook()
    else:
        asyncio.run(start_polling())