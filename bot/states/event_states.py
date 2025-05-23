from aiogram.fsm.state import State, StatesGroup

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_dates = State()
    waiting_for_organizers = State()
    waiting_for_price = State()
    waiting_for_photos = State()
    waiting_for_videos = State()
    confirmation = State()

    __all_states__ = (
        waiting_for_title,
        waiting_for_description,
        waiting_for_dates,
        waiting_for_organizers,
        waiting_for_price,
        waiting_for_photos,
        waiting_for_videos,
        confirmation,
    )

class EventView(StatesGroup):
    choosing_category = State()
    viewing_events = State()
    back_to_my_events = State()



class EventEdit(StatesGroup):
    choosing_field = State()
    editing_title = State()
    editing_description = State()
    editing_start_date = State()
    editing_end_date = State()
    editing_organizer = State()
    editing_price = State()
