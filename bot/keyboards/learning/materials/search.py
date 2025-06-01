from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def exit_and_favorites_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Закончить поиск"), KeyboardButton(text="⭐ Избранное")]
        ],
        resize_keyboard=True
    )

def favorite_button(index: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ В избранное", callback_data=f"fav:{index}")]
        ]
    )

def search_navigation_keyboard(source: str, offset: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Далее", callback_data=f"material_page:{source}:{offset}")]
        ]
    )
