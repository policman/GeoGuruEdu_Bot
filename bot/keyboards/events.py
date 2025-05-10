from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню событий

event_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📝 Создать событие")],
        [KeyboardButton("✅ Посетить событие")],
        [KeyboardButton("Мои события")],
        [KeyboardButton("⬅️ Назад")]
    ],
    resize_keyboard=True
)

confirmation_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("✅ Готово"), KeyboardButton("✏️ Редактировать")],
        [KeyboardButton("🗑 Отменить"), KeyboardButton("💾 Сохранить черновик")]
    ],
    resize_keyboard=True
)

my_events_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("Активные"), KeyboardButton("Созданные")],
        [KeyboardButton("Архивные")],
        [KeyboardButton("⬅️ Назад")]
    ],
    resize_keyboard=True
)