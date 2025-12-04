import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
from datetime import datetime

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"

# ====== ТВОЯ ГРУППА И ТЕМА ======
GROUP_CHAT_ID = -1003156012968  # ID группы (с префиксом -100)
TOPIC_THREAD_ID = 20             # ID темы "информация об участнике"

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ====== FSM для анкеты ======
class Form(StatesGroup):
    age = State()
    game_id = State()
    screenshot = State()

# ====== Хэндлеры ======
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

@dp.message(F.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer("✅ Отлично! Сколько тебе лет? 🔞", reply_markup=types.ReplyKeyboardRemove())

@dp.message(F.text == "❌ Нет")
async def cancel_form(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("😌 Хорошо. Если передумаешь — пиши ☘️", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Form.age)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой ID из CPM.")

@dp.message(Form.game_id)
async def ask_screenshot(message: types.Message, state: FSMContext):
    await state.update_data(game_id=message.text)
    await state.set_state(Form.screenshot)
    await message.answer("📸 Отлично! Теперь отправь скриншот из профиля CPM 👇🏻")

@dp.message(Form.screenshot, F.photo)
async def finish_form(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    await state.clear()

    await message.answer("☘️ Твоя заявка отправлена и находится на рассмотрении 🕒")

    if ADMIN_ID:
        try:
            now = datetime.now().strftime("%d.%m.%Y, %H:%M")

            text = (
                "📥 Новая заявка в клан XARIZMA!\n\n"
                f"👤 Имя: {message.from_user.full_name}\n"
                f"🔗 Username: @{message.from_user.username}\n"
                f"🆔 Telegram ID: {message.from_user.id}\n\n"
                f"🔞 Возраст: {data.get('age')}\n"
                f"💻 Игровой ID: {data.get('game_id')}\n"
                f"🕒 Время: {now}"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
                ]
            ])

            # ——— Отправка админу
            await bot.send_photo(
                ADMIN_ID,
                photo_id,
                caption=text,
                reply_markup=keyboard
            )

            # ——— Отправка в тему группы 💬
            await bot.send_photo(
                GROUP_CHAT_ID,
                photo_id,
                caption=text,
                message_thread_id=TOPIC_THREAD_ID
            )

        except Exception as e:
            print(f"Ошибка при отправке: {e}")

@dp.message(Form.screenshot)
async def no_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")

# ====== Callback: Одобрить ======
@dp.callback_query(lambda c: c.data and c.data.startswith("approve:"))
async def process_approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, "✅ Твоя заявка одобрена! Добро пожаловать в клан!")

# ====== Callback: Отклонить ======
@dp.callback_query(lambda c: c.data and c.data.startswith("reject:"))
async def process_reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"join_wait:{user_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="no_join")
        ]
    ])

    await bot.send_message(
        user_id,
        "❌ Сейчас нет мест в клане, но ты можешь вступить в группу ожидания.\n\n"
        "Отправить ссылку?",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("join_wait:"))
async def join_wait_group(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Вот ссылка на группу ожидания:\n{GROUP_LINK}")

@dp.callback_query(lambda c: c.data == "no_join")
async def no_join(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup()
    await bot.send_message(callback.from_user.id, "😌 Хорошо! Если что — пиши позже ☘️")

# ====== Сервер + polling для Render ======
async def dummy(request):
    return web.Response(text="ok")

async def start_polling_and_server():
    polling_task = asyncio.create_task(dp.start_polling(bot))

    app = web.Application()
    app.router.add_get("/", dummy)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080)))
    await site.start()

    await polling_task
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    print("🤖 Бот запущен (Render + polling)")
    asyncio.run(start_polling_and_server())
