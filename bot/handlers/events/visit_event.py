from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from datetime import datetime

from bot.keyboards.events.view_event import visit_event_keyboard
from bot.states.event_states import VisitEvent
from .show_event_list import show_event_list

router = Router()

@router.message(lambda m: m.text == "Посетить событие")
async def handle_visit_event_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(VisitEvent.menu)
    await message.answer("Раздел посещения событий:", reply_markup=visit_event_keyboard)

@router.message(lambda m: m.text == "Список событий")
async def handle_list_all_events(message: Message, state: FSMContext):
    await state.set_state(VisitEvent.listing)
    await state.update_data(
        page=0,
        filter_organizer=None,
        filter_min_price=None,
        filter_max_price=None,
        filter_start_date=None,
        filter_end_date=None,
        search_query=None
    )
    await show_event_list(message, state)

@router.message(StateFilter(VisitEvent.menu))
async def handle_text_search(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Введите текст для поиска")
        return
    await state.update_data(search_query=message.text.strip(), page=0)
    await state.set_state(VisitEvent.listing)
    await show_event_list(message, state)


@router.callback_query(F.data == "filter:organizer")
async def handle_filter_organizer(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VisitEvent.filter_organizer)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите имя организатора для фильтрации:")

@router.callback_query(F.data == "filter:price")
async def handle_filter_price(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VisitEvent.filter_price_range)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите диапазон цены в формате min-max (например: 1000-3000):")

@router.callback_query(F.data == "filter:date")
async def handle_filter_date(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VisitEvent.filter_start_date)
    await callback.answer()
    if isinstance(callback.message, Message):
        await callback.message.answer("Введите начальную дату в формате YYYY-MM-DD:")

@router.callback_query(F.data == "filter:reset")
async def handle_reset_filters(callback: CallbackQuery, state: FSMContext):
    await state.update_data(
        filter_organizer=None,
        filter_min_price=None,
        filter_max_price=None,
        filter_start_date=None,
        filter_end_date=None,
        search_query=None,
        page=0
    )
    await callback.answer("Фильтры сброшены")
    if isinstance(callback.message, Message):
        await show_event_list(callback.message, state)

@router.message(StateFilter(VisitEvent.filter_organizer))
async def apply_organizer_filter(message: Message, state: FSMContext):
    organizer = (message.text or "").strip()
    if not organizer:
        await message.answer("Введите имя организатора")
        return
    await state.update_data(filter_organizer=organizer, page=0)
    await state.set_state(VisitEvent.listing)
    await show_event_list(message, state)

@router.message(StateFilter(VisitEvent.filter_price_range))
async def apply_price_filter(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    try:
        min_price, max_price = map(int, text.split("-"))
        await state.update_data(filter_min_price=min_price, filter_max_price=max_price, page=0)
    except Exception:
        await message.answer("Неверный формат. Введите диапазон как min-max")
        return
    await state.set_state(VisitEvent.listing)
    await show_event_list(message, state)

@router.message(StateFilter(VisitEvent.filter_start_date))
async def receive_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime((message.text or "").strip(), "%Y-%m-%d").date()
        await state.update_data(filter_start_date=start_date.isoformat())
        await state.set_state(VisitEvent.filter_end_date)
        await message.answer("Введите конечную дату в формате YYYY-MM-DD:")
    except ValueError:
        await message.answer("❌ Неверный формат. Попробуйте ещё раз: YYYY-MM-DD")

@router.message(StateFilter(VisitEvent.filter_end_date))
async def receive_end_date(message: Message, state: FSMContext):
    try:
        end_date = datetime.strptime((message.text or "").strip(), "%Y-%m-%d").date()
        data = await state.get_data()
        start_date_str = data.get("filter_start_date")
        if not start_date_str:
            await message.answer("Произошла ошибка. Начальная дата не найдена. Повторите выбор даты.")
            return

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        if end_date < start_date:
            await message.answer("❌ Конечная дата не может быть раньше начальной. Введите конечную дату ещё раз:")
            return

        await state.update_data(filter_end_date=end_date.isoformat(), page=0)
        await state.set_state(VisitEvent.listing)
        await show_event_list(message, state)

    except ValueError:
        await message.answer("❌ Неверный формат. Попробуйте ещё раз: YYYY-MM-DD")


@router.callback_query(lambda c: c.data and c.data.startswith("page:"))
async def paginate_events(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("page", 0)

    if callback.data == "page:next":
        page = current_page + 1
    elif callback.data == "page:prev":
        page = max(current_page - 1, 0)
    else:
        await callback.answer("❌ Неверный формат данных.")
        return

    await state.update_data(page=page)
    await callback.answer()

    # Явная проверка типа — это устраняет ошибку Pylance
    if isinstance(callback.message, Message):
        await show_event_list(callback.message, state)
    else:
        await callback.answer("Ошибка: сообщение недоступно.")
