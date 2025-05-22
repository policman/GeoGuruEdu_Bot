from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Только одна кнопка
exit_search_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Закончить поиск")]],
    resize_keyboard=True
)
def more_results_keyboard(source: str, offset: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🔽",
                callback_data=f"more:{source}:{offset}"
            )]
        ]
    )
