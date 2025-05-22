# ✅ Файл: bot/handlers/menu.py

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.keyboards.menu import main_menu_keyboard, section_menu_keyboard

router = Router()

@router.message(Command("menu"))
async def show_main_menu(message: Message):
    await message.answer("🔘 Главное меню", reply_markup=main_menu_keyboard)