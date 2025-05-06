from aiogram import types
from aiogram.dispatcher import Dispatcher
from bot.keyboards.menu import main_reply_keyboard
from bot.services.user_repo import get_user_by_telegram_id, insert_user
from bot.config import DATABASE_URL
import asyncpg

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
    await conn.close()

    await message.answer("Добро пожаловать!", reply_markup=main_reply_keyboard)

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=["start"])
