from aiogram import Router
from aiogram.types import (
    Message, CallbackQuery, InputMediaPhoto, InputMediaAudio, 
    InputMediaDocument, InputMediaVideo, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from typing import Union, Optional, cast
from .format_event_dates import format_event_dates
import asyncpg
import os
from dotenv import load_dotenv

from bot.keyboards.events.my_events import my_events_keyboard


from bot.states.event_states import EventView
from bot.services.event_service import EventService
from bot.database.user_repo import get_user_by_telegram_id
from bot.keyboards.events import events_list_keyboard
from bot.keyboards.events.manage_event import (
    manage_event_keyboard, 
    manage_event_reply_keyboard,
    
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

router = Router()

MediaType = InputMediaAudio | InputMediaDocument | InputMediaPhoto | InputMediaVideo


async def show_event_list(
    message_or_callback: Union[Message, CallbackQuery],
    state: FSMContext,
    source: str,
    page: int = 0
):
    message: Optional[Message] = None
    user_id: Optional[int] = None

    if isinstance(message_or_callback, CallbackQuery):
        msg = message_or_callback.message
        if msg is not None and isinstance(msg, Message):
            message = msg
            user = message_or_callback.from_user
            user_id = user.id if user else None
    elif isinstance(message_or_callback, Message):
        message = message_or_callback
        user = message.from_user
        user_id = user.id if user else None

    if message is None or user_id is None:
        return

    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    db_user = await get_user_by_telegram_id(conn, user_id)

    if not db_user:
        await conn.close()
        await message.answer("❌ Пользователь не найден в системе.")
        return

    if source == "active":
        events = await event_service.get_active_events(db_user["id"])
        title = "Ваши активные события:"
    elif source == "created":
        events = await event_service.get_created_events(db_user["id"])
        title = "Созданные вами события:"
    elif source == "archive":
        events = await event_service.get_archive_events(db_user["id"])
        title = "Архивные события:"
    else:
        events = []
        title = "События"

    await conn.close()


    if not events:
        await message.answer("Событий не найдено.", reply_markup=my_events_keyboard)
        return

    await state.set_state(EventView.viewing_events)

    if isinstance(message_or_callback, CallbackQuery):
        try:
            await message.delete()
        except Exception:
            pass

    await message.answer(title, reply_markup=events_list_keyboard(events, page, source))


@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "📌 Активные")
async def handle_active_events(message: Message, state: FSMContext):
    await show_event_list(message, state, source="active", page=0)


@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "🛠 Созданные")
async def handle_created_events(message: Message, state: FSMContext):
    await show_event_list(message, state, source="created", page=0)


@router.message(StateFilter(EventView.choosing_category), lambda m: m.text == "📦 Архивные")
async def handle_archive_events(message: Message, state: FSMContext):
    await show_event_list(message, state, source="archive", page=0)


@router.callback_query(StateFilter(EventView.viewing_events), lambda c: c.data and c.data.startswith("event:"))
async def handle_show_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = callback.message
    if not callback.data or msg is None or not isinstance(msg, Message):
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    _, event_id, source, page = parts

    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    event = await event_service.get_event_by_id(int(event_id))
    await conn.close()

    if not event:
        await msg.answer("Событие не найдено.")
        return

    price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"
    caption = (
        f"<b>{event['title']}</b>\n\n"
        f"<i>{event['description']}</i>"
        # f"📅 {format_event_dates(event['start_date'], event['end_date'])}\n"
        # f"👤 Организатор: {event['organizers']}\n"
        # f"💰 Стоимость: {price}"
    )

    try:
        await msg.delete()
    except Exception:
        pass

    photos = event.get("photos") or []
    if photos:
        media = [InputMediaPhoto(media=photos[0], caption=caption, parse_mode="HTML")]
        media.extend([InputMediaPhoto(media=photo) for photo in photos[1:]])
        await msg.answer_media_group(
            cast(
                list[MediaType],  # aiogram ожидает list[MediaType]
                media
            )
        )
    else:
        await msg.answer(caption, parse_mode="HTML")

    videos = event.get("videos") or []
    for video in videos:
        await msg.answer_video(video)

    from_user = callback.from_user
    user_id = from_user.id if from_user else None

    
    await msg.answer(
        # f"📅 {format_event_dates(event['start_date'], event['end_date'])}\n"
        # f"👤 Организатор: {event['organizers']}\n"
        # f"💰 Стоимость: {price}",  # невидимый символ, не выводится пользователю
        f"{format_event_dates(event['start_date'], event['end_date'])} • {price} • {event['organizers']}\n",
        
        reply_markup=manage_event_reply_keyboard()
    )
    await msg.answer(
        "Редактировать событие:",
        reply_markup=manage_event_keyboard(event, user_id, source, page)
    )

    await state.set_state(EventView.viewing_events)
    await state.update_data(event_id=event['id'], source=source, page=page)

# --- Хендлеры для reply-кнопок ---
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

    event_service = EventService(conn)
    await event_service.invite_all_users(event_id=int(event_id), inviter_user_id=user_id, conn=conn)
    await conn.close()
    await message.answer("✅ Приглашения отправлены всем пользователям!")


@router.message(lambda m: m.text == "⬅️ Назад")
async def handle_back(message: Message, state: FSMContext):
    # Вернуть к списку активных событий, например
    await message.answer("Возвращаю к списку событий...", reply_markup=ReplyKeyboardRemove())
    await show_event_list(message, state, source="active", page=0)

@router.message(StateFilter(EventView.viewing_events), lambda m: m.text == "🗑 Удалить")
async def handle_delete_event_reply(message: Message, state: FSMContext):
    print("Удалить нажато!")
    print("STATE:", await state.get_state())

    data = await state.get_data()
    event_id = data.get("event_id")
    if not event_id:
        await message.answer("Не удалось определить событие для удаления.")
        return
    await state.update_data(pending_delete_id=event_id)
    await message.answer(
        "Вы уверены, что хотите удалить это событие?\nВосстановить будет невозможно!",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

@router.message(lambda m: m.text == "✅ Да")
async def confirm_delete_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("pending_delete_id")
    if not event_id:
        await message.answer("Не удалось определить событие для удаления.")
        return
    # Удаляем из БД
    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    await event_service.delete_event_by_id(int(event_id))
    await conn.close()
    await message.answer("Событие удалено!\nВосстановить его уже нельзя.", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    # Возвращаем меню "Мои события"
    await state.set_state(EventView.choosing_category)
    from bot.handlers.events.navigation import show_my_events_menu
    await show_my_events_menu(message, state)

from bot.handlers.events.view import handle_show_event

@router.message(lambda m: m.text == "❌ Нет")
async def cancel_delete_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    await message.answer("Удаление отменено.")

    # Создаём фейковый callback, чтобы использовать handle_show_event повторно
    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
        async def answer(self, *args, **kwargs): return None

    fake_callback = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )
    await handle_show_event(fake_callback, state)

