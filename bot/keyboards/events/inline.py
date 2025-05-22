from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

EVENTS_PER_PAGE = 5

def events_list_keyboard(events: list, page: int, source: str) -> InlineKeyboardMarkup:
    """Клавиатура списка событий с пагинацией."""
    event_buttons = [
        [InlineKeyboardButton(
            text=event["title"],
            callback_data=f"event:{event['id']}:{source}:{page}"
        )]
        for event in events[page * EVENTS_PER_PAGE : (page + 1) * EVENTS_PER_PAGE]
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{source}:{page - 1}")
        )
    if (page + 1) * EVENTS_PER_PAGE < len(events):
        nav_buttons.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page:{source}:{page + 1}")
        )

    if nav_buttons:
        event_buttons.append(nav_buttons)

    return InlineKeyboardMarkup(inline_keyboard=event_buttons)

def back_to_list_keyboard(source: str, page: int) -> InlineKeyboardMarkup:
    """Кнопка назад к списку событий."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back:{source}:{page}")]
        ]
    )

def event_action_keyboard(event_id: int, source: str, page: int, is_author: bool) -> InlineKeyboardMarkup:
    buttons = []
    if is_author:
        buttons.append([
            InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_event:{event_id}:{source}:{page}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_event:{event_id}:{source}:{page}")
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back:{source}:{page}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
