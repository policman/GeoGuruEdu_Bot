from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def testing_menu_keyboard() -> ReplyKeyboardMarkup:

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Создать тест"),
                KeyboardButton(text="Пройти тест")
            ],
            [
                KeyboardButton(text="Пригласить в тест"),
                KeyboardButton(text="Приглашения на тест")
            ],
            [
                KeyboardButton(text="⬅️ Вернуться")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
