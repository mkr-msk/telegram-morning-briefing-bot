# handlers/settings.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import time as dt_time

router = Router()

# FSM состояния
class Settings(StatesGroup):
    waiting_time = State()
    waiting_modules = State()

@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Во сколько слать брифинг? (HH:MM)")
    await state.set_state(Settings.waiting_time)

@router.message(Settings.waiting_time)
async def set_time(message: Message, state: FSMContext):
    text = message.text.strip()
    import re
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", text):
        return await message.answer("Неверный формат! Введите время в формате HH:MM.")

    await state.update_data(time=text, modules=[])

    builder = InlineKeyboardBuilder()
    builder.button(text="📰 Новости", callback_data="module_news")
    builder.button(text="💱 Курс валют", callback_data="module_currency")
    builder.adjust(2)
    builder.button(text="✅ Готово", callback_data="modules_done")

    await message.answer("Выберите модули для брифинга:", reply_markup=builder.as_markup())
    await state.set_state(Settings.waiting_modules)

@router.callback_query(Settings.waiting_modules, F.data.startswith("module_"))
async def toggle_module(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    modules = data.get("modules", [])
    module = callback.data.split("_", 1)[1]

    if module in modules:
        modules.remove(module)
        text = f"{module.capitalize()} отключен"
    else:
        modules.append(module)
        text = f"{module.capitalize()} включен"

    await state.update_data(modules=modules)

    builder = InlineKeyboardBuilder()
    for mod, label in [("news", "📰 Новости"), ("currency", "💱 Курс валют")]:
        prefix = "✅ " if mod in modules else ""
        builder.button(text=prefix + label, callback_data=f"module_{mod}")
    builder.adjust(2)
    builder.button(text="✅ Готово", callback_data="modules_done")

    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await callback.answer(text)

@router.callback_query(Settings.waiting_modules, F.data == "modules_done")
async def modules_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    time_str = data.get("time")
    modules = data.get("modules", [])

    # Преобразуем строку времени в объект datetime.time
    h, m = map(int, time_str.split(':'))
    time_obj = dt_time(hour=h, minute=m)

    # Сериализуем список модулей в JSON-строку
    import json
    modules_json = json.dumps(modules)

    # Сохраняем настройки в БД
    await callback.bot.db.execute(
        "UPDATE users SET notify_time = $1, modules = $2 WHERE chat_id = $3",
        time_obj, modules_json, callback.from_user.id
    )

    await callback.message.edit_text("✅ Настройки сохранены!")
    await callback.answer()
    await state.clear()