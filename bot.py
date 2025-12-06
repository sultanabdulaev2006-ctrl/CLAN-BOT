import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
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
# FSM (Состояния)
# ----------------------------
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()
    screenshot = State()

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
@dp.message(Text("✅ Да"))
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Text("❌ Нет"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😌 Хорошо. Возможно, твоя харизма ещё раскрывается. Успех любит время. ☘️",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    age = message.text
    # Проверка возраста
    if not age.isdigit() or int(age) < 12:  # Минимальный возраст 12 лет
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
async def ask_screenshot(message: types.Message, state: FSMContext):
    await state.update_data(game_id=message.text)
    await state.set_state(Form.screenshot)
    await message.answer("📸 Отлично! Теперь отправь скриншот из своего профиля CPM 👇🏻")

# ----------------------------
# ПРОВЕРКА, ЧТО ОТПРАВЛЕНО ИМЕННО ФОТО
# ----------------------------
@dp.message(Form.screenshot)
async def ask_for_photo(message: types.Message):
    # Если отправлено не фото, просим отправить фото
    if not message.photo:
        await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")
        return

@dp.message(Form.screenshot, Text.photo)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id  # Получаем последнее фото (наибольшее качество)

    # Отправка сообщения пользователю, что заявка обрабатывается
    await message.answer("📝 Твоя заявка обрабатывается, пожалуйста, подождите...")

    # Отправка заявки админу
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
        # Отправляем заявку админу
        await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=keyboard_admin)
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при отправке заявки админу: {str(e)}")
        await state.clear()
        return

    # Очистить состояние после завершения
    await state.clear()

@dp.message(Form.screenshot)
async def no_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")

# ----------------------------
# CALLBACK — Админ (Отклонить)
# ----------------------------
@dp.callback_query(Text.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()

    # Отправляем ссылку на группу ожидания
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"join_wait:{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"no_join:{user_id}")
        ]
    ])
    await bot.send_message(user_id,
        "❌ Твоя заявка отклонена.\n"
        "В клане сейчас нет свободных мест, но ты можешь присоединиться к группе ожидания 🕓\n"
        "Хочешь, чтобы я отправил ссылку на группу?",
        reply_markup=keyboard
    )

@dp.callback_query(Text.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()

    # Отправляем ссылку на группу ожидания
    await bot.send_message(user_id, f"🕓 Отлично! Вот ссылка на группу ожидания:\n{WAIT_GROUP_LINK}")

    await callback.answer("✅ Ссылка на группу ожидания отправлена", show_alert=True)

# ----------------------------
# Запуск бота через polling внутри web service
# ----------------------------
async def on_start(request):
    return web.Response(text="Bot is running")

async def on_shutdown(app):
    await bot.close()

# Запуск через polling
async def start_polling():
    print("Бот запущен с использованием Polling")
    await dp.start_polling(bot)

# Настроим веб-сервер
async def create_app():
    app = web.Application()
    app.router.add_get('/', on_start)
    app.on_shutdown.append(on_shutdown)
    return app

if __name__ == "__main__":
    # Создаем и запускаем веб-приложение
    app = asyncio.run(create_app())
    
    # Запускаем polling в отдельном процессе
    loop = asyncio.get_event_loop()
    loop.create_task(start_polling())

    # Запуск web-сервера
    web.run_app(app, host='0.0.0.0', port=8080)
