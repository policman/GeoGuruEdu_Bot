# bot/states/test_states.py

from aiogram.fsm.state import State, StatesGroup

class TestCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_q_count = State()
    waiting_for_q_text = State()
    waiting_for_opt_count = State()
    waiting_for_opt_text = State()
    waiting_for_opt_is_correct = State()


class TestTaking(StatesGroup):
    waiting_for_start        = State()  # только для перехода
    waiting_for_answer       = State()  # ждем выбор варианта
