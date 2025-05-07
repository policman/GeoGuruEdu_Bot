from aiogram import types
from aiogram.dispatcher import Dispatcher
from bot.keyboards.menu import main_reply_keyboard
from bot.database.user_repo import get_user_by_telegram_id, insert_user
from bot.config import DATABASE_URL
import asyncpg
from datetime import datetime

def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"

async def start_handler(message: types.Message):
    user = message.from_user
    conn = await asyncpg.connect(DATABASE_URL)

    existing = await get_user_by_telegram_id(conn, user.id)
    if not existing:
        user_data = {
            'last_name': user.last_name or 'Фамилия',
            'first_name': user.first_name or 'Имя',
            'middle_name': None,
            'username': user.username or '',
            'telegram_id': user.id,
            'position': 'Сотрудник',
            'experience': 0,
            'department': None
        }
        await insert_user(conn, user_data)
    else:
        user_data = existing

    await conn.close()

    # Формируем имя пользователя
    full_name = user_data['first_name']
    if user_data['middle_name']:
        full_name += f" {user_data['middle_name']}"

    greeting = get_greeting()
    await message.answer(f"{greeting}, {full_name}!", reply_markup=main_reply_keyboard)
    await message.answer("🔸 Ваша активность за сегодня:\n[Заглушка для статистики]")

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
