from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
import asyncpg
from datetime import datetime
from bot.config import DATABASE_URL
from .format_event_dates import format_event_dates
#from .get_user_by_telegram_id import get_user_by_telegram_id
from aiogram import Bot
from typing import cast, Any
from bot.states.event_states import VisitEvent
from bot.keyboards.events.view_event import visit_event_keyboard
from aiogram import Router, F
from bot.database.user_repo import get_user_by_telegram_id  # добавь в импорты

# Храним ID сообщений для удаления
deleted_messages: dict[int, list[int]] = {}

router = Router()

EVENTS_PER_PAGE = 3

async def show_event_list(msg: Message, state: FSMContext):
    if not isinstance(msg, Message):
        return
    
    bot = cast(Bot, msg.bot)
    user_id_tg = msg.chat.id

    print("💬 Telegram ID:", user_id_tg)
    if user_id_tg is None:
        await msg.answer("Пользователь не найден.")
        return
    await clear_event_messages(bot, user_id_tg, msg.chat.id)

    # Удаляем все предыдущие сообщения пользователя (если были)
    if user_id_tg not in deleted_messages:
        deleted_messages[user_id_tg] = []
    else:
        for mid in deleted_messages[user_id_tg]:
            try:
                await bot.delete_message(chat_id=msg.chat.id, message_id=mid)
            except:
                pass
        deleted_messages[user_id_tg] = []


    if not msg.from_user:
        await msg.answer("⚠️ Не удалось определить пользователя.")
        return
    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, msg.chat.id)

    if user is None:
        await msg.answer("Пользователь не найден.")
        await conn.close()
        return

    user_id: int = user["id"]  # теперь Pylance не ругается


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

    filters = ["author_id IS DISTINCT FROM $1", "is_draft = FALSE", "end_date >= CURRENT_DATE"]

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
    offset = page * EVENTS_PER_PAGE

    # Разделяем параметры
    params_for_count = params.copy()  # без offset
    params_for_select = params + [offset]  # с offset

    query = f"""
        SELECT id, title, description, start_date, end_date, organizers, price, photo, author_id
        FROM events
        WHERE {where_clause}
        ORDER BY start_date
        LIMIT {EVENTS_PER_PAGE} OFFSET ${len(params_for_select)}
    """

    events = await conn.fetch(query, *params_for_select)

    total_events = await conn.fetchval(
        f"SELECT COUNT(*) FROM events WHERE {where_clause}",
        *params_for_count
    )
    total_pages = max((total_events + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE, 1)



    participant_ids = {
        row['event_id']
        for row in await conn.fetch("""
            SELECT event_id FROM event_participants
            WHERE user_id = $1
        """, user_id)
    }

    applied_ids = {
        row['event_id']
        for row in await conn.fetch("""
            SELECT event_id FROM invitations
            WHERE invited_user_id = $1
            AND inviter_user_id IS NULL
            AND is_accepted IS NULL
        """, user_id)
    }


    await conn.close()

    # Получаем количество участников по всем event_id одной выборкой
    event_ids = [ev["id"] for ev in events]
    participant_counts = {}

    if event_ids:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch("""
            SELECT event_id, COUNT(*) AS count
            FROM event_participants
            WHERE event_id = ANY($1::int[])
            GROUP BY event_id
        """, event_ids)
        await conn.close()

        participant_counts = {row["event_id"]: row["count"] for row in rows}

    if not events:
        msg_sent = await msg.answer("Нет событий по заданным фильтрам.")
        deleted_messages[user_id_tg].append(msg_sent.message_id)
        return

    for ev in events:
        print("🔎 applied_ids:", applied_ids)
        print("🔎 participant_ids:", participant_ids)

        print(f"Event ID: {ev['id']}, Title: {ev['title']}, Author ID: {ev.get('author_id')}, Current User ID: {user_id}")

        caption = f"<b>{ev['title']}</b>\n<i>{ev['description']}</i>\n\n📅 {format_event_dates(ev['start_date'], ev['end_date'])}\n👤 Организатор: {ev['organizers']}\n💰 Стоимость: {'бесплатно' if ev['price'] == 0 else str(ev['price']) + '₽'}"
        participant_count = participant_counts.get(ev["id"], 0)
        caption += f"\n👥 Участников: {participant_count}"

        # Inline-кнопка
        if ev["id"] in participant_ids:
            kb = InlineKeyboardMarkup(inline_keyboard=[])
            caption += "\n\n✅ Вы участвуете"
        elif ev["id"] in applied_ids:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="⏳ В обработке", callback_data="noop")]]
            )
            caption += "\n\n⏳ Заявка в обработке"
        else:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📨 Подать заявку", callback_data=f"apply_event:{ev['id']}")]]
            )


        # Отправка одного сообщения с медиа и описанием
        # Сначала пытаемся достать file_id из ev["photo"]
        file_id = None
        raw_photo = ev.get("photo")

        # Вариант A: если в БД вы храните photo как одиночная строка (TEXT)
        if isinstance(raw_photo, str) and raw_photo.strip():
            file_id = raw_photo.strip()

        # Вариант B: если в БД photo хранится в виде массива (TEXT[]), то raw_photo будет list
        elif isinstance(raw_photo, (list, tuple)) and raw_photo:
            candidate = raw_photo[0]
            if isinstance(candidate, str) and candidate.strip():
                file_id = candidate.strip()

        # Теперь проверяем, удалось ли получить строку подходящей длины
        if file_id and len(file_id) > 20:
            # Попробуем отправить именно этот file_id
            try:
                media_msg = await bot.send_photo(
                    chat_id=msg.chat.id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
            except Exception:
                # Если Telegram снова вернёт ошибку (неверный file_id), отправим просто текст
                media_msg = await bot.send_message(
                    chat_id=msg.chat.id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb
                )
        else:
            # Если file_id невалиден или отсутствует, просто отправляем текст
            media_msg = await bot.send_message(
                chat_id=msg.chat.id,
                text=caption,
                parse_mode="HTML",
                reply_markup=kb
            )


        deleted_messages[user_id_tg].append(media_msg.message_id)



    if total_pages > 1:
        nav_row = list(filter(None, [
            InlineKeyboardButton(text="⬅️", callback_data="page:prev") if page > 0 else None,
            InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"),
            InlineKeyboardButton(text="➡️", callback_data="page:next") if (page + 1) * EVENTS_PER_PAGE < total_events else None,
        ]))

        msg_sent = await msg.answer(text="Навигация:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_row]))
        deleted_messages[user_id_tg].append(msg_sent.message_id)

    # Формируем описание активных фильтров
    filter_text_lines = ["<b>Активные фильтры:</b>"]
    if organizer:
        filter_text_lines.append(f"Организатор: {organizer}")
    if min_price is not None or max_price is not None:
        price_str = f"{min_price or 0} – {max_price or 0} ₽"
        filter_text_lines.append(f"Цена: {price_str}")
    if start_date_str or end_date_str:
        date_range = f"{start_date_str or '...'} — {end_date_str or '...'}"
        filter_text_lines.append(f"Даты: {date_range}")
    if search_query:
        filter_text_lines.append(f"Поиск: «{search_query}»")

    filter_caption = "\n".join(filter_text_lines)

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

    msg_sent = await msg.answer(filter_caption, reply_markup=filter_kb, parse_mode="HTML")
    deleted_messages[user_id_tg].append(msg_sent.message_id)

    deleted_messages[user_id_tg].append(msg_sent.message_id)

@router.message(F.text == "Выйти из списка")
async def exit_event_list(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы вернулись в меню 'Посетить событие'", reply_markup=visit_event_keyboard)


async def clear_event_messages(bot: Bot, user_id: int, chat_id: int):
    for mid in deleted_messages.get(user_id, []):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except:
            pass
    deleted_messages[user_id] = []
