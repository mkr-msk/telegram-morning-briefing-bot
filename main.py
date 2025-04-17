import os
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncpg
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from handlers.settings import router as settings_router
from services.currency import get_usd_change
from services.news import get_top_news
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE, DOMAIN, USE_WEBHOOK

# пути и URL для webhook
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8000))
WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")

async def send_briefing(bot: Bot, db):
    rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
    for chat_id, t, modules in rows:
        texts = []
        if "currency" in modules:
            texts.append(await get_usd_change())
        if "news" in modules:
            texts.append(get_top_news())
        if texts:
            await bot.send_message(chat_id, "\n\n".join(texts))

async def on_startup(app: web.Application):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    print(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    await bot.session.close()
    await dp.storage.close()

# 1) Инициализация бота и диспетчера на глобальном уровне
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()
dp.include_routers(settings_router)

async def main():
    # 2) Подключение к БД
    db = await asyncpg.create_pool(DATABASE_URL)
    dp["db"] = db

    # 3) Планировщик задач
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, "cron", hour="*", minute=0, args=(bot, db))
    scheduler.start()

    # 4) Запуск
    if USE_WEBHOOK.lower() == "true":
        app = web.Application()
        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)

        # Webhook handler
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=WEBHOOK_SECRET
        ).register(app, path=WEBHOOK_PATH)

        setup_application(app, dp, bot=bot)

        print(f"Запускаем webhook-сервер на https://{DOMAIN}{WEBHOOK_PATH}")
        web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

    else:
        print("Запускаем polling (отладка локально)")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())