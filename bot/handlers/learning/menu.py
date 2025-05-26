from aiogram import types
from bot.keyboards.learning import learning_menu_keyboard

async def learning_entry(message: types.Message):
    text = (
        #"📘 <b>Курсы</b> — интерактивные обучающие модули по ключевым технологиям МСК\n\n"
        "🧪 <b>Тестирование</b> — проверка знаний после прохождения тем\n\n"
        "🔍 <b>Поиск материалов</b> — найдите научные публикации по интересующим темам через Semantic Scholar"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=learning_menu_keyboard)
