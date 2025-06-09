from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def manage_event_keyboard(event, user_id, source, page):
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=f"edit_event:{event['id']}:{source}:{page}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def manage_event_reply_keyboard():
    buttons = [
        [KeyboardButton(text="📨 Разослать приглашения"), KeyboardButton(text="👥 Участники")],
        [KeyboardButton(text="🗑 Удалить")],
        [KeyboardButton(text="⬅️ Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def invite_method_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [ KeyboardButton(text="📑 По отделам/профилю"), KeyboardButton(text="👥 Всем сотрудникам") ],
            [ KeyboardButton(text="🌐 Всем"), KeyboardButton(text="⬅️ Назад к событию") ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Клавиатура «Подтвердить / Отменить» для всех трёх сценариев
def invite_confirm_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [ KeyboardButton(text="✅ Разослать"), KeyboardButton(text="❌ Отмена") ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def to_organizer_keyboard() -> ReplyKeyboardMarkup:
    """
    Показать в режиме ввода сообщения участника:
    [⬅️ К событию]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ К событию")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def answers_back_keyboard() -> ReplyKeyboardMarkup:
    """
    Клавиатура при просмотре списка ответов:
    [⬅️ К событию]
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⬅️ К событию")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def answers_list_inline(answers: list, limit: int, offset: int, event_id: int, participant_id: int, organizer_id: int) -> InlineKeyboardMarkup:
    """
    Строим Inline-клавиатуру из записей answers = list[asyncpg.Record],
    каждая имеет поля id, message_text, answer_text, answered_at.
    Формат кнопки: первые 3–4 слова исходного сообщения + дата в скобках «dd.MM» 
    или «dd.MM.YYYY» если другой год.
    callback_data = f"view_answer:{msg_id}:{event_id}:{participant_id}:{organizer_id}:{offset}"
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for rec in answers:
        # из rec['message_text'] берём первые 3 слова
        words = rec["message_text"].split()
        short = " ".join(words[:3]) + ("…" if len(words) > 3 else "")
        # форматируем дату
        dt = rec["answered_at"].date()
        if dt.year == date.today().year:
            date_label = f"{dt.day:02d}.{dt.month:02d}"
        else:
            date_label = f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
        btn_text = f"{short} ({date_label})"
        cb = f"view_answer:{rec['id']}:{event_id}:{participant_id}:{organizer_id}:{offset}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])

    # Навигация «⬅️» и «➡️» если нужно
    nav = []
    total = limit + offset  # фактически, вызывающему надо знать общее число, но можно докинуть отдельно
    # Если offset > 0, есть назад
    if offset >= limit:
        prev_offset = offset - limit
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_answers:{event_id}:{participant_id}:{organizer_id}:{prev_offset}"))
    # Если длина answers == limit, значит, возможно, есть ещё «вперёд»
    if len(answers) == limit:
        next_offset = offset + limit
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_answers:{event_id}:{participant_id}:{organizer_id}:{next_offset}"))
    if nav:
        kb.inline_keyboard.append(nav)

    return kb

def author_participants_keyboard() -> ReplyKeyboardMarkup:
    """
    Reply-клавиатура, появляющаяся после нажатия «Участники» автором:
    [Вопросы участников]  — открыть список вопросов, нуждающихся в ответе
    [Список участников]  — статистика по отделам/профилям
    [⬅️ К событию]       — вернуться к просмотру события
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Вопросы участников")],
            [KeyboardButton(text="Список участников")],
            [KeyboardButton(text="⬅️ К событию")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
