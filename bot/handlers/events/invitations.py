# bot/handlers/events/invitations.py

import asyncpg
from aiogram import Router
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from bot.config import DATABASE_URL

router = Router()

# --- Хендлер: Список приглашений ---
@router.message(lambda m: m.text == "📩 Приглашения")
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
