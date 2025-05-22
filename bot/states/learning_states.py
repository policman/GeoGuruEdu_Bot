from aiogram.fsm.state import StatesGroup, State

class MaterialSearch(StatesGroup):
    waiting_for_query = State()