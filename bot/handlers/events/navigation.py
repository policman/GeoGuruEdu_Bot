from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.menu import section_menu_keyboard
from bot.keyboards.events import event_menu_keyboard, my_events_keyboard
from bot.states.event_states import EventView
from .view import show_event_list

router = Router()

# INLINE навигация
@router.callback_query(lambda c: c.data and c.data.startswith("back:"))
async def back_to_source_list(callback: CallbackQuery, state: FSMContext):
    if callback.data:
        parts = callback.data.split(":")
        if len(parts) == 3:
            _, source, page = parts
            await show_event_list(callback, state, source=source, page=int(page))
        else:
            print("vverx")
            await callback.answer("❌ Неверный формат данных.")



# Reply кнопки
@router.message(lambda m: m.text == "Мои события")
async def show_my_events_menu(message: Message, state: FSMContext):
    await state.set_state(EventView.choosing_category)
    await message.answer("Мои события:", reply_markup=my_events_keyboard)

@router.message(lambda m: m.text == "⬅️ В меню")
async def back_to_main_from_events(message: Message, state: FSMContext):
    await state.set_state(EventView.choosing_category)
    await message.answer("Мои события:", reply_markup=event_menu_keyboard)

@router.message(lambda m: m.text == "⬅️ Назад")
async def back_to_my_events_menu(message: Message, state: FSMContext):
    await state.clear()  # очищаем все данные FSM
    await state.set_state(EventView.choosing_category)
    await message.answer("Мои события:", reply_markup=my_events_keyboard)

@router.message(lambda m: m.text == "⬅️ Главное меню")
async def return_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите раздел:", reply_markup=section_menu_keyboard)
