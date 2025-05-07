from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Меню")]
    ],
    resize_keyboard=True
)

# Расширенное меню
menu_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Обучение")],
        [KeyboardButton(text="🧪 Тестирование")],
        [KeyboardButton(text="📊 Прогресс")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📅 События")],
        [KeyboardButton(text="Назад")]
    ],
    resize_keyboard=True
)
