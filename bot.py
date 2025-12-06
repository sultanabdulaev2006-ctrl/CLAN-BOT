import os
import json
import aiohttp
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# ----------------------------
# НАСТРОЙКИ
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WAIT_GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------
# FSM для клана
# ----------------------------
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()

# FSM для Ранг Кинг
class KingForm(StatesGroup):
    gmail = State()
    password = State()

# ----------------------------
# LOGIN и SET RANK (асинхронно)
# ----------------------------
FIREBASE_API_KEY = 'AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM'
FIREBASE_LOGIN_URL = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={FIREBASE_API_KEY}"
RANK_URL = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"

async def async_login(email, password):
    payload = {
        "clientType": "CLIENT_TYPE_ANDROID",
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    headers = {
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(FIREBASE_LOGIN_URL, headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status == 200 and "idToken" in data:
                return data["idToken"]
            return None

async def async_set_rank(token):
    rating_data = {k: 100000 for k in [
        "cars", "car_fix", "car_collided", "car_exchange", "car_trade", "car_wash",
        "slicer_cut", "drift_max", "drift", "cargo", "delivery", "taxi", "levels", "gifts",
        "fuel", "offroad", "speed_banner", "reactions", "police", "run", "real_estate",
        "t_distance", "treasure", "block_post", "push_ups", "burnt_tire", "passanger_distance"
    ]}
    rating_data["time"] = 10000000000
    rating_data["race_win"] = 3000

    payload = {"data": json.dumps({"RatingData": rating_data})}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "okhttp/3.12.13"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(RANK_URL, headers=headers, json=payload) as resp:
            return resp.status == 200

# ----------------------------
# Главное меню /start
# ----------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Ранг Кинг", callback_data="choice_king")],
        [InlineKeyboardButton(text="🛡 Вступить в клан", callback_data="choice_clan")]
    ])
    await message.answer("Выбери действие:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("choice_"))
async def handle_choice(callback: types.CallbackQuery, state: FSMContext):
    choice = callback.data.split("_")[1]
    await callback.message.edit_reply_markup()
    
    if choice == "king":
        await state.set_state(KingForm.gmail)
        await callback.message.answer("📧 Введи Gmail от игрового аккаунта:")
    elif choice == "clan":
        await state.set_state(Form.age)
        await callback.message.answer("🔞 Сколько тебе лет?")

# ----------------------------
# FSM Ранг Кинг
# ----------------------------
@dp.message(KingForm.gmail)
async def king_password(message: types.Message, state: FSMContext):
    await state.update_data(gmail=message.text)
    await state.set_state(KingForm.password)
    await message.answer("🔒 Введи пароль:")

@dp.message(KingForm.password)
async def run_king_script(message: types.Message, state: FSMContext):
    data = await state.get_data()
    gmail = data["gmail"]
    password = message.text

    await message.answer("🔐 Выполняю логин и установку ранга...")
    token = await async_login(gmail, password)
    if not token:
        await message.answer("❌ Ошибка входа.")
    else:
        success = await async_set_rank(token)
        if success:
            await message.answer("✅ RANG установлен!")
        else:
            await message.answer("❌ Ошибка при установке.")
    await state.clear()

# ----------------------------
# FSM Клан
# ----------------------------
@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    age = message.text
    if not age.isdigit() or int(age) < 12:
        await message.answer("❌ Неверный возраст. Укажи числом.")
        return
    await state.update_data(age=age)
    await state.set_state(Form.nickname)
    await message.answer("🎮 Напиши игровой ник.")

@dp.message(Form.nickname)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой ID из CPM.")

@dp.message(Form.game_id)
async def finish_clan(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await message.answer("📝 Твоя заявка обрабатывается, пожалуйста, подождите...")
    now = datetime.now().strftime("%d.%m.%Y, %H:%M")
    admin_text = (
        "📥 Новая заявка в клан XARIZMA!\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n\n"
        f"🔞 Возраст: {data['age']}\n"
        f"🎮 Игровой ник: {data['nickname']}\n"
        f"💻 Игровой ID: {data['game_id']}\n"
        f"🕒 Время: {now}"
    )
    keyboard_admin = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
        ]
    ])
    try:
        await bot.send_message(ADMIN_ID, admin_text, reply_markup=keyboard_admin)
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке админу: {str(e)}")
    await state.clear()

# ----------------------------
# CALLBACK — Админ (Отклонить)
# ----------------------------
@dp.callback_query(lambda callback: callback.data.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"join_wait:{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"no_join:{user_id}")
        ]
    ])
    await bot.send_message(user_id,
        "❌ Твоя заявка отклонена.\n"
        "Свободных мест нет, но можешь войти в группу ожидания.\n"
        "Отправить ссылку?",
        reply_markup=keyboard
    )

@dp.callback_query(lambda callback: callback.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Отлично! Вот ссылка на группу ожидания:\n{WAIT_GROUP_LINK}")
    await callback.answer("✅ Ссылка на группу ожидания отправлена", show_alert=True)

# ----------------------------
# Запуск через web service и polling
# ----------------------------
async def on_start(request):
    return web.Response(text="Bot is running")

async def on_shutdown(app):
    await bot.close()

async def start_polling():
    print("Бот запущен через Polling")
    await dp.start_polling(bot)

async def create_app():
    app = web.Application()
    app.router.add_get('/', on_start)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    app = asyncio.run(create_app())
    loop = asyncio.get_event_loop()
    loop.create_task(start_polling())
    web.run_app(app, host='0.0.0.0', port=8080)
