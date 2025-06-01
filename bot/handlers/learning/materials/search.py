# bot/handlers/learning/materials/search.py
from aiogram import types
from aiogram.fsm.context import FSMContext
from bot.states.learning_states import MaterialSearch
from bot.services.openalex import search_openalex
from bot.keyboards.learning.materials.search import (
    exit_and_favorites_keyboard, favorite_button, search_navigation_keyboard
)
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='auto', target='ru')


async def start_material_search(message: types.Message, state: FSMContext):
    await message.answer(
        "🔍 Введите запрос для поиска публикаций:",
        reply_markup=exit_and_favorites_keyboard()
    )
    await state.set_state(MaterialSearch.waiting_for_query)


async def handle_query(message: types.Message, state: FSMContext):
    query = message.text.strip() if message.text else ""
    if len(query) < 3:
        await message.answer("⚠️ Минимум 3 символа.")
        return

    try:
        results = await search_openalex(query, per_page=3, page=1)
    except Exception as e:
        await message.answer(f"Ошибка при запросе OpenAlex: {e}")
        return

    if not results:
        await message.answer("❌ Ничего не найдено.")
        return

    # Сохраняем состояние
    await state.update_data(query=query, page=1, results=results, favorites=[])

    # Показываем первые 3 результата
    for i, item in enumerate(results[:3]):
        raw_title = item.get("title", "Без названия")
        # Получаем русский вариант
        ru_title = translator.translate(raw_title)
        # Сравниваем оба, игнорируя регистр и пробелы по краям
        if ru_title.strip().lower() != raw_title.strip().lower():
            display_title = f"{ru_title} (Переведено)"
        else:
            display_title = raw_title

        authors = ', '.join(
            auth.get("author", {}).get("display_name", "")
            for auth in item.get("authorships", [])
        )
        year = item.get("publication_year", "")
        url = item.get("primary_location", {}).get("landing_page_url") or item.get("id", "")

        text = (
            f"<b>{i + 1}. {display_title}</b>\n"
            f"👤 {authors}\n"
            f"📅 {year}\n\n"
            f"🔗 <a href='{url}'>Ссылка</a>"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=favorite_button(i))

    # Навигация
    await message.answer("Навигация:", reply_markup=search_navigation_keyboard("openalex", 3))
    await state.set_state(MaterialSearch.browsing_results)
