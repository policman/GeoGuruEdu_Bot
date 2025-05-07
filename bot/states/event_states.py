from aiogram.dispatcher.filters.state import State, StatesGroup

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_dates = State()
    waiting_for_organizers = State()
    waiting_for_price = State()
    waiting_for_photos = State()
    waiting_for_videos = State()
    confirmation = State()
