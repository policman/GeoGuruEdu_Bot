from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
import asyncpg
from datetime import datetime
from aiogram.utils.media_group import MediaGroupBuilder
from bot.config import DATABASE_URL
from .format_event_dates import format_event_dates
from .get_or_create_user_id import get_or_create_user_id

from aiogram import Bot
from typing import cast, Any

deleted_messages: dict[int, list[int]] = {}

async def show_event_list(msg: Message, state: FSMContext):
    if not isinstance(msg, Message):
        return

    bot = cast(Bot, msg.bot)
    user_id_tg = msg.from_user.id if msg.from_user else None
    if user_id_tg is None:
        await msg.answer("Пользователь не найден.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_id = await get_or_create_user_id(msg)
    if user_id is None:
        await msg.answer("Пользователь не найден.")
        return



    # Удаляем старые сообщения событий и навигации
    if user_id_tg in deleted_messages:
        for message_id in deleted_messages[user_id_tg]:
            try:
                await bot.delete_message(chat_id=msg.chat.id, message_id=message_id)
            except:
                pass
        deleted_messages[user_id_tg] = []
    else:
        deleted_messages[user_id_tg] = []

    data = await state.get_data()
    page = data.get("page", 0)
    organizer = data.get("filter_organizer")
    min_price = data.get("filter_min_price")
    max_price = data.get("filter_max_price")
    start_date_str = data.get("filter_start_date")
    end_date_str = data.get("filter_end_date")
    search_query = data.get("search_query")

    start_date = None
    end_date = None
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        await conn.close()
        await msg.answer("Ошибка формата даты. Используйте формат: YYYY-MM-DD")
        return

    filters = ["author_id != $1", "is_draft = FALSE", "end_date >= CURRENT_DATE"]
    # params = [user_id]

    params: list[Any] = [user_id]

    if organizer:
        filters.append(f"organizers ILIKE '%' || ${len(params)+1} || '%'")
        params.append(organizer)
    if min_price is not None:
        filters.append(f"price >= ${len(params)+1}")
        params.append(min_price)
    if max_price is not None:
        filters.append(f"price <= ${len(params)+1}")
        params.append(max_price)
    if start_date:
        filters.append(f"start_date >= ${len(params)+1}")
        params.append(start_date.isoformat())
    if end_date:
        filters.append(f"end_date <= ${len(params)+1}")
        params.append(end_date.isoformat())
    if search_query:
        filters.append(f"(title ILIKE '%' || ${len(params)+1} || '%' OR description ILIKE '%' || ${len(params)+1} || '%')")
        params.append(search_query)

    where_clause = " AND ".join(filters)
    offset = page * 4
    query = f"""
        SELECT id, title, description, start_date, end_date, organizers, price, photos, videos
        FROM events
        WHERE {where_clause}
        ORDER BY start_date
        OFFSET ${len(params)+1} LIMIT 4
    """

    params_with_offset = params + [offset]
    events = await conn.fetch(query, *params_with_offset)
    total_events = await conn.fetchval(f"SELECT COUNT(*) FROM events WHERE {where_clause}", *params)
    total_pages = max((total_events + 3) // 4, 1)

    participant_ids = {row['event_id'] for row in await conn.fetch("SELECT event_id FROM event_participants WHERE user_id = $1", user_id)}
    applied_ids = {row['event_id'] for row in await conn.fetch("""
        SELECT event_id FROM invitations
        WHERE invited_user_id = $1 AND is_accepted IS DISTINCT FROM FALSE
    """, user_id)}

    await conn.close()

    if not events:
        msg_sent = await msg.answer("Нет событий по заданным фильтрам.")
        deleted_messages[user_id_tg].append(msg_sent.message_id)
        return

    for ev in events:
        media_group = MediaGroupBuilder()
        photos = ev.get("photos") or []
        videos = ev.get("videos") or []
        full_caption = f"<b>{ev['title']}</b>\n\n<i>{ev['description']}</i>"

        if photos:
            media_group.add_photo(media=photos[0], caption=full_caption, parse_mode="HTML")
            for photo in photos[1:]:
                media_group.add_photo(media=photo)
        elif videos:
            media_group.add_video(media=videos[0], caption=full_caption, parse_mode="HTML")
            for video in videos[1:]:
                media_group.add_video(media=video)

        if media_group.build():
            result = await bot.send_media_group(chat_id=msg.chat.id, media=media_group.build())
            for m in result:
                deleted_messages[user_id_tg].append(m.message_id)

        details_text = f"{format_event_dates(ev['start_date'], ev['end_date'])} • {'бесплатно' if ev['price'] == 0 else str(ev['price']) + '₽'} • {ev['organizers']}"
        if ev['id'] in participant_ids:
            details_text += "\n\n✅ Вы участвуете"
            msg_sent = await bot.send_message(chat_id=msg.chat.id, text=details_text)
        elif ev['id'] in applied_ids:
            details_text += "\n\n⌛ Заявка уже подана"
            msg_sent = await bot.send_message(chat_id=msg.chat.id, text=details_text)
        else:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📨 Подать заявку", callback_data=f"apply_event:{ev['id']}")]]
            )
            msg_sent = await bot.send_message(chat_id=msg.chat.id, text=details_text, reply_markup=kb)

        deleted_messages[user_id_tg].append(msg_sent.message_id)

    if total_pages > 1:
        nav_row = list(filter(None, [
            InlineKeyboardButton(text="⬅️", callback_data="page:prev") if page > 0 else None,
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data="page:next") if (page + 1) * 4 < total_events else None,
        ]))

        msg_sent = await msg.answer(text="Навигация по страницам:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_row]))
        deleted_messages[user_id_tg].append(msg_sent.message_id)


    # Блок фильтров остаётся
    filter_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Организатор", callback_data="filter:organizer"),
                InlineKeyboardButton(text="Цена", callback_data="filter:price"),
                InlineKeyboardButton(text="Дата", callback_data="filter:date")
            ],
            [InlineKeyboardButton(text="🔄 Сбросить фильтры", callback_data="filter:reset")]
        ]
    )
    await msg.answer("Фильтры:", reply_markup=filter_kb)
