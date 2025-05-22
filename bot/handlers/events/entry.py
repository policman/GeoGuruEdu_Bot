from aiogram.types import Message
from bot.keyboards.events import event_menu_keyboard

async def events_entry(message: Message):
    await message.answer("Выберите действие:", reply_markup=event_menu_keyboard)
