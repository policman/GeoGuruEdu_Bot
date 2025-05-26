from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

learning_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        #[KeyboardButton(text="🧠 ИИ чат"), 
        [KeyboardButton(text="🧪 Тестирование"), KeyboardButton(text="🔍 Поиск материалов")],
        [KeyboardButton(text="⬅️ Главное меню")]
    ],
    resize_keyboard=True
)
