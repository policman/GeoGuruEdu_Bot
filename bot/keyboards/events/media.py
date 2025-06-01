#bot/keyboards/events/media
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

confirm_photos_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Готово")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

