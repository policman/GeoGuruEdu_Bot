import time
from aiogram import types
from aiogram.fsm.context import FSMContext

from bot.states.learning_states import MaterialSearch
from bot.services.openalex import search_openalex
from bot.services.semantic_scholar import search_papers

from bot.keyboards.learning.materials import exit_search_keyboard
from bot.keyboards.learning.learning import learning_menu_keyboard
from bot.keyboards.learning.materials.search import more_results_keyboard

DELAY_SECONDS = 5  # защита от спама

async def search_materials(message: types.Message, state: FSMContext):
    await message.answer(
        "🔍 Введите ключевые слова для поиска научных публикаций:",
        reply_markup=exit_search_keyboard
    )
    await state.set_state(MaterialSearch.waiting_for_query)
    await state.update_data(last_query_time=0)

async def handle_query(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "❌ Закончить поиск":
        await state.clear()
        await message.answer("Поиск завершён", reply_markup=learning_menu_keyboard)
        return

    if len(text) < 3:
        await message.answer("⚠️ Минимум 3 символа")
        return

    data = await state.get_data()
    now = time.time()
    if now - data.get("last_query_time", 0) < DELAY_SECONDS:
        await message.answer("⏳ Подождите немного перед новым поиском.")
        return

    await state.update_data(last_query_time=now, query=text)
    await message.answer("🔎 Выполняется поиск...")

    # Попытка №1: OpenAlex
    openalex_results = await search_openalex(text)
    if openalex_results:
        for item in openalex_results:
            title = item.get("title", "Без названия")
            url = item.get("primary_location", {}).get("landing_page_url") or item.get("id", "")
            reply = (
                f"<b>{title}</b>\n"
                f"🔗 <a href='{url}'>Ссылка</a>"
            )
            await message.answer(reply, parse_mode="HTML", disable_web_page_preview=True)

        await message.answer("Показать ещё?", reply_markup=more_results_keyboard("openalex", 5))
        return

    # Попытка №2: Semantic Scholar
    scholar_results = await search_papers(text)
    if scholar_results:
        for paper in scholar_results:
            reply = (
                f"<b>{paper.get('title')}</b>\n"
                f"🔗 <a href='{paper.get('url')}'>Ссылка</a>"
            )
            await message.answer(reply, parse_mode="HTML", disable_web_page_preview=True)

        await message.answer("Показать ещё?", reply_markup=more_results_keyboard("scholar", 5))
        return

    # Ничего не найдено
    await message.answer("❌ Ничего не найдено в обеих базах.")
