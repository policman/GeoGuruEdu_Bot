from aiogram.fsm.state import StatesGroup, State

class MaterialSearch(StatesGroup):
    waiting_for_query = State()
    browsing_results = State()
    viewing_favorites = State()  # ← добавь эту строку, если её нет
