from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

ai_chat_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⛔️ Завершить диалог")]
    ],
    resize_keyboard=True
)
