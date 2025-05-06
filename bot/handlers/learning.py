from aiogram import types
from aiogram.dispatcher import Dispatcher

async def learning_handler(callback: types.CallbackQuery):
    await callback.message.answer("Здесь будет список обучающих модулей...")
    await callback.answer()

def register_learning_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(learning_handler, lambda c: c.data == "go_learning")
