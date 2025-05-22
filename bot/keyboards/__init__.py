# Импорт из keyboards/menu.py
from .menu import main_menu_keyboard, section_menu_keyboard

# Импорт из keyboards/events/__init__.py
from .events import (
    event_menu_keyboard,
    confirmation_keyboard,
    confirm_photos_keyboard,
    confirm_skip_video_keyboard,
    my_events_keyboard,
    back_to_my_events_keyboard,
    events_list_keyboard,
    back_to_list_keyboard
)

__all__ = [
    # Главное меню
    "main_menu_keyboard",
    "section_menu_keyboard",

    # Клавиатуры событий
    "event_menu_keyboard",
    "confirmation_keyboard",
    "confirm_photos_keyboard",
    "confirm_skip_video_keyboard",
    "my_events_keyboard",
    "back_to_my_events_keyboard",
    "events_list_keyboard",
    "back_to_list_keyboard"
]
