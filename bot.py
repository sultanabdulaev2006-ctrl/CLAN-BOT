import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ===== Переменные окружения (Replit Secrets) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
PRIVATE_GROUP_LINK = "https://t.me/+8XWLNODTnV1mNzMy"
PRIVATE_CHAT_ID = -1003156012968

# ===== Инициализация бота =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ===== FSM для формы =====
class Form(StatesGroup):
    age = State()
    nickname = State()
    game_id = State()

# ===== Команда /start =====
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

# ===== Ответ на "Да" =====
@dp.message(lambda m: m.text == "✅ Да")
async def ask_age(message: types.Message, state: FSMContext):
    await state.set_state(Form.age)
    await message.answer("🔞 Сколько тебе лет?", reply_markup=types.ReplyKeyboardRemove())

# ===== Ответ на "Нет" =====
@dp.message(lambda m: m.text == "❌ Нет")
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😌 Хорошо. Возможно, твоя харизма ещё раскрывается. Успех любит время. ☘️",
        reply_markup=types.ReplyKeyboardRemove()
    )

# ===== Обработка возраста =====
@dp.message(Form.age)
async def ask_nickname(message: types.Message, state: FSMContext):
    age = message.text
    if not age.isdigit() or int(age) < 12:
        await message.answer("❌ Неверный возраст. Укажи возраст числом.")
        return
    await state.update_data(age=age)
    await state.set_state(Form.nickname)
    await message.answer("🎮 Напиши свой игровой ник.")

# ===== Обработка ника =====
@dp.message(Form.nickname)
async def ask_game_id(message: types.Message, state: FSMContext):
    await state.update_data(nickname=message.text)
    await state.set_state(Form.game_id)
    await message.answer("💻✍🏻 Отправь свой игровой ID из CPM.")

# ===== Обработка ID и отправка администратору =====
@dp.message(Form.game_id)
async def finish_form(message: types.Message, state: FSMContext):
    await state.update_data(game_id=message.text)
    data = await state.get_data()
    await message.answer("📝 Твоя заявка обрабатывается, пожалуйста, подождите...")
    
    now = datetime.now().strftime("%d.%m.%Y, %H:%M")
    admin_text = (
        "📥 Новая заявка в клан XARIZMA!\n\n"
        f"👤 Имя: {message.from_user.full_name}\n"
        f"🔗 Username: @{message.from_user.username or 'нет'}\n"
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
    await state.clear()

# ===== Callback: отклонение заявки =====
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
        "❌ Твоя заявка отклонена.\nСвободных мест нет, но можешь войти в группу ожидания.\nОтправить ссылку?",
        reply_markup=keyboard
    )

# ===== Callback: согласие на группу ожидания =====
@dp.callback_query(lambda c: c.data.startswith("join_wait:"))
async def join_wait(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup()
    await bot.send_message(user_id, f"🕓 Вот твоя приватная ссылка для вступления:\n{PRIVATE_GROUP_LINK}")
    await callback.answer("Ссылка отправлена!", show_alert=True)

# ===== Callback: отказ от группы ожидания =====
@dp.callback_query(lambda c: c.data.startswith("no_join:"))
async def no_join(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup()
    await callback.answer("Ты отказался от группы ожидания.", show_alert=True)

# ===== Обработка запросов на вступление в чат =====
@dp.chat_join_request()
async def handle_join_request(event: types.ChatJoinRequest):
    if event.chat.id == PRIVATE_CHAT_ID:
        await bot.approve_chat_join_request(chat_id=PRIVATE_CHAT_ID, user_id=event.from_user.id)

# ===== Запуск бота через polling =====
if __name__ == "__main__":
    print("Бот стартовал ✅")
    asyncio.run(dp.start_polling(bot))
