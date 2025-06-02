from aiogram import Router
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from typing import Union, Optional
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
from aiogram.types import InputMediaPhoto
from datetime import date
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

router = Router()


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

    await message.answer(
        title,
        reply_markup=events_list_keyboard(events, page, source, db_user["id"])
    )


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

    _, event_id_str, source, page_str = callback.data.split(":")
    event_id = int(event_id_str)
    page = int(page_str)

    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    event = await event_service.get_event_by_id(event_id)
    db_user = await get_user_by_telegram_id(conn, callback.from_user.id)

    # ------------------------------------------
    # 1) Сразу обрабатываем «Архивные»: только фото/текст и кнопка «⬅️ Назад»
    if source == "archive":
        # Если событие не найдено, сразу закрываем соединение и выходим
        if not event:
            await conn.close()
            await msg.answer("Событие не найдено.")
            return

        # Закрываем соединение БД перед отправкой любых сообщений
        await conn.close()

        # Убедимся, что bot и msg.chat не None
        bot = callback.bot
        assert bot is not None
        assert msg.chat is not None

        # Отправляем фото + заголовок/описание
        full_caption = f"<b>{event['title']}</b>\n\n<i>{event['description']}</i>"
        if event.get("photo"):
            await bot.send_photo(
                chat_id=msg.chat.id,
                photo=event["photo"],
                caption=full_caption,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=msg.chat.id,
                text=full_caption,
                parse_mode="HTML"
            )

        # Затем детали: дата, цена, организатор
        price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"
        details_text = (
            f"📅 Дата: {format_event_dates(event['start_date'], event['end_date'])}\n"
            f"💰 Цена: {price}\n"
            f"👤 Организатор: {event['organizers']}"
        )

        # Reply-кнопка «⬅️ Назад»
        kb_back_only = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="⬅️ Назад")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await bot.send_message(
            chat_id=msg.chat.id,
            text=details_text,
            reply_markup=kb_back_only
        )

        # Остаёмся в том же состоянии и выходим
        await state.set_state(EventView.viewing_events)
        await state.update_data(event_id=event_id, source=source, page=page)
        return
    # ------------------------------------------

    # Если не архив, продолжаем предыдущую логику:
    if not event:
        await conn.close()
        await msg.answer("Событие не найдено.")
        return
    assert event is not None

    if not db_user:
        await conn.close()
        await msg.answer("❌ Пользователь не найден в системе.")
        return
    assert db_user is not None

    await state.update_data(event_id=event_id, source=source, page=page)

    try:
        await msg.delete()
    except Exception:
        pass

    bot = callback.bot
    assert bot is not None

    # === 1. Если пользователь — автор события ===
    user_id = db_user["id"]
    author_id = event["author_id"]
    if user_id == author_id:
        # Общие детали (текст без карточки)
        price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"
        full_caption = f"<b>{event['title']}</b>\n\n<i>{event['description']}</i>"
        photo = event.get("photo")
        if photo:
            await bot.send_photo(
                chat_id=msg.chat.id,
                photo=photo,
                caption=full_caption,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=msg.chat.id,
                text=full_caption,
                parse_mode="HTML"
            )

        details_text = (
            f"📅 Дата: {format_event_dates(event['start_date'], event['end_date'])}\n\n"
            f"💰 Цена: {price}\n\n"
            f"👤 Организатор: {event['organizers']}"
        )
        # Reply-кнопки «Разослать приглашения / Участники / Удалить / Назад»
        await bot.send_message(
            chat_id=msg.chat.id,
            text=details_text,
            reply_markup=manage_event_reply_keyboard()
        )
        # Inline-кнопка «Редактировать»
        await bot.send_message(
            chat_id=msg.chat.id,
            text="Редактировать событие:",
            reply_markup=manage_event_keyboard(event, user_id, source, page)
        )

    # === 2. Если пользователь — участник (но не автор) ===
    else:
        # Проверяем, действительно ли он участник
        conn = await asyncpg.connect(DATABASE_URL)
        is_participant_row = await conn.fetchrow(
            """
            SELECT 1
            FROM event_participants
            WHERE event_id = $1 AND user_id = $2
            """,
            event_id, user_id
        )
        participant_counts = await event_service.get_participant_counts()
        participant_counts = await event_service.get_participant_counts()
        await conn.close()

        is_participant = bool(is_participant_row)
        if is_participant:
            # Формируем карточку в стиле списка событий
            price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"
            caption = (
                f"<b>{event['title']}</b>\n"
                f"<i>{event['description']}</i>\n\n"
                f"📅 {format_event_dates(event['start_date'], event['end_date'])}\n"
                f"👤 Организатор: {event['organizers']}\n"
                f"💰 Стоимость: {price}"
            )
            count = participant_counts.get(event_id, 0)
            caption += f"\n👥 Участников: {count}"
            caption += "\n\n✅ Вы участвуете"

            # Reply-кнопки «Написать организатору / Ответы организатора / Назад»
            kb_participant = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Написать организатору")],
                    [KeyboardButton(text="Ответы организатора")],
                    [KeyboardButton(text="⬅️ Назад")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )

            photo = event.get("photo")
            if photo:
                await bot.send_photo(
                    chat_id=msg.chat.id,
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=kb_participant
                )
            else:
                await bot.send_message(
                    chat_id=msg.chat.id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=kb_participant
                )
        else:
            # === 3. Остальные пользователи (не автор и не участник) ===
            price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"
            full_caption = f"<b>{event['title']}</b>\n\n<i>{event['description']}</i>"
            photo = event.get("photo")
            if photo:
                await bot.send_photo(
                    chat_id=msg.chat.id,
                    photo=photo,
                    caption=full_caption,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=msg.chat.id,
                    text=full_caption,
                    parse_mode="HTML"
                )

            details_text = (
                f"📅 Дата: {format_event_dates(event['start_date'], event['end_date'])}\n"
                f"💰 Цена: {price}\n"
                f"👤 Организатор: {event['organizers']}"
            )
            kb_back_only = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="⬅️ Назад")]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            await bot.send_message(
                chat_id=msg.chat.id,
                text=details_text,
                reply_markup=kb_back_only
            )

    # Остаёмся в том же состоянии
    await state.set_state(EventView.viewing_events)
    await state.update_data(event_id=event_id, source=source, page=page)




@router.message(lambda m: m.text == "⬅️ Назад")
async def handle_back(message: Message, state: FSMContext):
    """Возвращаем пользователя к списку событий (активных по умолчанию)."""
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

@router.callback_query(StateFilter(EventView.viewing_events), lambda c: c.data and c.data.startswith("page:"))
async def handle_pagination(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    msg = callback.message
    if not callback.data or msg is None:
        return

    try:
        _, source, page = callback.data.split(":")
        page = int(page)
    except ValueError:
        await msg.answer("Ошибка навигации.")  # type: ignore
        return

    await show_event_list(callback, state, source=source, page=page)