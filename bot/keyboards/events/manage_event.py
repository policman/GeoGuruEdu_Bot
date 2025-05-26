from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def manage_event_keyboard(event, user_id, source, page):
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"edit_event:{event['id']}:{source}:{page}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def manage_event_reply_keyboard():
    buttons = [
        [KeyboardButton(text="📨 Разослать приглашения"), KeyboardButton(text="👥 Участники")],
        [KeyboardButton(text="🗑 Удалить")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


