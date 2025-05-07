from aiogram import types
from aiogram.dispatcher import Dispatcher
from bot.keyboards.menu import main_reply_keyboard, menu_reply_keyboard

async def show_menu(message: types.Message):
    await message.answer("🔸 Выберите раздел:", reply_markup=menu_reply_keyboard)

async def back_to_main(message: types.Message):
    await message.answer("🔸 Главное меню", reply_markup=main_reply_keyboard)
    await message.answer("🔸 Ваша активность за сегодня:\n[Заглушка для статистики]")

def register_menu_handlers(dp: Dispatcher):
    dp.register_message_handler(show_menu, lambda m: m.text == "Меню")
    dp.register_message_handler(back_to_main, lambda m: m.text == "Назад")
