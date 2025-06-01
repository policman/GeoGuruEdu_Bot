from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

cancel_creation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отменить создание")]
    ],
    resize_keyboard=True
)
