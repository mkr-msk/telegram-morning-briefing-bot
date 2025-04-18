# handlers/base.py
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📨 Получить брифинг сейчас"),
         KeyboardButton(text="⚙️ Настройки")],
    ],
    resize_keyboard=True
)

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    """
    Сохраняем пользователя и показываем главное меню.
    """
    db = message.bot.db
    await db.execute(
        """
        INSERT INTO users(chat_id, notify_time, modules)
        VALUES($1, '09:00', '[]')
        ON CONFLICT DO NOTHING
        """,
        message.chat.id
    )
    await message.answer(
        "Привет! Я — бот «Утренний брифинг». С помощью меню ты сможешь настраивать получение курса валют и новостей автоматически.",
        reply_markup=main_kb
    )

@router.message(F.text == "📨 Получить брифинг сейчас")
async def cmd_send_now(message: Message):
    """
    Отправляем брифинг сразу.
    """
    db = message.bot.db
    row = await db.fetchrow(
        "SELECT modules FROM users WHERE chat_id = $1",
        message.chat.id
    )
    modules = row["modules"] or []
    texts = []
    # Курс валют
    if "currency" in modules:
        from services.currency import get_usd_change
        texts.append(await get_usd_change())
    # Новости (теперь асинхронные)
    if "news" in modules:
        from services.news import get_top_news
        texts.append(await get_top_news())

    if not texts:
        await message.answer("У вас не включено ни одного модуля: зайдите в ⚙️ Настройки.")
    else:
        await message.answer("\n\n".join(texts))