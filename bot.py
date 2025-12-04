import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
)
from aiohttp import web
from datetime import datetime

# ----------------------------
# НАСТРОЙКИ
# ----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

GROUP_CHAT_ID = -1003156012968
TOPIC_THREAD_ID = 20  # id темы

NEW_GROUP_LINK = "https://t.me/+moSa3x2Nbyo4NzBi"
WAIT_GROUP_LINK = "https://t.me/+S8yADtnHIRhiOGNi"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ----------------------------
# Словари для хранения состояния
# ----------------------------
messages_in_group = {}          # message_id сообщений в ветке
stored_applications = {}        # данные анкеты до публикации в ветку

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
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())

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

    # Сохраняем данные анкеты для последующей обработки
    stored_applications[message.from_user.id] = {
        "age": data["age"],
        "nickname": data["nickname"],
        "game_id": data["game_id"],
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "photo_id": photo_id
    }

    await message.answer("☘️ Твоя заявка отправлена и находится на рассмотрении. 🕒")

    # ----------------------------
    # Отправка заявки администратору
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
    keyboard_admin = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{message.from_user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{message.from_user.id}")
        ]
    ])
    await bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=keyboard_admin)

@dp.message(Form.screenshot)
async def no_photo(message: types.Message):
    await message.answer("⚠️ Пожалуйста, отправь фото из профиля CPM.")

# ----------------------------
# CALLBACK — Админ (Одобрить/Отклонить)
# ----------------------------
@dp.callback_query(F.data.startswith("approve:"))
async def approve(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    data = stored_applications.get(user_id)
    if not data:
        await callback.answer("❌ Данные пользователя не найдены.", show_alert=True)
        return

    # Одобрено: отправляем ссылку на основную группу
    await bot.send_message(user_id,
        "✅ Твоя заявка одобрена!\nДобро пожаловать в клан.\n"
        f"Вот ссылка для вступления в группу:\n{NEW_GROUP_LINK}"
    )
    await callback.answer("✅ Пользователь получил ссылку на группу", show_alert=True)

@dp.callback_query(F.data.startswith("reject:"))
async def reject(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()

    # Отклонено: спрашиваем пользователя хочет ли ссылку на группу ожидания
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

# ----------------------------
# CALLBACK — Группа ожидания
# ----------------------------
@dp.callback_query(F.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Отлично! Вот ссылка на группу ожидания:\n{WAIT_GROUP_LINK}")

@dp.callback_query(F.data.startswith("no_join:"))
async def no_join(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, "😌 Хорошо! Если что — всегда можешь написать позже ☘️")

# ----------------------------
# Проверка админа
# ----------------------------
async def is_admin(user_id: int):
    try:
        member = await bot.get_chat_member(GROUP_CHAT_ID, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# ----------------------------
# CALLBACK — Кнопки в ветке (только для админов)
# ----------------------------
@dp.callback_query(F.data.startswith("addgroup:"))
async def add_group(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Только админы могут использовать эту кнопку.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    try:
        await bot.send_message(user_id, f"✅ Ты добавлен в группу! Вот ссылка:\n{NEW_GROUP_LINK}")
        await callback.answer("✅ Ссылка отправлена пользователю", show_alert=True)
    except:
        await callback.answer("⚠️ Не удалось отправить пользователю сообщение.", show_alert=True)

@dp.callback_query(F.data.startswith("kick:"))
async def kick_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Только админы могут использовать эту кнопку.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    try:
        await bot.ban_chat_member(GROUP_CHAT_ID, user_id)
        await bot.unban_chat_member(GROUP_CHAT_ID, user_id)
        await callback.answer("✅ Пользователь удалён из группы", show_alert=True)
    except Exception as e:
        await callback.answer(f"⚠️ Не удалось удалить пользователя: {e}", show_alert=True)

@dp.callback_query(F.data.startswith("ban:"))
async def ban_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Только админы могут использовать эту кнопку.", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    try:
        await bot.ban_chat_member(GROUP_CHAT_ID, user_id)
        await callback.answer("⛔ Пользователь заблокирован в группе", show_alert=True)
    except Exception as e:
        await callback.answer(f"⚠️ Не удалось заблокировать пользователя: {e}", show_alert=True)

# ----------------------------
# Обработка вступления в группу ожидания
# ----------------------------
@dp.chat_member()
async def member_update(event: ChatMemberUpdated):
    user_id = event.from_user.id

    # Пользователь вступил в группу ожидания — публикуем в ветку
    if not event.old_chat_member.is_member() and event.new_chat_member.is_member():
        data = stored_applications.get(user_id)
        if not data:
            return

        group_text = (
            "📌 Новая информация об участнике:\n\n"
            f"🆔 Игровой ID: {data['game_id']}\n"
            f"🎮 Игровой ник: {data['nickname']}\n"
            f"🔗 Username: @{data['username']}"
        )
        group_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить в группу", callback_data=f"addgroup:{user_id}")],
            [
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"kick:{user_id}"),
                InlineKeyboardButton(text="⛔ Заблокировать", callback_data=f"ban:{user_id}")
            ]
        ])
        msg = await bot.send_message(GROUP_CHAT_ID, group_text, message_thread_id=TOPIC_THREAD_ID, reply_markup=group_keyboard)
        messages_in_group[user_id] = msg.message_id
        del stored_applications[user_id]

    # Автоудаление сообщения, если пользователь выходит из группы
    if event.old_chat_member.is_member() and not event.new_chat_member.is_member():
        msg_id = messages_in_group.get(user_id)
        if msg_id:
            try:
                await bot.delete_message(GROUP_CHAT_ID, msg_id)
                del messages_in_group[user_id]
            except:
                pass

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
