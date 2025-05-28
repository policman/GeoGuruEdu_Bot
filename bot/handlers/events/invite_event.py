from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError
import asyncpg
import datetime

from bot.config import DATABASE_URL

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
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await message.answer("Пользователь не найден в системе.")
        return
    user_id = user_row['id']

    row = await conn.fetchrow("""
        SELECT created_at FROM invitations
        WHERE event_id = $1 AND inviter_user_id = $2
        ORDER BY created_at DESC LIMIT 1
    """, event_id, user_id)

    if row and (datetime.datetime.now() - row['created_at']).total_seconds() < 5:
        await conn.close()
        await message.answer("Подождите 5 секунд перед следующей рассылкой приглашений.")
        return

    users = await conn.fetch("""
        SELECT id FROM users
        WHERE id != $1
          AND id NOT IN (
              SELECT invited_user_id FROM invitations
              WHERE event_id = $2 AND is_accepted = FALSE
          )
    """, user_id, event_id)

    invited_count = 0
    for user in users:
        await conn.execute("""
            INSERT INTO invitations (event_id, invited_user_id, inviter_user_id, is_read, is_accepted, created_at)
            VALUES ($1, $2, $3, FALSE, NULL, $4)
            ON CONFLICT DO NOTHING
        """, event_id, user["id"], user_id, datetime.datetime.now())
        invited_count += 1

    await conn.close()
    await message.answer(f"✅ Приглашения разосланы! ({invited_count} пользователей)")


@router.message(F.text == "👥 Участники")
async def show_event_participants(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if not event_id:
        await message.answer("⚠️ Событие не выбрано.")
        return

    conn = await asyncpg.connect(DATABASE_URL)

    participants = await conn.fetch("""
        SELECT u.username, u.first_name, u.last_name
        FROM event_participants ep
        JOIN users u ON ep.user_id = u.id
        WHERE ep.event_id = $1
    """, event_id)

    text = "👥 <b>Участники события:</b>\n\n"
    if participants:
        text += "\n".join(
            f"• {r['last_name']} {r['first_name']} (@{r['username']})" if r['username']
            else f"• {r['last_name']} {r['first_name']}" for r in participants
        )
    else:
        text += "❌ Пока никто не присоединился."

    await message.answer(text, parse_mode="HTML")

    requests = await conn.fetch("""
        SELECT inv.id AS invitation_id, u.first_name, u.last_name, u.username
        FROM invitations inv
        JOIN users u ON u.id = inv.invited_user_id
        WHERE inv.event_id = $1
    AND inv.approved_by_author IS NULL
    AND inv.invited_user_id = inv.inviter_user_id  -- только заявки, поданные самими пользователями

    """, event_id)

    await conn.close()

    if not requests:
        return

    await message.answer("<b>Заявки на участие:</b>", parse_mode="HTML")
    for req in requests:
        user_text = f"👤 {req['last_name']} {req['first_name']} (@{req['username']})" if req['username'] else f"👤 {req['last_name']} {req['first_name']}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_request:{req['invitation_id']}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_request:{req['invitation_id']}")
            ]
        ])
        await message.answer(user_text, reply_markup=kb)


@router.callback_query(F.data.startswith("approve_request:"))
async def approve_request(callback: CallbackQuery):
    data = callback.data
    if not data:
        await callback.answer("Ошибка: пустые данные.")
        return

    invitation_id = int(data.split(":")[1])
    bot = callback.bot
    assert bot is not None

    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("""
        SELECT event_id, invited_user_id, u.telegram_id, e.title
        FROM invitations i
        JOIN users u ON u.id = i.invited_user_id
        JOIN events e ON e.id = i.event_id
        WHERE i.id = $1
    """, invitation_id)

    if not row:
        await conn.close()
        await callback.answer("Заявка не найдена.")
        return

    await conn.execute("""
        UPDATE invitations
        SET approved_by_author = TRUE, is_read = TRUE
        WHERE id = $1
    """, invitation_id)

    await conn.execute("""
        INSERT INTO event_participants (event_id, user_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
    """, row['event_id'], row['invited_user_id'])

    await conn.close()

    try:
        await bot.send_message(
            chat_id=row['telegram_id'],
            text=f"✅ Ваша заявка на участие в событии \"{row['title']}\" была одобрена!"
        )
    except TelegramForbiddenError:
        pass



    if isinstance(callback.message, Message):
        await callback.message.edit_text("✅ Заявка принята.")



@router.callback_query(F.data.startswith("reject_request:"))
async def reject_request(callback: CallbackQuery):
    data = callback.data
    if not data:
        await callback.answer("Ошибка: пустые данные.")
        return

    invitation_id = int(data.split(":")[1])

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        UPDATE invitations
        SET approved_by_author = FALSE, is_read = TRUE
        WHERE id = $1
    """, invitation_id)
    await conn.close()

    if isinstance(callback.message, Message):
       await callback.message.edit_text("❌ Заявка отклонена.")
