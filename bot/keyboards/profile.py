from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def profile_edit_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить фамилию", callback_data="edit_profile:last_name")],
            [InlineKeyboardButton(text="Изменить имя", callback_data="edit_profile:first_name")],
            [InlineKeyboardButton(text="Изменить отчество", callback_data="edit_profile:middle_name")],
            [InlineKeyboardButton(text="Изменить должность", callback_data="edit_profile:position")],
            [InlineKeyboardButton(text="Изменить стаж", callback_data="edit_profile:experience")],
            [InlineKeyboardButton(text="Изменить отдел", callback_data="edit_profile:department")],
        ]
    )
