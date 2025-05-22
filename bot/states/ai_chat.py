from aiogram.fsm.state import StatesGroup, State

class AIChatStates(StatesGroup):
    chatting = State()
    waiting_response = State()
