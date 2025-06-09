# bot/handlers/learning/menu.py

from aiogram import Router
from aiogram.types import Message

# Импортируем функции, возвращающие клавиатуры
from bot.keyboards.learning.learning import learning_menu_keyboard
from bot.keyboards.learning.menu import testing_menu_keyboard

router = Router()

@router.message(lambda m: m.text == "📚 Обучение")
async def enter_learning_section(message: Message):
    await message.answer(
        "📘 Выберите раздел обучения:",
        reply_markup=learning_menu_keyboard()  # <-- вызываем функцию
    )

@router.message(lambda m: m.text == "Тестирование")
async def enter_testing_section(message: Message):
    await message.answer(
        "Меню тестирования:",
        reply_markup=testing_menu_keyboard()  # <-- вызываем функцию
    )

@router.message(lambda m: m.text == "⬅️ Вернуться")
async def back_to_learning(message: Message):
    await message.answer(
        "📘 Выберите раздел обучения:",
        reply_markup=learning_menu_keyboard()  # <-- снова вызываем функцию
    )
