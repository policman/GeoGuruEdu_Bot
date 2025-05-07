from aiogram import types
from aiogram.dispatcher import Dispatcher
from bot.database.user_repo import get_user_by_telegram_id
from bot.config import DATABASE_URL
import asyncpg

async def show_profile(message: types.Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, user_id)
    await conn.close()

    if user:
        profile_text = (
            f"👤 <b>Профиль пользователя</b>\n\n"
            f"Фамилия: {user['last_name']}\n"
            f"Имя: {user['first_name']}\n"
            f"Отчество: {user['middle_name'] or '-'}\n"
            f"Username: @{user['username']}\n"
            f"Должность: {user['position']}\n"
            f"Стаж: {user['experience']} лет\n"
            f"Отдел: {user['department'] or '-'}"
        )
    else:
        profile_text = "⚠️ Пользователь не найден в базе данных."

    await message.answer(profile_text, parse_mode="HTML")

def register_profile_handlers(dp: Dispatcher):
    dp.register_message_handler(show_profile, lambda m: m.text == "👤 Профиль")
