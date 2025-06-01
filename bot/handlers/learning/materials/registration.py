from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from bot.states.learning_states import MaterialSearch
from aiogram.fsm.context import FSMContext
from bot.keyboards.menu import section_menu_keyboard
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.handlers.learning.materials.favorites import show_favorites_paginated, save_favorite

from .search import start_material_search, handle_query
from .pagination import show_more_results

router = Router()

# Точка входа
@router.message(lambda m: m.text == "🔍 Поиск материалов")
async def entry_point(message: Message, state):
    await start_material_search(message, state)

# @router.message(lambda m: m.text == "❌ Закончить поиск")
# async def exit_material_search(message: Message, state: FSMContext):
#     await state.clear()
#     await message.answer("Поиск завершён.", reply_markup=section_menu_keyboard)

# from aiogram.filters import StateFilter

@router.message(StateFilter(MaterialSearch.waiting_for_query), lambda m: m.text == "❌ Закончить поиск")
async def exit_material_search(message: Message, state: FSMContext):
    await state.clear()
    # Здесь ваша кнопка главного меню, например:
    from bot.keyboards.menu import section_menu_keyboard
    await message.answer("Поиск завершён.", reply_markup=section_menu_keyboard)


@router.message(StateFilter(MaterialSearch.waiting_for_query), lambda m: m.text == "⭐ Избранное")
async def show_fav_during_search(message: Message, state: FSMContext):
    if not message.from_user:
        await message.answer("Ошибка: пользователь не определён.")
        return

    await state.set_state(MaterialSearch.viewing_favorites)
    await state.update_data(fav_page=0)

    await message.answer(
        "📚 Ваши избранные материалы:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад к поиску")]],
            resize_keyboard=True
        )
    )

    # Здесь гарантированно есть from_user, можно передать ID
    await show_favorites_paginated(message, message.from_user.id, 0, state)



# Обработка ввода запроса
@router.message(StateFilter(MaterialSearch.waiting_for_query))
async def query_handler(message: Message, state):
    await handle_query(message, state)

@router.callback_query(lambda c: c.data and c.data.startswith("material_page:"))
async def show_more_callback(callback: CallbackQuery, state: FSMContext):
    await show_more_results(callback, state)


@router.message(lambda m: m.text == "⭐ Избранное")
async def show_fav_materials(message: Message, state: FSMContext):
    await state.set_state(MaterialSearch.viewing_favorites)
    await state.update_data(fav_page=0)
    await message.answer(
        "📚 Ваши избранные материалы:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад к поиску")]],
            resize_keyboard=True
        )
    )
    if not message.from_user:
        await message.answer("Ошибка: пользователь не определён.")
        return

    # Передаём state как четвёртый аргумент
    await show_favorites_paginated(message, message.from_user.id, 0, state)


@router.message(StateFilter(MaterialSearch.viewing_favorites), lambda m: m.text == "⬅️ Назад к поиску")
async def back_to_search_from_favorites(message: Message, state: FSMContext):
    # Сбрасываем state, чтобы бот снова ждал query
    await state.clear()
    # Предлагаем заново ввести запрос
    from bot.handlers.learning.materials.search import start_material_search
    await start_material_search(message, state)
