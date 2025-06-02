from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncpg

from bot.database.user_repo import (
    get_user_by_telegram_id,
    update_user_field,
    update_user_fields
)
from bot.config import DATABASE_URL
from bot.keyboards.menu import section_menu_keyboard

router = Router()


# ======================
# 1) Старая часть: редактирование через «👤 Профиль»
# ======================
class EditProfile(StatesGroup):
    editing_field = State()

def profile_edit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Фамилия", callback_data="edit_profile:last_name")],
        [InlineKeyboardButton(text="Имя", callback_data="edit_profile:first_name")],
        [InlineKeyboardButton(text="Отчество", callback_data="edit_profile:middle_name")],
        [InlineKeyboardButton(text="Должность", callback_data="edit_profile:position")],
        [InlineKeyboardButton(text="Стаж", callback_data="edit_profile:experience")],
        [InlineKeyboardButton(text="Отдел", callback_data="edit_profile:department")]
    ])

@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, state: FSMContext):
    if not message.from_user:
        await message.answer("⚠️ Не удалось определить пользователя.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, message.from_user.id)
    await conn.close()

    if not user:
        await message.answer("⚠️ Пользователь не найден в базе.")
        return

    profile_text = (
        f"👤 <b>Профиль пользователя</b>\n\n"
        f"Фамилия: {user.get('last_name') or '-'}\n"
        f"Имя: {user.get('first_name') or '-'}\n"
        f"Отчество: {user.get('middle_name') or '-'}\n"
        f"Username: @{user.get('username') or '-'}\n"
        f"Должность: {user.get('position') or '-'}\n"
        f"Стаж: {user.get('experience', 0)} лет\n"
        f"Отдел: {user.get('department') or '-'}"
    )

    await message.answer(profile_text, parse_mode="HTML", reply_markup=profile_edit_keyboard())

@router.callback_query(F.data.startswith("edit_profile:"))
async def handle_edit_profile(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not callback.from_user or not callback.data:
        await callback.answer("Ошибка вызова", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    field = parts[1]
    prompts = {
        "last_name": "Введите новую фамилию:",
        "first_name": "Введите новое имя:",
        "middle_name": "Введите новое отчество (или оставьте пустым):",
        "position": "Введите новую должность:",
        "experience": "Введите новый стаж в годах (только число):",
        "department": "Введите новый отдел (или оставьте пустым):"
    }

    await state.set_state(EditProfile.editing_field)
    await state.update_data(field=field)
    await bot.send_message(callback.from_user.id, prompts[field])
    await callback.answer()

@router.message(EditProfile.editing_field)
async def save_profile_field(message: Message, state: FSMContext):
    if not message.from_user:
        await message.answer("Ошибка определения пользователя.")
        return

    data = await state.get_data()
    field = data.get("field")
    if not field:
        await message.answer("Ошибка состояния.")
        await state.clear()
        return

    value = (message.text or "").strip()
    if field == "experience":
        try:
            value = int(value)
        except ValueError:
            await message.answer("Введите число для стажа.")
            return

    conn = await asyncpg.connect(DATABASE_URL)
    await update_user_field(conn, message.from_user.id, field, value)
    user = await get_user_by_telegram_id(conn, message.from_user.id)
    await conn.close()
    await state.clear()

    if user:
        profile_text = (
            f"✅ <b>Данные обновлены!</b>\n\n"
            f"Фамилия: {user.get('last_name') or '-'}\n"
            f"Имя: {user.get('first_name') or '-'}\n"
            f"Отчество: {user.get('middle_name') or '-'}\n"
            f"Username: @{user.get('username') or '-'}\n"
            f"Должность: {user.get('position') or '-'}\n"
            f"Стаж: {user.get('experience', 0)} лет\n"
            f"Отдел: {user.get('department') or '-'}"
        )
        await message.answer(profile_text, parse_mode="HTML", reply_markup=profile_edit_keyboard())
    else:
        await message.answer("⚠️ Пользователь не найден.")


# ======================
# 2) Новая часть: первичное заполнение «должность» + «отдел» после /start
# ======================
class FillProfile(StatesGroup):
    POSITION = State()
    DEPARTMENT = State()

@router.message(FillProfile.POSITION)
async def fill_position(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    await state.update_data(position=text)

    # При переходе на ввод отдела снова убираем любую клавиатуру
    await state.set_state(FillProfile.DEPARTMENT)
    await message.answer("Спасибо! Теперь введите ваш отдел:", reply_markup=ReplyKeyboardRemove())

@router.message(FillProfile.DEPARTMENT)
async def fill_department(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    position = data.get("position")
    department = text

    user = message.from_user
    if user is None:
        await message.answer("❌ Не удалось определить пользователя.")
        await state.clear()
        return

    conn = await asyncpg.connect(DATABASE_URL)
    # Обновляем сразу оба поля: position и department
    await update_user_fields(conn, user.id, position=position, department=department)
    await conn.close()

    await state.clear()
    # После обновления выводим главное меню
    await message.answer("✅ Ваш профиль обновлён.", reply_markup=section_menu_keyboard)