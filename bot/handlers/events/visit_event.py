from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.keyboards.events.view_event import visit_event_keyboard
from bot.keyboards.events.my_events import my_events_keyboard
import asyncpg
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.config import DATABASE_URL
from typing import cast
from aiogram.types import Message
from bot.states.event_states import VisitEvent
from aiogram.filters import StateFilter


router = Router()


# Главное меню "Посетить событие"
@router.message(lambda m: m.text == "Посетить событие")
async def handle_visit_event_menu(message: Message, state: FSMContext):
    await message.answer(
        "Раздел посещения событий:",
        reply_markup=visit_event_keyboard
    )

# Список всех доступных событий других пользователей
@router.message(lambda m: m.text == "Список событий")
async def handle_list_all_events(message: Message, state: FSMContext):
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    telegram_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await message.answer("Пользователь не найден.")
        return
    user_id = user_row["id"]

    events = await conn.fetch(
        """
        SELECT id, title, start_date, end_date, organizers
        FROM events
        WHERE author_id != $1
          AND is_draft = FALSE
          AND end_date >= CURRENT_DATE
        ORDER BY start_date
        """,
        user_id
    )
    await conn.close()

    if not events:
        await message.answer("Нет доступных событий.")
        return

    for ev in events:
        text = (
            f"<b>{ev['title']}</b>\n"
            f"📅 {ev['start_date']} – {ev['end_date']}\n"
            f"👤 Организатор: {ev['organizers']}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📨 Подать заявку",
                        callback_data=f"apply_event:{ev['id']}"
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")




@router.message(lambda m: m.text == "Поиск")
async def handle_search_events(message: Message, state: FSMContext):
    await state.set_state(VisitEvent.search_query)
    await message.answer("🔎 Введите текст для поиска по событиям (в названии или описании):")


# --- Хендлер: Список приглашений ---
@router.message(lambda m: m.text == "Приглашения")
async def handle_invitations(message: Message, state):
    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    telegram_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await message.answer("Пользователь не найден в системе.")
        return
    user_id = user_row["id"]

    invitations = await conn.fetch(
        """
        SELECT inv.id as invitation_id, ev.id as event_id, ev.title, ev.start_date, ev.organizers
        FROM invitations inv
        JOIN events ev ON ev.id = inv.event_id
        WHERE inv.invited_user_id = $1 AND inv.is_accepted IS NULL
        """,
        user_id
    )
    await conn.close()

    if not invitations:
        await message.answer("У вас нет новых приглашений.")
        return

    for inv in invitations:
        text = (
            f"Приглашение на событие:\n"
            f"<b>{inv['title']}</b>\n"
            f"Дата: {inv['start_date']}\n"
            f"Организатор: {inv['organizers']}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Принять",
                        callback_data=f"accept_invite:{inv['invitation_id']}:{inv['event_id']}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"decline_invite:{inv['invitation_id']}"
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

# Назад (к “Мои события”)
@router.message(lambda m: m.text == "⬅️ Назад")
async def handle_back_from_visit_event(message: Message, state: FSMContext):
    await message.answer(
        "Вы вернулись к списку своих событий.",
        reply_markup=my_events_keyboard
    )


# --- Хендлер: Принять приглашение ---
@router.callback_query(lambda c: c.data and c.data.startswith("accept_invite:"))
async def handle_accept_invite(callback: CallbackQuery):
    if not callback.data:
        await callback.answer("Ошибка данных!", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Ошибка данных!", show_alert=True)
        return
    invitation_id = int(parts[1])
    event_id = int(parts[2])
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "UPDATE invitations SET is_accepted = TRUE, is_read = TRUE WHERE id = $1",
        invitation_id
    )
    user_row = await conn.fetchrow("SELECT invited_user_id FROM invitations WHERE id = $1", invitation_id)
    if user_row:
        await conn.execute(
            """
            INSERT INTO event_participants (event_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            event_id, user_row["invited_user_id"]
        )
    await conn.close()
    await callback.answer("Вы приняли приглашение!")
    try:
        await callback.message.edit_text("✅ Приглашение принято, вы добавлены в участники события.")  # type: ignore[attr-defined]
    except AttributeError:
        pass

# --- Хендлер: Отклонить приглашение ---
@router.callback_query(lambda c: c.data and c.data.startswith("decline_invite:"))
async def handle_decline_invite(callback: CallbackQuery):
    if not callback.data:
        await callback.answer("Ошибка данных!", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) < 2:
        await callback.answer("Ошибка данных!", show_alert=True)
        return
    invitation_id = int(parts[1])
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "UPDATE invitations SET is_accepted = FALSE, is_read = TRUE WHERE id = $1",
        invitation_id
    )
    await conn.close()
    await callback.answer("Приглашение отклонено.")
    try:
        await callback.message.edit_text("❌ Приглашение отклонено.")  # type: ignore[attr-defined]
    except AttributeError:
        pass


@router.callback_query(lambda c: c.data and c.data.startswith("apply_event:"))
async def handle_apply_for_event(callback: CallbackQuery):
    data = callback.data
    if not data:
        await callback.answer("Ошибка: нет данных.", show_alert=True)
        return

    parts = data.split(":")
    if len(parts) < 2:
        await callback.answer("Ошибка в формате данных.", show_alert=True)
        return

    event_id = int(parts[1])
    user = callback.from_user
    if not user:
        await callback.answer("Не удалось определить пользователя.", show_alert=True)
        return

    telegram_id = user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    user_id = user_row["id"]

    await conn.execute(
        """
        INSERT INTO invitations (event_id, invited_user_id, inviter_user_id, is_read, is_accepted, created_at)
        VALUES ($1, $2, $3, FALSE, NULL, NOW())
        ON CONFLICT DO NOTHING
        """,
        event_id, user_id, user_id
    )
    await conn.close()

    if callback.message:
        msg = cast(Message, callback.message)
        try:
            await msg.edit_reply_markup(reply_markup=None)
            await msg.answer("✅ Заявка подана.")
        except Exception:
            pass
    else:
        await callback.answer("✅ Заявка подана.")

@router.message(StateFilter(VisitEvent.search_query))
async def process_search_query(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("⚠️ Пожалуйста, введите текст для поиска.")
        return
    search_text = message.text.strip().lower()

    if not message.from_user:
        await message.answer("Не удалось определить пользователя.")
        return

    telegram_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await message.answer("Пользователь не найден.")
        return
    user_id = user_row["id"]

    results = await conn.fetch(
        """
        SELECT id, title, start_date, end_date, organizers
        FROM events
        WHERE author_id != $1
        AND is_draft = FALSE
        AND end_date >= CURRENT_DATE
        AND (
            title ILIKE '%' || $2 || '%' OR
            description ILIKE '%' || $2 || '%'
        )
        ORDER BY start_date
        """,
        user_id, search_text
    )


    await conn.close()
    await state.clear()

    if not results:
        await message.answer("❌ События не найдены.")
        return

    for ev in results:
        text = (
            f"<b>{ev['title']}</b>\n"
            f"📅 {ev['start_date']} – {ev['end_date']}\n"
            f"👤 Организатор: {ev['organizers']}"
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📨 Подать заявку",
                        callback_data=f"apply_event:{ev['id']}"
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
