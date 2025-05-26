from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def event_reply_keyboard(is_author: bool = True):
    buttons = []
    if is_author:
        buttons.append([KeyboardButton(text="🗑 Удалить")])
    buttons.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def event_edit_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить название", callback_data="edit_field:title"),
                InlineKeyboardButton(text="Изменить описание", callback_data="edit_field:description")
            ],
            [
                InlineKeyboardButton(text="Изменить даты", callback_data="edit_field:dates"),
                InlineKeyboardButton(text="Изменить организаторов", callback_data="edit_field:organizers")
            ],
            [
                InlineKeyboardButton(text="⬅️ Отмена", callback_data="cancel_edit")
            ]
        ]
    )


visit_event_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Список событий")],
        [KeyboardButton(text="Поиск")],
        [KeyboardButton(text="Приглашения")],
        [KeyboardButton(text="⬅️ В меню")],
    ],
    resize_keyboard=True
)
