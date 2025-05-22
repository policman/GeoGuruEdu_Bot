#bot/keyboards/events/menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню раздела "События"
event_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Создать событие"), KeyboardButton(text="Посетить событие")],
        [KeyboardButton(text="Мои события")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ],
    resize_keyboard=True
)
