# ✅ Файл: bot/keyboards/menu.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# # Главное меню (первая кнопка "Меню")
# main_menu_keyboard = ReplyKeyboardMarkup(
#     keyboard=[
#         [KeyboardButton(text="Меню")]
#     ],
#     resize_keyboard=True
# )

# Расширенное меню с разделами
section_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Обучение"),KeyboardButton(text="📅 События")],
        [KeyboardButton(text="👤 Профиль"),KeyboardButton(text="📊 Прогресс")]
    ],
    resize_keyboard=True
)

def main_menu_keyboard(invite_count=0):
    invite_text = f"Приглашения ({invite_count})" if invite_count else "Приглашения"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Посетить событие")],
            [KeyboardButton(text=invite_text)],
            [KeyboardButton(text="Мои события")],
        ],
        resize_keyboard=True
    )