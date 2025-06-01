#bot/keyboards/events/my_events.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

my_events_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Активные"), KeyboardButton(text="🛠 Созданные"), KeyboardButton(text="📦 Архивные")],
        [KeyboardButton(text="⬅️ В меню")]
    ],
    resize_keyboard=True
)

back_to_my_events_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    resize_keyboard=True
)
