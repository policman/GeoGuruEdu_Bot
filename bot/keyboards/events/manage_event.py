from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import datetime

def manage_event_keyboard(event, user_id, source, page):
    buttons = []
    today = datetime.date.today()
    is_active = event["end_date"] >= today
    if is_active:
        buttons.append([
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"edit_event:{event['id']}:{source}:{page}"
            ),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def manage_event_reply_keyboard():
    buttons = [
        [KeyboardButton(text="📨 Разослать приглашения")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
