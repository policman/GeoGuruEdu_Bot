from aiogram import Router
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from bot.keyboards.menu import section_menu_keyboard
from bot.database.user_repo import get_user_by_telegram_id, insert_user
from bot.database.invitations_repo import get_unread_invitations_count
from bot.config import DATABASE_URL
from bot.handlers.profile import FillProfile
import asyncpg
from datetime import datetime

router = Router()

def get_greeting() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    elif 18 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        await message.answer("❌ Не удалось определить пользователя.")
        return

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
        existing = user_data
    else:
        user_data = existing

    invite_count = await get_unread_invitations_count(user.id, conn)
    await conn.close()

    full_name = user_data['first_name']
    if user_data.get('middle_name'):
        full_name += f" {user_data['middle_name']}"

    greeting = get_greeting()

    # Если у пользователя position="Сотрудник" и department IS NULL → запускаем FSM
    if user_data.get('position') == 'Сотрудник' and (user_data.get('department') is None):
        # Сразу удалить любую старую клавиатуру
        await state.set_state(FillProfile.POSITION)
        await message.answer(
            f"{greeting}, {full_name}! Пожалуйста, введите вашу должность:",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Иначе сразу выводим главное меню
    await message.answer(f"{greeting}, {full_name}!", reply_markup=section_menu_keyboard)
