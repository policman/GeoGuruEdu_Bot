from aiogram.fsm.state import State, StatesGroup

class EventCreation(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_dates = State()
    waiting_for_organizers = State()
    waiting_for_price = State()
    waiting_for_photos = State()
    confirmation = State()

    __all_states__ = (
        waiting_for_title,
        waiting_for_description,
        waiting_for_dates,
        waiting_for_organizers,
        waiting_for_price,
        waiting_for_photos,
        confirmation,
    )

# class EventView(StatesGroup):
    
#     viewing_events = State()
    
#     writing_to_organizer = State()   # участник пишет сообщение организатору
#     viewing_answers      = State()   # участник просматривает ответы организатора
#     paging_answers       = State()   # состояние для навигации по списку ответов

class EventView(StatesGroup):
    viewing_participants_menu = State()   # <- добавлено
    viewing_events = State()
    writing_to_organizer = State()
    paging_answers = State()
    viewing_answers = State()
    paging_questions = State()
    viewing_questions = State()
    viewing_question = State()
    answering_question = State()
    back_to_my_events = State()
    choosing_category = State()

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

class InvitationStates(StatesGroup):
    CHOOSING_METHOD = State()             # выбрать один из 4 способов
    ENTER_DEPARTMENTS = State()           # вводим отделы (через запятую)
    ENTER_PROFILES = State()              # вводим профили (через запятую)
    CONFIRM_DEPTS_PROFS = State()         # подтверждаем рассылку по отделам/профилям
    CONFIRM_COLLEAGUES = State()          # подтверждаем рассылку «всем сотрудникам»
    CONFIRM_ALL = State()                 # подтверждаем рассылку «всем»