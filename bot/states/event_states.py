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


class VisitEvent(StatesGroup):
    menu = State()
    show_list = State()
    search = State()
    my_events = State()
    invitations = State()
    viewing_one_event = State()
    search_query = State()
    listing = State()
    search_query = State()
    filtering = State()
    filter_organizer = State()
    filter_price_range = State()
    filter_date_range = State()
    filter_start_date = State()  # ← Добавь это
    filter_end_date = State()    # ← И это
# from aiogram.fsm.state import StatesGroup, State

# class EventManageFSM(StatesGroup):
#     viewing_event = State()  # состояние просмотра одного события
