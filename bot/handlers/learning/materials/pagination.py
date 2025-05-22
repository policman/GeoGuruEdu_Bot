from aiogram import types
from aiogram.fsm.context import FSMContext
from bot.services.semantic_scholar import search_papers
from bot.services.openalex import search_openalex
from bot.keyboards.learning.materials.search import more_results_keyboard
from bot.states.learning_states import MaterialSearch

MAX_RESULTS = 30  # максимум сколько можно пролистывать

async def show_more_results(callback: types.CallbackQuery, state: FSMContext):
    if not callback.data or not isinstance(callback.message, types.Message):
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        return
    _, source, offset = parts
    try:
        offset = int(offset)
    except ValueError:
        await callback.answer("Ошибка в данных.")
        return

    await callback.answer()
    await callback.message.edit_reply_markup()  # удалим старую кнопку

    data = await state.get_data()
    query = data.get("query")

    if not query:
        await callback.message.answer("⚠️ Ошибка: предыдущий запрос не найден.")
        return

    if offset >= MAX_RESULTS:
        await callback.message.answer("📌 Достигнут предел результатов.")
        return

    if source == "scholar":
        results = await search_papers(query, offset + 5)
        title = "Ещё:"
    else:
        results = await search_openalex(query, offset + 5)
        title = "Ещё:"

    if not results or offset >= len(results):
        await callback.message.answer("📭 Больше результатов не найдено.")
        return

    await callback.message.answer(title)

    # Показать только текущую "страницу"
    for paper in results[offset:offset + 5]:
        if source == "scholar":
            text = (
                f"<b>{paper.get('title')}</b>\n"
                f"🔗 <a href='{paper.get('url')}'>Ссылка</a>"
            )
        else:
            url = paper.get("primary_location", {}).get("landing_page_url") or paper.get("id", "")
            text = (
                f"<b>{paper.get('title')}</b>\n"
                f"🔗 <a href='{url}'>Ссылка</a>"
            )
        await callback.message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
