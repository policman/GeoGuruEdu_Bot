from aiogram import types
from aiogram.dispatcher import Dispatcher
from bot.keyboards.menu import main_reply_keyboard, menu_reply_keyboard
from bot.services.user_repo import get_user_by_telegram_id
from bot.config import DATABASE_URL
import asyncpg

async def show_menu(message: types.Message):
    await message.answer("Выберите раздел:", reply_markup=menu_reply_keyboard)

async def back_to_main(message: types.Message):
    await message.answer("Главное меню", reply_markup=main_reply_keyboard)

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

def register_menu_handlers(dp: Dispatcher):
    dp.register_message_handler(show_menu, lambda m: m.text == "📋 Меню")
    dp.register_message_handler(back_to_main, lambda m: m.text == "Назад")
    dp.register_message_handler(show_profile, lambda m: m.text == "👤 Профиль")
