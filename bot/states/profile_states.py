from aiogram.fsm.state import StatesGroup, State

class EditProfile(StatesGroup):
    waiting_for_field = State()
    editing_last_name = State()
    editing_first_name = State()
    editing_middle_name = State()
    editing_position = State()
    editing_experience = State()
    editing_department = State()
