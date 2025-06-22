from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv

from bot.keyboards.events.manage_event import (
    to_organizer_keyboard,
    answers_back_keyboard,
    answers_list_inline,
    author_participants_keyboard,
)
from bot.states.event_states import EventView
from bot.services.event_service import EventService
from bot.database.user_repo import get_user_by_telegram_id
from bot.handlers.events.view import handle_show_event

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

router = Router()


class FakeCallback:
    """
    Используется для повторного вызова handle_show_event.
    """
    def __init__(self, data: str, from_user, message: Message, bot):
        self.data = data
        self.from_user = from_user
        self.message = message
        self.bot = bot

    async def answer(self, *args, **kwargs):
        return None


@router.message(StateFilter(EventView.viewing_events), lambda m: m.text == "Написать организатору")
async def start_writing_to_organizer(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if event_id is None:
        await message.answer("❌ Событие не задано.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    ev_row = await conn.fetchrow("SELECT author_id FROM events WHERE id = $1", event_id)
    await conn.close()
    if ev_row is None:
        await message.answer("❌ Не удалось получить организатора.")
        return

    organizer_id = ev_row["author_id"]
    await state.update_data(writing_event_id=event_id, organizer_id=organizer_id)

    conn = await asyncpg.connect(DATABASE_URL)
    org_row = await conn.fetchrow("SELECT first_name, last_name FROM users WHERE id = $1", organizer_id)
    await conn.close()
    if org_row is not None:
        org_name = f"{org_row['first_name']} {org_row['last_name']}"
    else:
        org_name = "Организатор"

    kb = to_organizer_keyboard()
    await message.answer(
        f"Напишите сообщение для организатора {org_name}.\nМаксимум 300 символов:",
        reply_markup=kb
    )
    await state.set_state(EventView.writing_to_organizer)


@router.message(StateFilter(EventView.writing_to_organizer), lambda m: m.text == "⬅️ К событию")
async def cancel_write_to_organizer(message: Message, state: FSMContext):
    await state.update_data(writing_event_id=None, organizer_id=None)

    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    if event_id is None:
        await state.set_state(EventView.viewing_events)
        return

    fake_cb = FakeCallback(
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user,
        message=message,
        bot=message.bot
    )
    await handle_show_event(fake_cb, state)
    await state.set_state(EventView.viewing_events)


@router.message(StateFilter(EventView.writing_to_organizer))
async def save_message_to_organizer(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Введите непустой текст (или «⬅️ К событию»).")
        return
    if len(text) > 300:
        await message.answer("Слишком длинное сообщение, максимум 300 символов. Пожалуйста, сократите.")
        return

    data = await state.get_data()
    event_id = data.get("writing_event_id")
    organizer_id = data.get("organizer_id")
    from_user = message.from_user
    if event_id is None or organizer_id is None or from_user is None:
        await message.answer("Ошибка. Попробуйте снова.")
        await state.set_state(EventView.viewing_events)
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", from_user.id)
    if user_row is None:
        await conn.close()
        await message.answer("❌ Участник не найден.")
        await state.set_state(EventView.viewing_events)
        return
    participant_db_id = user_row["id"]

    service = EventService(conn)
    await service.save_participant_message(
        event_id=event_id,
        from_user_id=participant_db_id,
        to_user_id=organizer_id,
        text=text
    )
    await conn.close()

    await message.answer("✅ Ваше сообщение отправлено организатору.", reply_markup=ReplyKeyboardRemove())
    await state.update_data(writing_event_id=None, organizer_id=None)

    data = await state.get_data()
    source = data.get("source", "active")
    page = data.get("page", 0)

    fake_cb = FakeCallback(
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user,
        message=message,
        bot=message.bot
    )
    await handle_show_event(fake_cb, state)
    await state.set_state(EventView.viewing_events)


@router.message(StateFilter(EventView.viewing_events), lambda m: m.text == "Ответы организатора")
async def show_answers_to_participant(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if event_id is None:
        await message.answer("❌ Событие не задано.")
        return

    user = message.from_user
    if user is None:
        await message.answer("❌ Не удалось определить пользователя.")
        return
    participant_telegram = user.id

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", participant_telegram)
    if user_row is None:
        await conn.close()
        await message.answer("❌ Участник не найден.")
        return
    participant_db_id = user_row["id"]

    ev_row = await conn.fetchrow("SELECT author_id FROM events WHERE id = $1", event_id)
    if ev_row is None:
        await conn.close()
        await message.answer("❌ Не удалось найти событие.")
        return
    organizer_id = ev_row["author_id"]

    service = EventService(conn)
    total = await service.count_answers_for_participant(event_id, participant_db_id, organizer_id)

    limit = 5
    offset = 0
    answers = await service.fetch_answers_for_participant(
        event_id, participant_db_id, organizer_id, limit, offset
    )
    await conn.close()

    if not answers:
        await message.answer("Пока нет ответов от организатора.", reply_markup=answers_back_keyboard())
        return

    kb = answers_list_inline(
        answers, limit, offset, event_id, participant_db_id, organizer_id
    )
    await message.answer("Выберите ответ, чтобы прочитать полностью:", reply_markup=kb)
    await state.update_data(
        paging_event_id=event_id,
        paging_participant_id=participant_db_id,
        paging_organizer_id=organizer_id,
        paging_offset=offset
    )
    await state.set_state(EventView.paging_answers)

@router.message(StateFilter(EventView.viewing_events), lambda m: m.text == "👥 Участники")
async def author_open_participants(message: Message, state: FSMContext):
    """
    Эта вьюшка вызывается, когда автор нажимает «👥 Участники».
    Показываем reply-клавиатуру:
    [Вопросы участников]
    [Список участников]
    [⬅️ К событию]
    """
    data = await state.get_data()
    event_id = data.get("event_id")
    if event_id is None:
        await message.answer("❌ Событие не задано.")
        return

    # Переходим в новый подрежим
    await message.answer("Что вы хотите посмотреть?", reply_markup=author_participants_keyboard())
    await state.set_state(EventView.viewing_participants_menu)

@router.message(StateFilter(EventView.viewing_participants_menu), lambda m: m.text == "Список участников")
async def author_show_participant_stats(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if event_id is None:
        await message.answer("❌ Событие не задано.")
        return

    # Получаем ID автора (организатора) по event_id
    conn = await asyncpg.connect(DATABASE_URL)
    ev_row = await conn.fetchrow("SELECT author_id FROM events WHERE id = $1", event_id)
    if ev_row is None:
        await conn.close()
        await message.answer("❌ Событие не найдено.")
        await state.set_state(EventView.viewing_events)
        return

    author_id = ev_row["author_id"]
    # Проверим, что текущий пользователь — действительно автор
    from_user = message.from_user
    if from_user is None:
        await message.answer("❌ Не удалось определить отправителя.")
        return
    participant_telegram = from_user.id

    user_row = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        participant_telegram
    )

    if user_row is None or user_row["id"] != author_id:
        await conn.close()
        await message.answer("❌ Только организатор может просматривать участников.")
        await state.set_state(EventView.viewing_events)
        return

    # Собираем статистику
    service = EventService(conn)
    stats = await service.get_participant_stats(event_id)
    await conn.close()

    text_lines: list[str] = []
    # Отделы
    text_lines.append("📊 Участники по отделам:")
    for dept, cnt in stats["departments"].items():
        text_lines.append(f"{dept} — {cnt} чел.")
    # Если словарь professions пустой, просто не добавляем эту секцию
    if stats["professions"]:
        text_lines.append("")  # пустая строка
        text_lines.append("📋 Участники по профилям:")
        for prof, cnt in stats["professions"].items():
            text_lines.append(f"{prof} — {cnt} чел.")


    text = "\n".join(text_lines)
    # Кнопка «⬅️ К событию»
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ К событию")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(text, reply_markup=kb)
    # Остаёмся в меню просмотра участников, но следующая «↩️ К событию» вернёт назад
    await state.set_state(EventView.viewing_participants_menu)

@router.message(StateFilter(EventView.viewing_participants_menu), lambda m: m.text == "Вопросы участников")
async def author_show_questions(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if event_id is None:
        await message.answer("❌ Событие не задано.")
        return

    # Проверим, что текущий пользователь — автор
    conn = await asyncpg.connect(DATABASE_URL)
    ev_row = await conn.fetchrow("SELECT author_id FROM events WHERE id = $1", event_id)
    if ev_row is None:
        await conn.close()
        await message.answer("❌ Событие не найдено.")
        await state.set_state(EventView.viewing_events)
        return

    author_id = ev_row["author_id"]
    from_user = message.from_user
    if from_user is None:
        await message.answer("❌ Не удалось определить отправителя.")
        return
    participant_telegram = from_user.id

    user_row = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        participant_telegram
    )

    if user_row is None or user_row["id"] != author_id:
        await conn.close()
        await message.answer("❌ Только организатор может просматривать вопросы.")
        await state.set_state(EventView.viewing_events)
        return

    # Подсчитываем и забираем первые вопросы
    service = EventService(conn)
    total = await service.count_unanswered_questions(event_id, author_id)
    limit = 5
    offset = 0
    questions = await service.fetch_unanswered_questions(event_id, author_id, limit, offset)
    await conn.close()

    if not questions:
        await message.answer("❌ Пока нет вопросов от участников.", reply_markup=answers_back_keyboard())
        await state.set_state(EventView.viewing_participants_menu)
        return

    # Строим inline-клавиатуру для вопросов (используем первые 3 слова + дата)
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for rec in questions:
        words = rec["message_text"].split()
        short = " ".join(words[:3]) + ("…" if len(words) > 3 else "")
        dt = rec["created_at"].date()
        if dt.year == datetime.today().year:
            date_label = f"{dt.day:02d}.{dt.month:02d}"
        else:
            date_label = f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
        btn_text = f"{short} ({date_label})"
        cb = f"view_question:{rec['id']}:{event_id}:{author_id}:{offset}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])

    # Пагинация: «⬅️» и «➡️», если нужно
    nav = []
    if offset >= limit:
        prev_offset = offset - limit
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_questions:{event_id}:{author_id}:{prev_offset}"))
    if len(questions) == limit:
        next_offset = offset + limit
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_questions:{event_id}:{author_id}:{next_offset}"))
    if nav:
        kb.inline_keyboard.append(nav)

    await message.answer("📨 Выберите вопрос, чтобы прочитать и ответить:", reply_markup=kb)
    await state.update_data(
        paging_event_id=event_id,
        paging_organizer_id=author_id,
        paging_offset_questions=offset
    )
    await state.set_state(EventView.paging_questions)

@router.callback_query(StateFilter(EventView.paging_questions), lambda c: c.data and c.data.startswith("page_questions:"))
async def page_questions(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = callback.message
    if not isinstance(msg, Message):
        return

    # разбираем callback.data, вытаскиваем event_id, organizer_id, offset
    if callback.data is None:
        return

    _, event_id_str, author_id_str, offset_str = callback.data.split(":")
    event_id = int(event_id_str)
    organizer_id = int(author_id_str)
    offset = int(offset_str)

    limit = 5
    conn = await asyncpg.connect(DATABASE_URL)
    service = EventService(conn)
    questions = await service.fetch_unanswered_questions(event_id, organizer_id, limit, offset)
    await conn.close()

    if not questions:
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for rec in questions:
        words = rec["message_text"].split()
        short = " ".join(words[:3]) + ("…" if len(words) > 3 else "")
        dt = rec["created_at"].date()
        if dt.year == datetime.today().year:
            date_label = f"{dt.day:02d}.{dt.month:02d}"
        else:
            date_label = f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
        btn_text = f"{short} ({date_label})"
        cb = f"view_question:{rec['id']}:{event_id}:{organizer_id}:{offset}"
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])

    nav = []
    if offset >= limit:
        prev_offset = offset - limit
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_questions:{event_id}:{organizer_id}:{prev_offset}"))
    if len(questions) == limit:
        next_offset = offset + limit
        nav.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_questions:{event_id}:{organizer_id}:{next_offset}"))
    if nav:
        kb.inline_keyboard.append(nav)

    try:
        await msg.edit_reply_markup(reply_markup=kb)
    except:
        await msg.answer("Обновление списка...", reply_markup=kb)

    await state.update_data(paging_offset_questions=offset)
    await state.set_state(EventView.paging_questions)


@router.callback_query(StateFilter(EventView.viewing_events, EventView.paging_questions), lambda c: c.data and c.data.startswith("view_question:"))
async def view_single_question(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    #  ↓ сразу “сужаем” тип:
    msg = callback.message
    if not isinstance(msg, Message):
        return

    if callback.data is None:
        return
    parts = callback.data.split(":")

    msg_id = int(parts[1])
    event_id = int(parts[2])
    organizer_id = int(parts[3])
    offset = int(parts[4])

    conn = await asyncpg.connect(DATABASE_URL)
    rec = await conn.fetchrow(
        """
        SELECT from_user_id, message_text, created_at
        FROM participant_messages
        WHERE id = $1
          AND event_id = $2
          AND to_user_id = $3
          AND is_answered = FALSE
        """,
        msg_id, event_id, organizer_id
    )
    # Узнаем ФИО автора вопроса
    user_row = None
    if rec:
        user_row = await conn.fetchrow(
            "SELECT first_name, last_name FROM users WHERE id = $1",
            rec["from_user_id"]
        )
    await conn.close()

    if rec is None or user_row is None:
        await msg.answer("❌ Вопрос не найден.")
        return

    asker_name = f"{user_row['first_name']} {user_row['last_name']}"
    created_at = rec["created_at"].strftime("%d.%m.%Y %H:%M")
    text = (
        f"📝 <b>Вопрос от участника ({asker_name}, {created_at}):</b>\n"
        f"{rec['message_text']}\n\n"
        "Введите ответ (или «⬅️ К вопросам»), максимум 300 символов:"
    )

    # Ставим состояние «организатор отвечает на вопрос»
    await state.update_data(
        answering_msg_id=msg_id,
        answering_event_id=event_id,
        answering_participant_id=rec["from_user_id"],
        answering_offset=offset
    )
    await msg.answer(text, parse_mode="HTML", reply_markup=to_organizer_keyboard())
    await state.set_state(EventView.answering_question)



@router.message(StateFilter(EventView.answering_question))
async def save_answer_from_organizer(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("Введите непустой ответ (или «⬅️ К вопросам»).")
        return
    if len(text) > 300:
        await message.answer("Слишком длинный ответ, максимум 300 символов. Пожалуйста, сократите.")
        return

    data = await state.get_data()
    msg_id = data.get("answering_msg_id")
    event_id = data.get("answering_event_id")
    participant_db_id = data.get("answering_participant_id")
    offset = data.get("answering_offset")
    if not all([msg_id, event_id, participant_db_id]):
        await message.answer("Ошибка. Попробуйте снова.")
        await state.set_state(EventView.viewing_participants_menu)
        return

    conn = await asyncpg.connect(DATABASE_URL)
    # Сохраняем ответ: обновляем запись
    answered_at = datetime.now()
    await conn.execute(
        """
        UPDATE participant_messages
        SET answer_text = $1,
            answered_at = $2,
            is_answered = TRUE
        WHERE id = $3
        """,
        text, answered_at, msg_id
    )
    await conn.close()

    await message.answer("✅ Ответ отправлен участнику.", reply_markup=author_participants_keyboard())

    # Возвращаемся к списку «Вопросов участников»
    data = await state.get_data()
    event_id = data.get("answering_event_id")
    organizer_id = data.get("answering_organizer_id") or data.get("paging_organizer_id")
    offset = data.get("answering_offset", 0)

    # Снова пробрасываем paging_questions с тем же offset
    fake_cb = FakeCallback(
        data=f"page_questions:{event_id}:{organizer_id}:{offset}",
        from_user=message.from_user,
        message=message,
        bot=message.bot
    )
    await page_questions(fake_cb, state)
    await state.set_state(EventView.paging_questions)


@router.callback_query(StateFilter(EventView.paging_answers), lambda c: c.data and c.data.startswith("page_answers:"))
async def page_answers(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    assert callback.data is not None
    _, event_id_str, part_id_str, org_id_str, offset_str = callback.data.split(":")
    event_id = int(event_id_str)
    participant_db_id = int(part_id_str)
    organizer_id = int(org_id_str)
    offset = int(offset_str)

    limit = 5
    conn = await asyncpg.connect(DATABASE_URL)
    service = EventService(conn)
    answers = await service.fetch_answers_for_participant(
        event_id, participant_db_id, organizer_id, limit, offset
    )
    await conn.close()

    if not answers:
        return

    kb = answers_list_inline(
        answers, limit, offset, event_id, participant_db_id, organizer_id
    )

    from aiogram.types import Message as AiogramMessage
    if callback.message is not None and isinstance(callback.message, AiogramMessage):
        try:
            await callback.message.edit_reply_markup(reply_markup=kb)
        except:
            await callback.message.answer("Обновление списка...", reply_markup=kb)

    await state.update_data(paging_offset=offset)
    await state.set_state(EventView.paging_answers)


@router.callback_query(StateFilter(EventView.paging_answers), lambda c: c.data and c.data.startswith("view_answer:"))
async def view_single_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    assert callback.data is not None
    parts = callback.data.split(":")
    msg_id = int(parts[1])
    event_id = int(parts[2])
    participant_db_id = int(parts[3])
    organizer_id = int(parts[4])
    offset = int(parts[5])

    conn = await asyncpg.connect(DATABASE_URL)
    rec = await conn.fetchrow(
        """
        SELECT message_text, answer_text, answered_at
        FROM participant_messages
        WHERE id = $1
          AND event_id = $2
          AND from_user_id = $3
          AND to_user_id = $4
          AND is_answered = TRUE
        """,
        msg_id, event_id, participant_db_id, organizer_id
    )
    await conn.close()
    if rec is None:
        from aiogram.types import Message as AiogramMessage
        if callback.message is not None and isinstance(callback.message, AiogramMessage):
            await callback.message.answer("❌ Ответ не найден.")
        return

    answered_at = rec["answered_at"]
    assert answered_at is not None
    answered_label = answered_at.strftime("%d.%m.%Y %H:%M")
    text = (
        f"📨 <b>Ваше сообщение:</b>\n"
        f"{rec['message_text']}\n\n"
        f"✅ <b>Ответ от организатора ({answered_label}):</b>\n"
        f"{rec['answer_text']}"
    )
    kb = answers_back_keyboard()
    from aiogram.types import Message as AiogramMessage
    if callback.message is not None and isinstance(callback.message, AiogramMessage):
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await state.set_state(EventView.viewing_events)


@router.message(StateFilter(EventView.viewing_events), lambda m: m.text == "⬅️ К событию")
async def back_to_event_from_chat(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("paging_event_id") or data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    if event_id is None:
        await state.set_state(EventView.viewing_events)
        return

    fake_cb = FakeCallback(
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user,
        message=message,
        bot=message.bot
    )
    await handle_show_event(fake_cb, state)
    await state.set_state(EventView.viewing_events)


async def get_participant_stats(self, event_id: int) -> dict:
    """
    Возвращает словарь вида:
    {
        "departments": { "Отдел1": 3, "Отдел2": 1, ... },
        "professions": { "Программист": 3, "Экономист": 1, ... }
    }
    """
    # Предполагаем, что у таблицы users есть поля department и profession
    rows = await self.conn.fetch(
        """
        SELECT u.department, u.profession
        FROM users AS u
        JOIN event_participants AS ep ON ep.user_id = u.id
        WHERE ep.event_id = $1
        """,
        event_id
    )
    dept_counts: dict[str, int] = {}
    prof_counts: dict[str, int] = {}
    for r in rows:
        d = r["department"] or "Не указан"
        p = r["profession"] or "Не указана"
        dept_counts[d] = dept_counts.get(d, 0) + 1
        prof_counts[p] = prof_counts.get(p, 0) + 1
    return {"departments": dept_counts, "professions": prof_counts}

async def fetch_unanswered_questions(self, event_id: int, organizer_id: int, limit: int, offset: int) -> list[asyncpg.Record]:
    """
    Возвращает list записей (id, message_text, from_user_id, created_at)
    для вопросов (is_answered = FALSE), отсортированных по created_at DESC.
    """
    return await self.conn.fetch(
        """
        SELECT id, message_text, from_user_id, created_at
        FROM participant_messages
        WHERE event_id = $1
          AND to_user_id = $2
          AND is_answered = FALSE
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4
        """,
        event_id, organizer_id, limit, offset
    )

async def count_unanswered_questions(self, event_id: int, organizer_id: int) -> int:
    row = await self.conn.fetchrow(
        """
        SELECT COUNT(*) AS cnt
        FROM participant_messages
        WHERE event_id = $1
          AND to_user_id = $2
          AND is_answered = FALSE
        """,
        event_id, organizer_id
    )
    return row["cnt"] if row else 0
    
# Вернуться к просмотру события из меню «Участники» или «Вопросы»
@router.message(StateFilter(EventView.viewing_participants_menu), lambda m: m.text == "⬅️ К событию")
@router.message(StateFilter(EventView.viewing_events),            lambda m: m.text == "⬅️ К событию")
@router.message(StateFilter(EventView.paging_questions),          lambda m: m.text == "⬅️ К событию")
@router.message(StateFilter(EventView.answering_question),         lambda m: m.text == "⬅️ К событию")
@router.message(StateFilter(EventView.paging_questions),          lambda m: m.text == "⬅️ К вопросам")
async def back_to_event_or_questions(message: Message, state: FSMContext):
    data = await state.get_data()
    # Если мы были в подменю «Пагинация вопросов» — возвращаемся к списку «Вопросы участников»
    if await state.get_state() == EventView.paging_questions and message.text == "⬅️ К вопросам":
        event_id = data.get("paging_event_id")
        organizer_id = data.get("paging_organizer_id")
        offset = data.get("paging_offset_questions", 0)
        if event_id and organizer_id is not None:
            fake_cb = FakeCallback(
                data=f"page_questions:{event_id}:{organizer_id}:{offset}",
                from_user=message.from_user,
                message=message,
                bot=message.bot
            )
            await page_questions(fake_cb, state)
            await state.set_state(EventView.paging_questions)
            return

    # Иначе — просто вернуться к просмотру события
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)
    if event_id is None:
        await state.set_state(EventView.viewing_events)
        return

    fake_cb = FakeCallback(
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user,
        message=message,
        bot=message.bot
    )
    await handle_show_event(fake_cb, state)
    await state.set_state(EventView.viewing_events)
