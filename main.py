# main.py
import os
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg

from handlers.base import router as base_router
from handlers.settings import router as settings_router
from services.currency import get_usd_change
from services.news import get_top_news
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE, DOMAIN, USE_WEBHOOK, WEBHOOK_SECRET

# Настройки webhook
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def send_briefing(app: web.Application):
    """
    Собирает данные и рассылает брифинг пользователям.
    """
    bot: Bot = app["bot"]
    db: asyncpg.Pool = app["db"]
    try:
        rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
        for chat_id, t, modules in rows:
            texts = []
            if "currency" in modules:
                texts.append(await get_usd_change())
            if "news" in modules:
                texts.append(await get_top_news())
            if texts:
                # Объединяем текст с двумя переводами строки между блоками
                await bot.send_message(chat_id, "\n\n".join(texts))
    except Exception:
        logging.exception("Ошибка при отправке брифинга")

async def on_startup(app: web.Application):
    """
    Инициализация БД, планировщика и webhook.
    """
    # 1) Подключаемся к базе
    app["db"] = await asyncpg.create_pool(DATABASE_URL)
    app["bot"].db = app["db"]

    # 2) Планировщик: запуск send_briefing каждый час в 00 минут
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, 'cron', minute='0', args=(app,))
    scheduler.start()

    # 3) Настройка webhook в Telegram
    bot: Bot = app["bot"]
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    """
    Отмена webhook и закрытие ресурсов.
    """
    await app["bot"].delete_webhook()
    await app["db"].close()
    await app["dp"].storage.close()
    await app["bot"].session.close()

# Функция для создания aiohttp–приложения и интеграции Aiogram

def create_app() -> web.Application:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Регистрируем webhook handler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    return app

# Polling режим для локальной отладки

async def send_briefing_poll(bot: Bot, db: asyncpg.Pool):
    """
    Аналог send_briefing для polling: рассылает брифинг пользователям.
    """
    try:
        rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
        for chat_id, t, modules in rows:
            texts = []
            if "currency" in modules:
                texts.append(await get_usd_change())
            if "news" in modules:
                texts.append(await get_top_news())
            if texts:
                await bot.send_message(chat_id, "\n\n".join(texts))
    except Exception:
        logging.exception("Ошибка при отправке брифинга")

async def start_polling():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    db = await asyncpg.create_pool(DATABASE_URL)
    bot.db = db

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing_poll, 'cron', minute='0', args=(bot, db))
    scheduler.start()

    print("Запускаем polling (отладка локально)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if USE_WEBHOOK.lower() == "true":
        app = create_app()
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    else:
        asyncio.run(start_polling())