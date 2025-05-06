from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Меню")]
    ],
    resize_keyboard=True
)

menu_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Обучение")],
        [KeyboardButton(text="🧪 Тестирование")],
        [KeyboardButton(text="📊 Прогресс")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)
