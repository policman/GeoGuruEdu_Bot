from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

confirm_photos_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Готово")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

confirm_skip_video_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пропустить")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

my_events_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📌 Активные"), KeyboardButton("🛠 Созданные")],
        [KeyboardButton("📦 Архивные")],
        [KeyboardButton("⬅️ Назад")]
    ],
    resize_keyboard=True
)
