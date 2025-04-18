import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg

from handlers.base import router as base_router
from handlers.settings import router as settings_router
from services.currency import get_usd_change
from services.news import get_top_news
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE, DOMAIN, USE_WEBHOOK, WEBHOOK_SECRET

# Webhook configuration
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def send_briefing(app: web.Application):
    """
    Send briefing to users whose notify_time matches current time.
    """
    bot: Bot = app["bot"]
    db: asyncpg.Pool = app["db"]
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo(TIMEZONE))
        current_time = now.replace(second=0, microsecond=0).time()

        rows = await db.fetch(
            "SELECT chat_id, modules FROM users WHERE notify_time = $1",
            current_time
        )
        for chat_id, modules in rows:
            texts = []
            if "currency" in modules:
                texts.append(await get_usd_change())
            if "news" in modules:
                texts.append(await get_top_news())
            if texts:
                message_text = "\n\n".join(texts)
                await bot.send_message(chat_id, message_text)
    except Exception:
        logging.exception("Error sending briefing")

async def on_startup(app: web.Application):
    """
    Initialize DB, scheduler, webhook and bot commands.
    """
    # Initialize database pool
    app["db"] = await asyncpg.create_pool(DATABASE_URL)
    app["bot"].db = app["db"]

    # Set bot commands
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="get_briefing_now", description="Получить брифинг сейчас"),
        BotCommand(command="settings", description="Открыть настройки"),
    ]
    await app["bot"].set_my_commands(commands)

    # Scheduler: run every minute, function filters by user time
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, 'cron', minute='*', args=(app,))
    scheduler.start()

    # Configure webhook
    bot: Bot = app["bot"]
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    """
    Cleanup on shutdown: remove webhook and close resources.
    """
    await app["bot"].delete_webhook()
    await app["db"].close()
    await app["dp"].storage.close()
    await app["bot"].session.close()


def create_app() -> web.Application:
    """
    Create aiohttp web application with Aiogram integration.
    """
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    # Create web app
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    # Register startup and shutdown
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Register webhook handler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    return app

async def send_briefing_poll(bot: Bot, db: asyncpg.Pool):
    """
    Send briefing to all users (polling mode).
    """
    try:
        rows = await db.fetch("SELECT chat_id, modules FROM users")
        for chat_id, modules in rows:
            texts = []
            if "currency" in modules:
                texts.append(await get_usd_change())
            if "news" in modules:
                texts.append(await get_top_news())
            if texts:
                message_text = "\n\n".join(texts)
                await bot.send_message(chat_id, message_text)
    except Exception:
        logging.exception("Error sending briefing (polling)")

async def start_polling():
    """
    Run bot in long polling mode for local debugging.
    """
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    db = await asyncpg.create_pool(DATABASE_URL)
    bot.db = db

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing_poll, 'cron', minute='0', args=(bot, db))
    scheduler.start()

    print("Starting polling mode...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if USE_WEBHOOK.lower() == "true":
        app = create_app()
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    else:
        asyncio.run(start_polling())