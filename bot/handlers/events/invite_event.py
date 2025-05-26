# bot/handlers/events/invite_event.py

from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import asyncpg
from bot.config import DATABASE_URL
import datetime

router = Router()

@router.message(lambda m: m.text == "📨 Разослать приглашения")
async def handle_send_invitations(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if not event_id:
        await message.answer("Не удалось определить событие для рассылки приглашений.")
        return

    if not message.from_user:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    telegram_id = message.from_user.id

    conn = await asyncpg.connect(DATABASE_URL)
    # Получаем ID пользователя из таблицы users
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await message.answer("Пользователь не найден в системе.")
        return
    user_id = user_row['id']

    # Ограничение: разослать можно не чаще, чем раз в 5 секунд
    row = await conn.fetchrow(
        """
        SELECT created_at FROM invitations
        WHERE event_id = $1 AND inviter_user_id = $2
        ORDER BY created_at DESC LIMIT 1
        """,
        event_id, user_id
    )
    if row and (datetime.datetime.now() - row['created_at']).total_seconds() < 5:
        await conn.close()
        await message.answer("Подождите 5 секунд перед следующей рассылкой приглашений.")
        return

    # Получаем пользователей, которым можно отправить приглашение
    users = await conn.fetch(
        """
        SELECT id FROM users
        WHERE id != $1
          AND id NOT IN (
              SELECT invited_user_id FROM invitations
              WHERE event_id = $2 AND is_accepted = FALSE
          )
        """,
        user_id, event_id
    )
    invited_count = 0
    for user in users:
        await conn.execute(
            """
            INSERT INTO invitations (event_id, invited_user_id, inviter_user_id, is_read, is_accepted, created_at)
            VALUES ($1, $2, $3, FALSE, NULL, $4)
            ON CONFLICT DO NOTHING
            """,
            event_id, user["id"], user_id, datetime.datetime.now()
        )
        invited_count += 1
    await conn.close()
    await message.answer(f"✅ Приглашения разосланы! ({invited_count} пользователей)")

from aiogram import F

@router.message(F.text == "👥 Участники")
async def show_event_participants(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")

    if not event_id:
        await message.answer("⚠️ Событие не выбрано.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("""
        SELECT u.username, u.first_name, u.last_name
        FROM event_participants ep
        JOIN users u ON ep.user_id = u.id
        WHERE ep.event_id = $1
    """, event_id)


    await conn.close()

    if not rows:
        await message.answer("❌ Пока никто не принял приглашение.")
        return

    text = "👥 Участники события:\n\n" + "\n".join(
        f"• {r['last_name']} {r['first_name']} (@{r['username']})" if r['username'] else f"• {r['last_name']} {r['first_name']}"
        for r in rows
    )
    await message.answer(text)

