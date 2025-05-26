from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncpg
import os
from dotenv import load_dotenv
from aiogram.fsm.state import StatesGroup, State

from bot.services.event_service import EventService

router = Router()
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- FSM states ---

class EventEdit(StatesGroup):
    choosing_field = State()
    editing_title = State()
    editing_description = State()
    editing_start_date = State()
    editing_end_date = State()
    editing_organizers = State()
    editing_price = State()
    editing_photos = State()
    editing_videos = State()


# --- Клавиатура выбора поля ---
def edit_event_fields_keyboard(event_id, source, page):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Название", callback_data=f"editfield:title:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Описание", callback_data=f"editfield:description:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Дата начала", callback_data=f"editfield:start_date:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Дата окончания", callback_data=f"editfield:end_date:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Организатор", callback_data=f"editfield:organizers:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Стоимость", callback_data=f"editfield:price:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Фото", callback_data=f"editfield:photos:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="Видео", callback_data=f"editfield:videos:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="✅ Сохранить и выйти", callback_data=f"editfield:save:{event_id}:{source}:{page}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"editfield:cancel:{event_id}:{source}:{page}")]
    ])

# --- Удаление события ---
@router.callback_query(F.data.startswith("delete_event:"))
async def handle_delete_event(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    _, event_id, source, page = callback.data.split(":")
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Вы уверены, что хотите удалить это событие?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Да",
                            callback_data=f"confirm_delete_event:{event_id}:{source}:{page}"
                        ),
                        InlineKeyboardButton(
                            text="❌ Нет",
                            callback_data=f"event:{event_id}:{source}:{page}"
                        )
                    ]
                ]
            )
        )
    else:
        await callback.answer("Не удалось отредактировать сообщение.")

