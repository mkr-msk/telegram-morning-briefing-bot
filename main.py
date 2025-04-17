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

# Константы webhook
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", "8000"))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

async def send_briefing(app: web.Application):
    """
    Забирает данные из БД и рассылает брифинг всем пользователям.
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
                await bot.send_message(chat_id, "\n\n".join(texts))
    except Exception:
        logging.exception("Ошибка при отправке брифинга")

async def on_startup(app: web.Application):
    """
    Создаёт пул соединений, настраивает бот, диспетчер, планировщик и вебхук.
    """
    # 1) Инициализация DB
    app["db"] = await asyncpg.create_pool(DATABASE_URL)
    # Доступ к DB из хэндлеров
    app["bot"].db = app["db"]

    # 2) Инициализация планировщика
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    # Создаём задачу, вызывающую send_briefing каждое полночасие
    scheduler.add_job(lambda: asyncio.create_task(send_briefing(app)),
                      "cron", minute="0")
    scheduler.start()

    # 3) Настройка webhook в Telegram
    bot: Bot = app["bot"]
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    """
    Вызывается при остановке приложения: удаляем вебхук и закрываем ресурсы.
    """
    # Завершаем планировщик
    for job in AsyncIOScheduler.get_jobs():
        job.remove()
    await app["bot"].delete_webhook()
    # Закрываем БД и хранилище состояний
    await app["db"].close()
    await app["dp"].storage.close()

    # Закрываем сессию бота
    await app["bot"].session.close()

def create_app() -> web.Application:
    """
    Конструирует aiohttp-приложение с интеграцией Aiogram (webhook).
    """
    # 1) Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    # 2) Создаём приложение и сохраняем компоненты
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp

    # 3) Startup/Shutdown
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # 4) Регистрируем webhook handler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)

    return app

async def start_polling():
    """
    Запуск бота в режиме long polling для локальной отладки.
    """
    # Инициализируем бота и диспетчер
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(base_router)
    dp.include_router(settings_router)

    # Подключаем БД
    db = await asyncpg.create_pool(DATABASE_URL)
    bot.db = db

    # Планировщик
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(lambda: asyncio.create_task(send_briefing({"bot":bot, "db":db})),
                      "cron", minute="0")
    scheduler.start()

    print("Запускаем polling (отладка локально)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    if USE_WEBHOOK.lower() == "true":
        app = create_app()
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
    else:
        asyncio.run(start_polling())