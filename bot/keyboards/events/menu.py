#bot/keyboards/events/menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню раздела "События"
event_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Посетить"), KeyboardButton(text="Создать"), KeyboardButton(text="Мои события")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ],
    resize_keyboard=True
)