@router.callback_query(F.data.startswith("confirm_delete_event:"))
async def handle_confirm_delete_event(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    _, event_id, source, page = callback.data.split(":")
    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    await event_service.delete_event_by_id(int(event_id))
    await conn.close()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text("Событие успешно удалено.")
    else:
        await callback.answer("Событие успешно удалено.")

# --- Начало редактирования ---
@router.callback_query(F.data.startswith("edit_event:"))
async def handle_edit_event(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        await callback.answer("Некорректные данные.", show_alert=True)
        return

    _, event_id, source, page = callback.data.split(":")

    # ===== ПРОВЕРКА: только автор может редактировать =====
    # Получаем id текущего пользователя (telegram_id → user.id)
    telegram_id = callback.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if not user_row:
        await conn.close()
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    user_db_id = user_row['id']

    # Получаем creator_id из events
    event = await conn.fetchrow("SELECT creator_id FROM events WHERE id = $1", int(event_id))
    await conn.close()
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    creator_id = event['creator_id']

    if creator_id != user_db_id:
        await callback.answer("Редактировать может только создатель события.", show_alert=True)
        return
    # ======= /ПРОВЕРКА =======

    await state.update_data(event_id=event_id, source=source, page=page, fields={})
    await state.set_state(EventEdit.choosing_field)
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Что вы хотите изменить?",
            reply_markup=edit_event_fields_keyboard(event_id, source, page)
        )
    else:
        await callback.answer("Ошибка: не удалось отредактировать сообщение.", show_alert=True)


@router.callback_query(EventEdit.choosing_field, F.data.startswith("editfield:"))
async def handle_choose_field(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    _, field, event_id, source, page = callback.data.split(":")
    if field == "save":
        data = await state.get_data()
        fields = data.get("fields", {})
        conn = await asyncpg.connect(DATABASE_URL)
        event_service = EventService(conn)
        if fields:
            await event_service.update_event_fields(int(event_id), **fields)
        await conn.close()
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("Все изменения сохранены ✅")
        await state.clear()
        # Отобразить обновлённое событие!
        from bot.handlers.events.view import handle_show_event
        # Создаём псевдо-колбэк с такими же данными
        class FakeCallback:
            def __init__(self, message, data, from_user):
                self.message = message
                self.data = data
                self.from_user = from_user
            async def answer(self, *args, **kwargs): return None
        fake_callback = FakeCallback(
            message=callback.message,
            data=f"event:{event_id}:{source}:{page}",
            from_user=callback.from_user
        )
        await handle_show_event(fake_callback, state)
        return
    if field == "cancel":
        if callback.message and isinstance(callback.message, Message):
            await callback.message.edit_text("Редактирование отменено ❌")
        await state.clear()
        return
    prompts = {
    "title": "Введите новое название события:",
    "description": "Введите новое описание события:",
    "start_date": "Введите новую дату начала (ГГГГ-ММ-ДД):",
    "end_date": "Введите новую дату окончания (ГГГГ-ММ-ДД):",
    "organizers": "Введите нового организатора:",
    "price": "Введите новую стоимость (число, 0 = бесплатно):",
    "photos": "Пришлите новое(ые) фото (можно несколько).",
    "videos": "Пришлите новое(ые) видео (можно несколько)."
    }

    await state.update_data(field=field)
    await state.set_state(getattr(EventEdit, f"editing_{field}"))
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(prompts[field])

@router.message(EventEdit.editing_photos)
async def save_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data.get("fields", {})
    if message.photo:
        # Можно добавить сразу несколько file_id
        photo_ids = [p.file_id for p in message.photo]
        fields["photos"] = photo_ids
        await state.update_data(fields=fields)
        await state.set_state(EventEdit.choosing_field)
        await message.answer("Фото обновлено. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))
    else:
        await message.answer("Пришлите фото!")

@router.message(EventEdit.editing_videos)
async def save_videos(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data.get("fields", {})
    if message.video:
        fields["videos"] = [message.video.file_id]
        await state.update_data(fields=fields)
        await state.set_state(EventEdit.choosing_field)
        await message.answer("Видео обновлено. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))
    else:
        await message.answer("Пришлите видео!")

# --- Сохраняем значения каждого поля во временное хранилище FSM (не в БД!) ---
@router.message(EventEdit.editing_title)
async def save_title(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data.get("fields", {})
    fields["title"] = message.text
    await state.update_data(fields=fields)
    await state.set_state(EventEdit.choosing_field)
    await message.answer("Название обновлено. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))

@router.message(EventEdit.editing_description)
async def save_description(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data.get("fields", {})
    fields["description"] = message.text
    await state.update_data(fields=fields)
    await state.set_state(EventEdit.choosing_field)
    await message.answer("Описание обновлено. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))

@router.message(EventEdit.editing_start_date)
async def save_start_date(message: Message, state: FSMContext):
    from datetime import datetime
    try:
        if message.text is None:
            raise ValueError("Дата не может быть пустой")
        start_date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        data = await state.get_data()
        fields = data.get("fields", {})
        fields["start_date"] = start_date
        await state.update_data(fields=fields)
        await state.set_state(EventEdit.choosing_field)
        await message.answer("Дата начала обновлена. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))
    except Exception:
        await message.answer("Некорректная дата! Введите в формате ГГГГ-ММ-ДД:")

@router.message(EventEdit.editing_end_date)
async def save_end_date(message: Message, state: FSMContext):
    from datetime import datetime
    try:
        if message.text is None:
            raise ValueError("Дата не может быть пустой")
        end_date = datetime.strptime(message.text.strip(), "%Y-%m-%d").date()
        data = await state.get_data()
        fields = data.get("fields", {})
        fields["end_date"] = end_date
        await state.update_data(fields=fields)
        await state.set_state(EventEdit.choosing_field)
        await message.answer("Дата окончания обновлена. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))
    except Exception:
        await message.answer("Некорректная дата! Введите в формате ГГГГ-ММ-ДД:")

@router.message(EventEdit.editing_organizers)
async def save_organizer(message: Message, state: FSMContext):
    data = await state.get_data()
    fields = data.get("fields", {})
    fields["organizers"] = message.text
    await state.update_data(fields=fields)
    await state.set_state(EventEdit.choosing_field)
    await message.answer(
        "Организатор обновлён. Что ещё изменить?",
        reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"])
    )


@router.message(EventEdit.editing_price)
async def save_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip()) if message.text else 0
        data = await state.get_data()
        fields = data.get("fields", {})
        fields["price"] = price
        await state.update_data(fields=fields)
        await state.set_state(EventEdit.choosing_field)
        await message.answer("Стоимость обновлена. Что ещё изменить?", reply_markup=edit_event_fields_keyboard(data["event_id"], data["source"], data["page"]))
    except Exception:
        await message.answer("Стоимость должна быть числом! Введите новую стоимость:")

# --- Заглушка на рассылку ---
@router.callback_query(F.data.startswith("invite_event:"))
async def handle_invite_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Возможность рассылки приглашений появится скоро!", show_alert=True)
