from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, DATABASE_URL, TIMEZONE
# from services.weather import get_weather
from services.currency import get_usd_change
from services.news import get_top_news
from handlers.settings import router as settings_router
import asyncpg
import asyncio

async def main():
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(settings_router)

    db = await asyncpg.create_pool(DATABASE_URL)
    dp['db'] = db

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(send_briefing, "cron", hour="*", minute=0, args=(bot, db))
    scheduler.start()

    await dp.start_polling(bot)

async def send_briefing(bot, db):
    rows = await db.fetch("SELECT chat_id, notify_time, modules FROM users")
    for chat_id, t, modules in rows:
        # сравнить текущее время с t — если совпадает, то:
        texts = []
        if 'weather' in modules:
            pass
            # texts.append(await get_weather())
        if 'currency' in modules:
            texts.append(await get_usd_change())
        if 'news' in modules:
            texts.append(get_top_news())
        await bot.send_message(chat_id, "\n\n".join(texts))

if __name__ == "__main__":
    asyncio.run(main())