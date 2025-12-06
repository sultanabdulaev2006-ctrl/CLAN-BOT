import os
import asyncio
import json
import threading
import requests
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
WAIT_GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"  # Ссылка на группу ожидания

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------
# FSM (Состояния) для анкеты клана
# ----------------------------
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()

# ----------------------------
# Ранг Кинг переменные
# ----------------------------
ALLOWED_FILE = "allowed_users.json"
if os.path.exists(ALLOWED_FILE):
    with open(ALLOWED_FILE, "r") as f:
        ALLOWED_USERS = set(json.load(f))
else:
    ALLOWED_USERS = {ADMIN_ID}

def save_allowed():
    with open(ALLOWED_FILE, "w") as f:
        json.dump(list(ALLOWED_USERS), f)

FIREBASE_API_KEY = 'AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM'
FIREBASE_LOGIN_URL = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={FIREBASE_API_KEY}"
RANK_URL = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"
user_states = {}

# ----------------------------
# HELPER FUNCTIONS для Ранг Кинг
# ----------------------------
def login(email, password):
    payload = {
        "clientType": "CLIENT_TYPE_ANDROID",
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)", "Content-Type": "application/json"}
    try:
        response = requests.post(FIREBASE_LOGIN_URL, headers=headers, json=payload)
        data = response.json()
        if response.status_code == 200 and "idToken" in data:
            return data["idToken"]
        else:
            return None
    except:
        return None

def set_rank(token):
    rating_data = {k: 100000 for k in [
        "cars", "car_fix", "car_collided", "car_exchange", "car_trade", "car_wash",
        "slicer_cut", "drift_max", "drift", "cargo", "delivery", "taxi", "levels", "gifts",
        "fuel", "offroad", "speed_banner", "reactions", "police", "run", "real_estate",
        "t_distance", "treasure", "block_post", "push_ups", "burnt_tire", "passanger_distance"
    ]}
    rating_data["time"] = 10000000000
    rating_data["race_win"] = 3000
    payload = {"data": json.dumps({"RatingData": rating_data})}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "okhttp/3.12.13"}
    response = requests.post(RANK_URL, headers=headers, json=payload)
    return response.status_code == 200

def send_welcome(user_id):
    user_states[user_id] = {"step": "await_email"}
    bot.send_message(user_id, "📧 Введи gmail")

# ----------------------------
# START / MAIN MENU
# ----------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Ранг Кинг"), KeyboardButton(text="✅ Вступить в клан")]
        ],
        resize_keyboard=True
    )
    await message.answer(f"Привет, {message.from_user.first_name}! Выбери действие:", reply_markup=keyboard)

# ----------------------------
# ОБРАБОТКА ВЫБОРА В START
# ----------------------------
@dp.message(lambda message: message.text == "✅ Вступить в клан")
async def clan_start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]],
        resize_keyboard=True
    )
    await message.answer("🍀 Хочешь оставить заявку на вступление в клан?", reply_markup=keyboard)

@dp.message(lambda message: message.text == "🎮 Ранг Кинг")
async def rank_king_start(message: types.Message):
    user_id = message.from_user.id
    if user_id in ALLOWED_USERS:
        send_welcome(user_id)
    else:
        await message.answer("⛔ У тебя нет разрешения на использование бота.")

# ----------------------------
# FSM КЛАН
# ----------------------------
@dp.message(lambda message: message.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())

@dp.message(lambda message: message.text == "❌ Нет")
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
        await message.answer("❌ Неверный возраст. Пожалуйста, укажи свой возраст числом.")
        return
    await state.update_data(age=age)
    await state.set_state(Form.nickname)
    await message.answer("🎮 Напиши свой игровой ник.")

@dp.message(Form.nickname)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой ID из CPM.")

@dp.message(Form.game_id)
async def finish_clan(message: types.Message, state: FSMContext):
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
        await message.answer(f"❌ Произошла ошибка при отправке заявки админу: {str(e)}")
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
# Ранг Кинг обработка
# ----------------------------
@dp.message(lambda message: message.from_user.id in ALLOWED_USERS)
async def handle_rank_king(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if user_id not in user_states:
        return

    state = user_states[user_id]
    if state["step"] == "await_email":
        state["email"] = text
        state["step"] = "await_password"
        msg = await message.reply("🔒 Введи пароль")
        state["last_msg_ids"] = [message.message_id, msg.message_id]

    elif state["step"] == "await_password":
        email = state["email"]
        password = text
        messages_to_delete = state.get("last_msg_ids", [])
        messages_to_delete.append(message.message_id)

        msg_login = await message.reply("🔐 Выполняю логин...")
        messages_to_delete.append(msg_login.message_id)

        token = login(email, password)
        if not token:
            msg_error = await message.reply("❌ Ошибка входа.")
            messages_to_delete.append(msg_error.message_id)
        else:
            msg_rank = await message.reply("👑 Rang устанавливается...")
            messages_to_delete.append(msg_rank.message_id)

            success = set_rank(token)
            if success:
                msg_done = await message.reply("✅ RANG установлен!")
            else:
                msg_done = await message.reply("❌ Ошибка при установке.")
            messages_to_delete.append(msg_done.message_id)

        user_states.pop(user_id)

        async def cleanup():
            for msg_id in messages_to_delete:
                try:
                    await bot.delete_message(message.chat.id, msg_id)
                except:
                    pass
            send_welcome(user_id)

        asyncio.create_task(cleanup())

# ----------------------------
# WEB SERVER
# ----------------------------
async def on_start(request):
    return web.Response(text="Bot is running")

async def on_shutdown(app):
    await bot.close()

async def create_app():
    app = web.Application()
    app.router.add_get('/', on_start)
    app.on_shutdown.append(on_shutdown)
    return app

# ----------------------------
# POLLING
# ----------------------------
async def start_polling():
    print("Бот запущен с использованием Polling")
    await dp.start_polling(bot)

# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    async def main():
        # Запуск polling
        asyncio.create_task(start_polling())
        # Запуск web-сервера
        app = await create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
        await site.start()
        print("🚀 Bot and web server are running!")
        while True:
            await asyncio.sleep(3600)

    asyncio.run(main())
