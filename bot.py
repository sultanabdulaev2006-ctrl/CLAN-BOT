import os
import asyncio
from datetime import datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ----------------------------
# CONFIG
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WAIT_GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------
# FSM
# ----------------------------
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()


# ----------------------------
# START
# ----------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]],
        resize_keyboard=True
    )

    await message.answer(
        f"🍀 Привет, {message.from_user.first_name}! Хочешь оставить заявку на вступление в клан?",
        reply_markup=keyboard
    )


# ----------------------------
# АНКЕТА
# ----------------------------
@dp.message(lambda m: m.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())


@dp.message(lambda m: m.text == "❌ Нет")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😌 Хорошо. Возможно, твоя харизма ещё раскрывается. Успех любит время. ☘️",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    age = message.text

    if not age.isdigit() or int(age) < 12:
        await message.answer("❌ Неверный возраст. Укажи возраст числом.")
        return

    await state.update_data(age=age)
    await state.set_state(Form.nickname)
    await message.answer("🎮 Напиши свой игровой ник.")


@dp.message(Form.nickname)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой игровой ID из CPM.")


@dp.message(Form.game_id)
async def finish_form(message: types.Message, state: FSMContext):
    await state.update_data(game_id=message.text)
    data = await state.get_data()

    # Сообщение пользователю
    await message.answer("📝 Твоя заявка обрабатывается, пожалуйста, подождите...")

    # Формируем текст админу
    now = datetime.now().strftime("%d.%m.%Y, %H:%M")
    admin_text = (
        "📥 Новая заявка в клан XARIZMA!\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n\n"
        f"🔞 Возраст: {data['age']}\n"
        f"🎮 Ник: {data['nickname']}\n"
        f"🆔 ID: {data['game_id']}\n"
        f"🕒 Время: {now}"
    )

    keyboard_admin = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
        ]
    ])

    # Отправляем админу
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=keyboard_admin)

    await state.clear()


# ----------------------------
# CALLBACK — Admin Reject
# ----------------------------
@dp.callback_query(lambda c: c.data.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"join_wait:{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"no_join:{user_id}")
        ]
    ])

    await bot.send_message(
        user_id,
        "❌ Твоя заявка отклонена.\n"
        "Свободных мест нет. Хочешь ссылку на группу ожидания?",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Ссылка на группу ожидания:\n{WAIT_GROUP_LINK}")
    await callback.answer("Ссылка отправлена!", show_alert=True)


# ----------------------------
# RENDER: Web Server + Polling
# ----------------------------
async def handle_root(request):
    return web.Response(text="Bot is running ✓")


async def start_bot():
    """Запуск Telegram polling"""
    await dp.start_polling(bot)


async def init_app():
    """Создание aiohttp приложения и запуск polling параллельно"""
    app = web.Application()
    app.router.add_get("/", handle_root)

    # Запускаем polling как фоновую задачу
    asyncio.create_task(start_bot())

    return app


if __name__ == "__main__":
    # Запускаем aiohttp сервер (Render требует web-сервер)
    web.run_app(init_app(), host="0.0.0.0", port=8080)
