# bot/handlers/events/chat.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
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


@router.message(StateFilter(EventView.paging_answers), lambda m: m.text == "⬅️ К событию")
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
