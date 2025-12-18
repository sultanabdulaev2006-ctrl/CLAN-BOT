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

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WAIT_GROUP_LINK = "https://t.me/+8XWLNODTnV1mNzMy"
WAIT_GROUP_CHAT_ID = -1003156012968
WAIT_GROUP_TOPIC_ID = 20

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

pending_users = {}
messages_map = {}

class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()

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
    await message.answer("📝 Твоя заявка обрабатывается, пожалуйста, подождите...")
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
    await bot.send_message(ADMIN_ID, admin_text, reply_markup=keyboard_admin)
    pending_users[message.from_user.id] = {"nickname": data['nickname'], "game_id": data['game_id']}
    await state.clear()

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
        "Свободных мест нет, но можешь войти в группу ожидания.\n"
        "Отправить ссылку?",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Ссылка на группу ожидания:\n{WAIT_GROUP_LINK}")
    await callback.answer("Ссылка отправлена!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("approve:"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, "✅ Ваша заявка одобрена! Добро пожаловать в клан!")
    if user_id not in pending_users:
        pending_users[user_id] = {"nickname": "неизвестно", "game_id": "неизвестно"}
    try:
        await bot.approve_chat_join_request(chat_id=WAIT_GROUP_CHAT_ID, user_id=user_id)
    except Exception as e:
        print("Ошибка при авто-одобрении:", e)

@dp.chat_member()
async def on_chat_member(event: types.ChatMemberUpdated):
    user_id = event.from_user.id
    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status
    if old_status in ["left", "kicked"] and new_status == "member":
        user_data = pending_users.get(user_id)
        if user_data:
            try:
                msg = await bot.send_message(
                    chat_id=WAIT_GROUP_CHAT_ID,
                    message_thread_id=WAIT_GROUP_TOPIC_ID,
                    text=f"📌 Новый участник:\n🎮 Ник: {user_data['nickname']}\n🆔 ID: {user_data['game_id']}\n👤 Telegram ID: {user_id}"
                )
                messages_map[user_id] = msg.message_id
                pending_users.pop(user_id, None)
            except Exception as e:
                print("Ошибка отправки данных в топик:", e)
    if old_status in ["member", "administrator"] and new_status in ["left", "kicked"]:
        message_id = messages_map.get(user_id)
        if message_id:
            try:
                await bot.delete_message(chat_id=WAIT_GROUP_CHAT_ID, message_id=message_id)
            except:
                pass
            messages_map.pop(user_id, None)

async def handle_root(request):
    return web.Response(text="Bot is running ✓")

async def start_bot():
    await dp.start_polling(bot)

async def init_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    asyncio.create_task(start_bot())
    return app

if __name__ == "__main__":
    web.run_app(init_app(), host="0.0.0.0", port=8080)
