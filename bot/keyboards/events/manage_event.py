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
        [KeyboardButton(text="🗑 Удалить"), KeyboardButton(text="📨 Разослать приглашения")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def edit_event_fields_keyboard(event_id, source, page):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"editfield:title:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Описание", callback_data=f"editfield:description:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Дата начала", callback_data=f"editfield:start_date:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Дата окончания", callback_data=f"editfield:end_date:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Организатор", callback_data=f"editfield:organizer:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Стоимость", callback_data=f"editfield:price:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="✅ Сохранить и выйти", callback_data=f"editfield:save:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"editfield:cancel:{event_id}:{source}:{page}")]
    ])
