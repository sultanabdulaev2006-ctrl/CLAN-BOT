import os
import asyncio
import threading
from datetime import datetime
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
)
import telebot
import requests
import json

# -------------------------------
# TELEGRAM CONFIG (Aiogram)
# -------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WAIT_GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"
bot_aiogram = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# -------------------------------
# TELEGRAM CONFIG (Telebot)
# -------------------------------
bot_telebot = telebot.TeleBot(BOT_TOKEN)

# -------------------------------
# Flask Web Server Setup
# -------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

async def handle_root(request):
    return web.Response(text="AIoGram bot is running ✓")

async def start_bot_aiogram():
    """Запуск Telegram polling для aiogram"""
    await dp.start_polling(bot_aiogram)

# -------------------------------
# Game Service Configuration (Telebot)
# -------------------------------
FIREBASE_API_KEY = 'YOUR_FIREBASE_API_KEY'
FIREBASE_LOGIN_URL = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={FIREBASE_API_KEY}"
RANK_URL = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"

# -------------------------------
# Aiogram Bot Logic (Клан Бот)
# -------------------------------
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Вступить в клан")],
            [KeyboardButton(text="👑 Ранг Кинг")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"🍀 Привет, {message.from_user.first_name}! Выбери, что хочешь сделать:",
        reply_markup=keyboard
    )

@dp.message(lambda m: m.text == "✅ Вступить в клан")
async def ask_age(message: types.Message, state: FSMContext):
    # Код для клана (не изменяется)
    await state.set_state(Form.age)
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())

@dp.message(lambda m: m.text == "👑 Ранг Кинг")
async def start_rank_king(message: types.Message):
    # Отправляем пользователя в режим ранга
    bot_telebot.send_message(message.chat.id, "📧 Введи gmail для входа в Ранг Кинг.")
    
@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    # Код для клана (не изменяется)
    age = message.text
    if not age.isdigit() or int(age) < 12:
        await message.answer("❌ Неверный возраст. Укажи возраст числом.")
        return

    await state.update_data(age=age)
    await state.set_state(Form.nickname)
    await message.answer("🎮 Напиши свой игровой ник.")

@dp.message(Form.nickname)
async def ask_game_id(message: types.Message, state: FSMContext):
    # Код для клана (не изменяется)
    await state.update_data(nickname=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой игровой ID из CPM.")

@dp.message(Form.game_id)
async def finish_form(message: types.Message, state: FSMContext):
    # Код для клана (не изменяется)
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
    await bot_aiogram.send_message(ADMIN_ID, admin_text, reply_markup=keyboard_admin)
    await state.clear()

# -------------------------------
# Telebot Logic (Ранг Кинг)
# -------------------------------
def login(email, password):
    # Логика для Firebase входа
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
    # Логика для установки ранга
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

    response = requests.post(RANK_URL, headers=headers, json=payload)
    return response.status_code == 200

@bot_telebot.message_handler(commands=['start'])
def start_telebot(message):
    user_id = message.from_user.id
    # Логика для Ранг Кинг
    bot_telebot.send_message(user_id, "📧 Введи gmail")

@bot_telebot.message_handler(func=lambda message: True)
def handle_message(message):
    # Логика для Ранг Кинг
    pass

# -------------------------------
# Запуск обоих ботов параллельно
# -------------------------------
def run_telebot():
    bot_telebot.infinity_polling()

def run_aiogram_bot():
    asyncio.run(start_bot_aiogram())

if __name__ == "__main__":
    # Запускаем оба бота в разных потоках
    threading.Thread(target=run_telebot).start()
    threading.Thread(target=run_aiogram_bot).start()

    # Запускаем Flask сервер (для платформы как Render)
    app.run(host="0.0.0.0", port=8080)
