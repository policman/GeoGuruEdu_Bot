from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def learning_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Показывает две кнопки: 🧪 Тестирование  и  🔍 Поиск материалов,
    а также «⬅️ Главное меню», если нужно вернуться назад в главное меню всего бота.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Тестирование"),
                KeyboardButton(text="🔍 Поиск материалов")
            ],
            [
                KeyboardButton(text="⬅️ Главное меню")
            ]
        ],
        resize_keyboard=True
    )
