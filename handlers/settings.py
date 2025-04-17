from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils import keyboard

router = Router()

class Settings(StatesGroup):
    waiting_time = State()
    choosing_modules = State()

@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, state: FSMContext):
    await message.answer("Во сколько слать брифинг? (HH:MM)")
    await state.set_state(Settings.waiting_time)

@router.message(Settings.waiting_time)
async def set_time(message: Message, state: FSMContext):
    # валидация времени…
    await state.update_data(time=message.text)
    # тут показываем InlineKeyboard с тремя кнопками — Погода, Валюта, Новости
    await message.answer("Выберите модули", reply_markup=...)
    await state.set_state(Settings.choosing_modules)

@router.callback_query(Settings.choosing_modules)
async def set_modules(callback, state: FSMContext):
    # сохраняем JSON списка включённых сервисов
    await state.update_data(modules=[...])
    data = await state.get_data()
    # пишем в БД chat_id, time, modules
    await save_settings(callback.from_user.id, data["time"], data["modules"])
    await callback.message.edit_text("Готово! Ежедневный брифинг настроен.")
    await state.clear()