#bot/keyboards/events/creation
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Клавиатура подтверждения создания события
confirmation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Готово"), KeyboardButton(text="✏️ Редактировать")],
        [KeyboardButton(text="🗑 Отменить"), KeyboardButton(text="💾 Сохранить черновик")]
    ],
    resize_keyboard=True
)
