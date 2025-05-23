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

from bot.states.event_states import EventView
from bot.services.event_service import EventService
from bot.database.user_repo import get_user_by_telegram_id
from bot.keyboards.events import events_list_keyboard
from bot.keyboards.events.manage_event import (
    manage_event_keyboard, 
    manage_event_reply_keyboard
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
        await message.answer("Событий не найдено.", reply_markup=ReplyKeyboardRemove())
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
        f"📌 <b>{event['title']}</b>\n\n"
        f"{event['description']}\n\n"
        f"📅 {format_event_dates(event['start_date'], event['end_date'])}\n"
        f"👤 Организатор: {event['organizers']}\n"
        f"💰 Стоимость: {price}"
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

    # Получаем user_id для проверки "свой/чужой"
    from_user = callback.from_user
    user_id = from_user.id if from_user else None

    # Инлайн-кнопка "✏️ Редактировать" (если доступна)
    inline_keyboard = manage_event_keyboard(event, user_id, source, page)
    if inline_keyboard and inline_keyboard.inline_keyboard:
        await msg.answer(
            "Вы можете редактировать событие 🔽",
            reply_markup=inline_keyboard
        )
    else:
        await msg.answer(f"Редактирование недоступно")

    # После этого — обычная reply-клавиатура с действиями
    await msg.answer(
        "Выберите действие:",
        reply_markup=manage_event_reply_keyboard()
    )
    # ... после показа всех сообщений:
    await state.update_data(event_id=event['id'], source=source, page=page)



# --- Хендлеры для reply-кнопок ---
@router.message(lambda m: m.text == "📨 Разослать приглашения")
async def handle_invite(message: Message, state: FSMContext):
    await message.answer("Возможность рассылки приглашений появится скоро!")



@router.message(lambda m: m.text == "⬅️ Назад")
async def handle_back(message: Message, state: FSMContext):
    # Вернуть к списку активных событий, например
    await message.answer("Возвращаю к списку событий...", reply_markup=ReplyKeyboardRemove())
    await show_event_list(message, state, source="active", page=0)


@router.message(lambda m: m.text == "🗑 Удалить")
async def handle_delete_event_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)
    if not event_id:
        await message.answer("Не удалось определить событие для удаления.")
        return
    # Сохраняем pending_delete_id для подтверждения
    await state.update_data(pending_delete_id=event_id, source=source, page=page)
    await message.answer(
        "Вы уверены, что хотите удалить это событие?",
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
    source = data.get("source", "active")
    page = data.get("page", 0)
    if not event_id:
        await message.answer("Не удалось определить событие для удаления.")
        return
    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    await event_service.delete_event_by_id(int(event_id))
    await conn.close()
    await message.answer("Событие удалено!", reply_markup=ReplyKeyboardRemove())
    await state.clear()
    # Возвращаем к списку событий (можно поменять source)
    await show_event_list(message, state, source=source, page=int(page))

@router.message(lambda m: m.text == "❌ Нет")
async def cancel_delete_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)
    await message.answer("Удаление отменено.", reply_markup=manage_event_reply_keyboard())
    # Можно вернуть пользователя обратно к действиям с этим событием или оставить просто клаву

