from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
import asyncpg
from datetime import datetime
from aiogram.utils.media_group import MediaGroupBuilder
from bot.config import DATABASE_URL
from .format_event_dates import format_event_dates  # убедись, что этот хелпер есть и правильно импортирован

async def show_event_list(msg: Message, state: FSMContext):
    if not isinstance(msg, Message) or not msg.from_user:
        return

    bot = msg.bot
    if bot is None:
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", msg.from_user.id)
    if not user_row:
        await conn.close()
        await msg.answer("Пользователь не найден.")
        return
    user_id = user_row["id"]

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
        await msg.answer("Ошибка формата даты. Используйте формат: YYYY-MM-DD:YYYY-MM-DD")
        await conn.close()
        return

    filters = ["author_id != $1", "is_draft = FALSE", "end_date >= CURRENT_DATE"]
    params = [user_id]

    if organizer:
        filters.append(f"organizers ILIKE '%' || ${len(params) + 1} || '%'")
        params.append(organizer)
    if min_price is not None:
        filters.append(f"price >= ${len(params) + 1}")
        params.append(min_price)
    if max_price is not None:
        filters.append(f"price <= ${len(params) + 1}")
        params.append(max_price)
    if start_date:
        filters.append(f"start_date >= ${len(params) + 1}")
        params.append(start_date)
    if end_date:
        filters.append(f"end_date <= ${len(params) + 1}")
        params.append(end_date)
    if search_query:
        filters.append(f"(title ILIKE '%' || ${len(params) + 1} || '%' OR description ILIKE '%' || ${len(params) + 1} || '%')")
        params.append(search_query)

    where_clause = " AND ".join(filters)
    offset = page * 4
    query = f"""
        SELECT id, title, description, start_date, end_date, organizers, price, photos, videos
        FROM events
        WHERE {where_clause}
        ORDER BY start_date
        OFFSET ${len(params) + 1} LIMIT 4
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

    active_filters = []
    if organizer:
        active_filters.append(f"Организатор: {organizer}")
    if min_price or max_price:
        active_filters.append(f"Цена: {min_price or 'от'} – {max_price or 'до'}")
    if start_date_str or end_date_str:
        active_filters.append(f"Дата: {start_date_str or 'от'} – {end_date_str or 'до'}")
    if search_query:
        active_filters.append(f"Поиск: {search_query}")

    if active_filters:
        await msg.answer("🔎 Актуальные фильтры:\n" + "\n".join(f"• {f}" for f in active_filters))

    if not events:
        await msg.answer("Нет событий по заданным фильтрам.")
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
        if photos and videos:
            for video in videos:
                media_group.add_video(media=video)

        if media_group.build():
            await bot.send_media_group(chat_id=msg.chat.id, media=media_group.build())

        details_text = f"{format_event_dates(ev['start_date'], ev['end_date'])} • {'бесплатно' if ev['price'] == 0 else str(ev['price']) + '₽'} • {ev['organizers']}"
        if ev['id'] in participant_ids:
            details_text += "\n\n✅ Вы участвуете"
            await bot.send_message(chat_id=msg.chat.id, text=details_text)
        elif ev['id'] in applied_ids:
            details_text += "\n\n⌛ Заявка уже подана"
            await bot.send_message(chat_id=msg.chat.id, text=details_text)
        else:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📨 Подать заявку", callback_data=f"apply_event:{ev['id']}")]]
            )
            await bot.send_message(chat_id=msg.chat.id, text=details_text, reply_markup=kb)

    nav_row = list(filter(None, [
        InlineKeyboardButton(text="⬅️", callback_data="page:prev") if page > 0 else None,
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"),
        InlineKeyboardButton(text="➡️", callback_data="page:next") if (page + 1) * 4 < total_events else None
    ]))

    if nav_row:
        await msg.answer(text="Навигация по страницам:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_row]))


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
