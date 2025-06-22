# bot/handlers/learning/materials/pagination.py
from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from typing import cast

from bot.services.openalex import search_openalex
from bot.keyboards.learning.materials.search import (
    favorite_button, search_navigation_keyboard
)
from bot.states.learning_states import MaterialSearch
from deep_translator import GoogleTranslator

router = Router()
ITEMS_PER_PAGE = 3

translator = GoogleTranslator(source='auto', target='ru')


@router.callback_query(lambda c: c.data and c.data.startswith("material_page:"))
async def show_more_results(callback: CallbackQuery, state: FSMContext):
    if not callback.message or not isinstance(callback.message, Message):
        await callback.answer("Ошибка: сообщение недоступно.")
        return
    msg = cast(Message, callback.message)

    await msg.delete()

    if not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Неверные данные.")
        return

    _, source, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        await callback.answer("Неверный номер страницы.")
        return

    data = await state.get_data()
    query = data.get("query", "")
    if not isinstance(query, str) or not query:
        await msg.answer("⚠️ Ошибка: предыдущий запрос не найден.")
        return

    results = await search_openalex(query, per_page=ITEMS_PER_PAGE, page=page)
    if not results:
        await msg.answer("📭 Больше результатов нет.")
        await callback.answer()
        return

    await state.update_data(page=page, results=results)

    for i, item in enumerate(results):
        raw_title = item.get("title", "Без названия")
        ru_title = translator.translate(raw_title)
        if ru_title.strip().lower() != raw_title.strip().lower():
            display_title = f"{ru_title} (Переведено)"
        else:
            display_title = raw_title

        authors = ', '.join(
            auth.get("author", {}).get("display_name", "") for auth in item.get("authorships", [])
        )
        year = item.get("publication_year", "")
        url = item.get("primary_location", {}).get("landing_page_url") or item.get("id", "")

        text = (
            f"<b> {display_title}</b>\n"
            f"👤 {authors}\n"
            f"📅 {year}\n\n"
            f"🔗 <a href='{url}'>Ссылка</a>"
        )
        await msg.answer(text, parse_mode="HTML", reply_markup=favorite_button(i))

    await msg.answer("Навигация:", reply_markup=search_navigation_keyboard(source, page + 1))
    await callback.answer()
