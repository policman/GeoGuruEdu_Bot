from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from bot.states.learning_states import MaterialSearch

from .search import search_materials, handle_query
from .pagination import show_more_results

router = Router()

@router.message(lambda m: m.text == "🔍 Поиск материалов")
async def entry_point(message: Message, state):
    await search_materials(message, state)

@router.message(StateFilter(MaterialSearch.waiting_for_query))
async def query_handler(message: Message, state):
    await handle_query(message, state)

@router.callback_query(lambda c: c.data and c.data.startswith("more:"))
async def show_more_callback(callback: CallbackQuery, state):
    await show_more_results(callback, state)
