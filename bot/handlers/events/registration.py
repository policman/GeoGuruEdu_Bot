from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .entry import events_entry
from .create import (
    start_event_creation, set_title, set_description, set_dates, set_organizers,
    set_price, set_photos, confirm_photos, set_videos, confirm_event, cancel_creation
)
from .view import (
    show_event_list, handle_active_events, handle_created_events, handle_archive_events, handle_show_event
)
from .navigation import router as navigation_router
from bot.states.event_states import EventCreation, EventView

router = Router()

@router.message(lambda m: m.text == "📅 События")
async def handle_events_entry(message: Message):
    await events_entry(message)

@router.message(lambda m: m.text == "Мои события")
async def handle_my_events_menu(message: Message, state: FSMContext):
    await state.set_state(EventView.choosing_category)
    from .navigation import show_my_events_menu
    await show_my_events_menu(message, state)

@router.message(lambda m: m.text == "⬅️ В меню")
async def handle_back_to_main_from_events(message: Message, state: FSMContext):
    await state.clear()
    from .navigation import back_to_main_from_events
    await back_to_main_from_events(message, state)

@router.message(lambda m: m.text == "⬅️ Назад")
async def handle_back_to_my_events_menu(message: Message, state: FSMContext):
    await state.set_state(EventView.choosing_category)
    from .navigation import back_to_my_events_menu
    await back_to_my_events_menu(message, state)

@router.message(lambda m: m.text == "⬅️ Главное меню")
async def handle_return_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    from .navigation import return_to_main_menu
    await return_to_main_menu(message, state)

# CREATE
@router.message(lambda m: m.text == "Создать событие")
async def handle_start_creation(message: Message, state: FSMContext):
    await start_event_creation(message, state)

@router.message(StateFilter(EventCreation.waiting_for_title))
async def handle_title(message: Message, state: FSMContext):
    await set_title(message, state)
@router.message(StateFilter(EventCreation.waiting_for_description))
async def handle_description(message: Message, state: FSMContext):
    await set_description(message, state)
@router.message(StateFilter(EventCreation.waiting_for_dates))
async def handle_dates(message: Message, state: FSMContext):
    await set_dates(message, state)
@router.message(StateFilter(EventCreation.waiting_for_organizers))
async def handle_organizers(message: Message, state: FSMContext):
    await set_organizers(message, state)
@router.message(StateFilter(EventCreation.waiting_for_price))
async def handle_price(message: Message, state: FSMContext):
    await set_price(message, state)
@router.message(StateFilter(EventCreation.waiting_for_photos), lambda m: m.content_type == "photo")
async def handle_photos(message: Message, state: FSMContext):
    await set_photos(message, state)
@router.message(StateFilter(EventCreation.waiting_for_photos), lambda m: m.text == "✅ Готово")
async def handle_confirm_photos(message: Message, state: FSMContext):
    await confirm_photos(message, state)
@router.message(StateFilter(EventCreation.waiting_for_videos), lambda m: m.content_type in ("video", "text"))
async def handle_videos(message: Message, state: FSMContext):
    await set_videos(message, state)
@router.message(StateFilter(EventCreation.confirmation), lambda m: m.text == "✅ Готово")
async def handle_confirm_event(message: Message, state: FSMContext):
    await confirm_event(message, state)
@router.message(StateFilter(EventCreation.confirmation), lambda m: m.text == "🗑 Отменить")
async def handle_cancel_event(message: Message, state: FSMContext):
    await cancel_creation(message, state)

# VIEW
@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "📌 Активные")
async def choosing_active(message: Message, state: FSMContext):
    await show_event_list(message, state, source="active", page=0)

@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "🛠 Созданные")
async def choosing_created(message: Message, state: FSMContext):
    await show_event_list(message, state, source="created", page=0)

@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "📦 Архивные")
async def choosing_archive(message: Message, state: FSMContext):
    await show_event_list(message, state, source="archive", page=0)

@router.callback_query(StateFilter(EventView.viewing_events), lambda c: c.data and c.data.startswith("event:"))
async def show_event_callback(callback: CallbackQuery, state: FSMContext):
    await handle_show_event(callback, state)

router.include_router(navigation_router)
