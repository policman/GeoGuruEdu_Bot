# keyboards/events/inline.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

EVENTS_PER_PAGE = 5

def events_list_keyboard(
    events: list[dict],
    page: int,
    source: str,
    current_user_id: int
) -> InlineKeyboardMarkup:
    """
    Клавиатура списка событий с пагинацией.
    Добавляет к названию события форматированную дату.
    Если event['author_id'] == current_user_id, в тексте кнопки добавляется "(Ваше) ".
    """
    # Импортируем форматтер дат только при вызове, чтобы не зацеплять handlers/events при импорте модуля
    from bot.handlers.events.format_event_dates import format_event_dates

    start = page * EVENTS_PER_PAGE
    end = (page + 1) * EVENTS_PER_PAGE
    page_events = events[start:end]

    event_buttons = []
    for event in page_events:
        # Проверяем, является ли текущий пользователь автором
        prefix = "(Ваше) " if event.get("author_id") == current_user_id else ""
        title = event.get("title", "Без названия")

        # Форматируем дату через format_event_dates
        date_label = format_event_dates(event["start_date"], event["end_date"])
        text = f"{prefix}{title} ({date_label})"

        callback_data = f"event:{event['id']}:{source}:{page}"
        event_buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    # Навигационные кнопки «Назад»/«Вперёд»
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{source}:{page - 1}")
        )
    if end < len(events):
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
    """
    Inline-клавиатура для действий с отдельным событием.
    Если is_author=True, показываются кнопки «Изменить» и «Удалить».
    """
    buttons = []
    if is_author:
        buttons.append([
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data=f"edit_event:{event_id}:{source}:{page}"
            ),
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=f"delete_event:{event_id}:{source}:{page}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back:{source}:{page}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
