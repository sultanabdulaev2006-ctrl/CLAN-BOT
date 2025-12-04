import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiohttp import web
from datetime import datetime

# ----------------------------
# НАСТРОЙКИ
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Группа куда отправляется "информация об участнике"
GROUP_CHAT_ID = -1003156012968
TOPIC_THREAD_ID = 20  # id темы

# Новая группа (кнопка "Добавить в группу")
NEW_GROUP_LINK = "https://t.me/+moSa3x2Nbyo4NzBi"

# Группа ожидания
GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------
# FSM
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
@dp.message(F.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer(
        "🔞 Сколько тебе лет?",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(F.text == "❌ Нет")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😌 Хорошо. Возможно, твоя харизма ещё раскрывается. Успех любит время. ☘️",
        reply_markup=types.ReplyKeyboardRemove()
    )


@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
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


@dp.message(Form.screenshot, F.photo)
async def finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    await state.clear()

    # Сообщение пользователю
    await message.answer("☘️ Твоя заявка отправлена и сейчас находится на рассмотрении. 🕒")

    # ----------------------------
    # ОТПРАВКА АДМИНУ
    # ----------------------------
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

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
        ]
    ])

    await bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=admin_text,
        reply_markup=keyboard
    )

    # ----------------------------
    # ОТПРАВКА В ГРУППУ (только 3 поля)
    # ----------------------------
    group_text = (
        "📌 Новая информация об участнике:\n\n"
        f"🆔 Игровой ID: {data['game_id']}\n"
        f"🎮 Игровой ник: {data['nickname']}\n"
        f"🔗 Username: @{message.from_user.username}"
    )

    group_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить в группу", callback_data=f"addgroup:{message.from_user.id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"kick:{message.from_user.id}"),
            InlineKeyboardButton(text="⛔ Заблокировать", callback_data=f"ban:{message.from_user.id}")
        ]
    ])

    await bot.send_message(
        GROUP_CHAT_ID,
        group_text,
        message_thread_id=TOPIC_THREAD_ID,
        reply_markup=group_keyboard
    )

# ----------------------------
# Ошибка если нет фото
# ----------------------------
@dp.message(Form.screenshot)
async def no_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")


# ----------------------------
# Callback — админу
# ----------------------------
@dp.callback_query(F.data.startswith("approve:"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(
        user_id,
        "✅ Твоя заявка одобрена.\n"
        "Добро пожаловать в clan.\n"
        "Здесь ценят спокойствие, уверенность и силу."
    )


@dp.callback_query(F.data.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
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
        "❌ Твоя заявка отклонена.\n"
        "В клане сейчас нет свободных мест, но ты можешь присоединиться к группе ожидания 🕓\n\n"
        "Хочешь, чтобы я отправил ссылку на группу?",
        reply_markup=keyboard
    )


# ----------------------------
# Callback — группа кнопки
# ----------------------------
@dp.callback_query(F.data.startswith("addgroup:"))
async def add_group(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await bot.send_message(user_id, f"Вот ссылка на новую группу:\n{NEW_GROUP_LINK}")
    await callback.answer("Отправлено пользователю!")


@dp.callback_query(F.data.startswith("kick:"))
async def kick_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        await bot.ban_chat_member(GROUP_CHAT_ID, user_id)
        await bot.unban_chat_member(GROUP_CHAT_ID, user_id)
        await callback.answer("Пользователь удалён.")
    except:
        await callback.answer("Ошибка. У бота недостаточно прав.")


@dp.callback_query(F.data.startswith("ban:"))
async def ban_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    try:
        await bot.ban_chat_member(GROUP_CHAT_ID, user_id)
        await callback.answer("Пользователь заблокирован.")
    except:
        await callback.answer("Ошибка. У бота недостаточно прав.")


# ----------------------------
# Группа ожидания
# ----------------------------
@dp.callback_query(F.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Отлично! Вот ссылка на группу ожидания:\n{GROUP_LINK}")


@dp.callback_query(F.data == "no_join")
async def no_join(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup()
    await bot.send_message(
        callback.from_user.id,
        "😌 Хорошо! Если что — всегда можешь написать позже ☘️"
    )


# ----------------------------
# Render server + polling
# ----------------------------
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


if __name__ == "__main__":
    print("🤖 Бот запущен (Render + polling)")
    asyncio.run(start_polling_and_server())
