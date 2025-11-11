import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# ====== Настройки ======
BOT_TOKEN = os.getenv("BOT_TOKEN")       # Токен бота
ADMIN_ID = os.getenv("ADMIN_ID")         # Telegram ID администратора

if not BOT_TOKEN:
    raise ValueError("❌ Переменная BOT_TOKEN не задана!")

ADMIN_ID = int(ADMIN_ID) if ADMIN_ID and ADMIN_ID.isdigit() else None

GROUP_LINK = "https://t.me/+e8m9zn85h4c2YmVi"  # 🔗 Ссылка на группу ожидания

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ====== FSM для анкеты ======
class Form(StatesGroup):
    age = State()
    game_id = State()
    screenshot = State()

# ====== Веб сервер для Render ======
async def handle(request):
    return web.Response(text="Bot is running 🚀")

async def start_web():
    app = web.Application()
    app.router.add_get("/", handle)
    port = int(os.getenv("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Web server running on port {port}")

# ====== Хэндлеры бота ======
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🍀 Привет! Хочешь оставить заявку на вступление в клан?",
        reply_markup=keyboard
    )

@dp.message(F.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer(
        "✅ Отлично! Сколько тебе лет? 🔞",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(F.text == "❌ Нет")
async def cancel_form(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😌 Хорошо. Возможно, твоя харизма ещё раскрывается. Успех любит время. ☘️",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Form.age)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(Form.game_id)
    await message.answer(
        "💻✍🏻 Отправь свой ID из CPM."
    )

@dp.message(Form.game_id)
async def ask_screenshot(message: types.Message, state: FSMContext):
    await state.update_data(game_id=message.text)
    await state.set_state(Form.screenshot)
    await message.answer(
        "📸 Отлично! Теперь отправь скриншот из своего профиля CPM 👇🏻"
    )

@dp.message(Form.screenshot, F.photo)
async def finish_form(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    await state.clear()

    await message.answer(
        "☘️ Твоя заявка отправлена и сейчас находится на рассмотрении. 🕒"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
        ]
    ])

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

            await bot.send_photo(ADMIN_ID, photo_id, caption="📸 Скрин из профиля CPM")
            await bot.send_message(ADMIN_ID, text, reply_markup=keyboard)

        except Exception as e:
            print(f"Ошибка при отправке админу: {e}")

@dp.message(Form.screenshot)
async def no_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")

@dp.callback_query(lambda c: c.data and c.data.startswith("approve:"))
async def process_approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    try:
        await bot.send_message(
            user_id,
            "✅ Твоя заявка одобрена.\n"
            "Добро пожаловать в clan.\n"
            "Здесь ценят спокойствие, уверенность и силу."
        )
    except Exception as e:
        print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# ✅ Обновлённое сообщение при отклонении заявки
@dp.callback_query(lambda c: c.data and c.data.startswith("reject:"))
async def process_reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    try:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"join_wait:{user_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data="no_join")
            ]
        ])
        await bot.send_message(
            user_id,
            "❌ Твоя заявка отклонена.\n"
            "В клане сейчас нет свободных мест, "
            "но ты можешь присоединиться к группе ожидания 🕓\n\n"
            "Хочешь, чтобы я отправил ссылку на группу?",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

# ✅ Обработка ответа пользователя
@dp.callback_query(lambda c: c.data and c.data.startswith("join_wait:"))
async def join_wait_group(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(
        user_id,
        f"🕓 Отлично! Вот [ссылка на группу ожидания]({GROUP_LINK}) 👇",
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "no_join")
async def no_join(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup()
    await bot.send_message(
        callback.from_user.id,
        "😌 Хорошо! Если что — всегда можешь написать позже ☘️"
    )

# ====== Запуск ======
async def main():
    asyncio.create_task(start_web())  # запускаем web-сервер параллельно
    print("🤖 Бот запущен и работает 24/7")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
