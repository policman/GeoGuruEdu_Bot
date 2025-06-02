from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import asyncpg
from datetime import datetime

from bot.config import DATABASE_URL
from bot.states.event_states import InvitationStates
from bot.keyboards.events.manage_event import (
    invite_method_keyboard,
    invite_confirm_keyboard,
)
from bot.handlers.events.view import handle_show_event

router = Router()


# 1) Нажатие «📨 Разослать приглашения» → показываем меню выбора метода
@router.message(lambda m: m.text == "📨 Разослать приглашения")
async def choose_invite_method(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    if not event_id:
        await message.answer("Ошибка: событие не выбрано.", reply_markup=ReplyKeyboardRemove())
        return

    await state.set_state(InvitationStates.CHOOSING_METHOD)
    await message.answer(
        "Выберите способ рассылки приглашений:",
        reply_markup=invite_method_keyboard()
    )


# 2) Обработка «⬅️ Назад к событию» в любом субсостоянии
@router.message(F.text == "⬅️ Назад к событию")
async def cancel_back_to_event(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Возвращаем к событию …", reply_markup=ReplyKeyboardRemove())

    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None


    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )
    await handle_show_event(fake, state)



# ──────────────────────────────────────────────────────────────────────────────
# 3) «📑 По отделам/профилю» → ввод отделов
@router.message(StateFilter(InvitationStates.CHOOSING_METHOD), F.text == "📑 По отделам/профилю")
async def invite_by_depts_profiles(message: Message, state: FSMContext):
    await state.set_state(InvitationStates.ENTER_DEPARTMENTS)
    # Клавиатура: только «Пропустить»
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Введите отделы через запятую (например: Отдел1, Отдел2) или нажмите «Пропустить»:",
        reply_markup=kb
    )

@router.message(StateFilter(InvitationStates.ENTER_DEPARTMENTS))
async def enter_departments(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    # Если пользователь нажал «Пропустить»
    if text.lower() == "пропустить":
        await state.update_data(departments=[])
    else:
        depts = [d.strip() for d in text.split(",") if d.strip()]
        await state.update_data(departments=depts)

    # Переход к вводу профилей
    await state.set_state(InvitationStates.ENTER_PROFILES)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Теперь введите профессии (профили) через запятую или нажмите «Пропустить»:",
        reply_markup=kb
    )


@router.message(StateFilter(InvitationStates.ENTER_PROFILES))
async def enter_profiles(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    # Если пользователь нажал «Пропустить», сохраняем пустой список профилей
    if text.lower() == "пропустить":
        await state.update_data(profiles=[])
    else:
        profs = [p.strip() for p in text.split(",") if p.strip()]
        await state.update_data(profiles=profs)

    data = await state.get_data()
    depts = data.get("departments", [])
    profs = data.get("profiles", [])
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    # Если и отделы, и профили не указаны → сразу возвращаем к событию
    if not depts and not profs:
        await state.clear()
        # Возвращаемся к экрану события через FakeCallback
        class FakeCallback:
            def __init__(self, message, data, from_user):
                self.message = message
                self.data = data
                self.from_user = from_user
                self.bot = message.bot

            async def answer(self, *args, **kwargs):
                return None

        fake = FakeCallback(
            message=message,
            data=f"event:{event_id}:{source}:{page}",
            from_user=message.from_user
        )
        await handle_show_event(fake, state)
        return

    # Иначе — показываем сводку и клавиатуру «✅ Разослать / ❌ Отмена»
    summary = (
        f"Будут отправлены приглашения пользователям из отделов:\n"
        f"{', '.join(depts) if depts else '(не указан)'}\n\n"
        f"и профессиям:\n{', '.join(profs) if profs else '(не указаны)'}"
    )
    await state.set_state(InvitationStates.CONFIRM_DEPTS_PROFS)
    await message.answer(
        summary + "\n\nПодтвердить рассылку?",
        reply_markup=invite_confirm_keyboard()
    )



@router.message(StateFilter(InvitationStates.CONFIRM_DEPTS_PROFS), F.text == "✅ Разослать")
async def send_by_depts_profiles(message: Message, state: FSMContext):
    data = await state.get_data()
    depts = data.get("departments", [])
    profs = data.get("profiles", [])
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить автора.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_telegram = user.id
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        inviter_telegram
    )
    if not row:
        await conn.close()
        await message.answer("Автор события не найден в системе.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_user_id = row["id"]

    # Если списки пусты — условие `ANY([])` вернёт false, но мы хотим допустить
    # рассылку «без фильтра по отделам» или «без фильтра по профилям».
    # Поэтому строим WHERE так, что если списки пусты, эту часть пропускаем:
    where_clauses = []
    params = []
    idx = 1

    if depts:
        where_clauses.append(f"department = ANY(${idx}::TEXT[])")
        params.append(depts)
        idx += 1

    if profs:
        where_clauses.append(f"position = ANY(${idx}::TEXT[])")
        params.append(profs)
        idx += 1

    # Добавляем условие «не автор»
    where_clauses.append(f"id != ${idx}")
    params.append(inviter_user_id)
    idx += 1

    where_sql = " OR ".join(where_clauses) if where_clauses else f"id != ${idx-1}"

    sql = f"SELECT telegram_id FROM users WHERE {where_sql}"
    rows = await conn.fetch(sql, *params)

    invited = 0
    bot = message.bot
    for record in rows:
        tgid = record.get("telegram_id")
        if bot is None or tgid is None:
            continue
        try:
            await bot.send_message(
                chat_id=tgid,
                text=f"📣 Приглашение на событие (ID {event_id})"
            )
            invited += 1
        except Exception:
            pass

    await conn.close()

    await message.answer(
        f"✅ Приглашения отправлены ({invited} чел.).",
        reply_markup=ReplyKeyboardRemove()
    )

    # Возвращаем меню события
    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None

    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)


@router.message(StateFilter(InvitationStates.CONFIRM_DEPTS_PROFS), F.text == "❌ Отмена")
async def cancel_by_depts_profiles(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    await message.answer("Рассылка отменена.", reply_markup=ReplyKeyboardRemove())

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None

    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)



# 4) «👥 Всем сотрудникам»
@router.message(StateFilter(InvitationStates.CHOOSING_METHOD), F.text == "👥 Всем сотрудникам")
async def invite_colleagues(message: Message, state: FSMContext):
    await state.set_state(InvitationStates.CONFIRM_COLLEAGUES)
    await message.answer(
        "Будут отправлены приглашения всем пользователям с тем же \"Местом работы\", что у вас.\nПодтвердить?",
        reply_markup=invite_confirm_keyboard()
    )

@router.message(StateFilter(InvitationStates.CONFIRM_COLLEAGUES), F.text == "✅ Разослать")
async def send_to_colleagues(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить автора.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_telegram = user.id
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "SELECT id, place_of_work FROM users WHERE telegram_id = $1",
        inviter_telegram
    )
    if not row:
        await conn.close()
        await message.answer("Автор события не найден.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_user_id = row["id"]
    place = row.get("place_of_work")
    if place is None:
        await conn.close()
        await message.answer("У автора не заполнено «Место работы».", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    rows = await conn.fetch(
        "SELECT telegram_id FROM users WHERE place_of_work = $1 AND id != $2",
        place, inviter_user_id
    )

    invited = 0
    bot = message.bot
    for record in rows:
        tgid = record.get("telegram_id")
        if bot is None or tgid is None:
            continue
        try:
            await bot.send_message(
                chat_id=tgid,
                text=f"📣 Приглашение на событие (ID {event_id})"
            )
            invited += 1
        except Exception:
            pass

    await conn.close()

    await message.answer(
        f"✅ Приглашения отправлены коллегам ({invited} чел.).",
        reply_markup=ReplyKeyboardRemove()
    )

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None


    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)


@router.message(StateFilter(InvitationStates.CONFIRM_COLLEAGUES), F.text == "❌ Отмена")
async def cancel_colleagues(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    await message.answer("Рассылка отменена.", reply_markup=ReplyKeyboardRemove())

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None


    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)



# 5) «🌐 Всем»
@router.message(StateFilter(InvitationStates.CHOOSING_METHOD), F.text == "🌐 Всем")
async def invite_all_opt_in(message: Message, state: FSMContext):
    await state.set_state(InvitationStates.CONFIRM_ALL)
    await message.answer(
        "Будут отправлены приглашения всем пользователям, у кого «Открыт к предложениям» = True.\nПодтвердить?",
        reply_markup=invite_confirm_keyboard()
    )

@router.message(StateFilter(InvitationStates.CONFIRM_ALL), F.text == "✅ Разослать")
async def send_to_all(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить автора.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_telegram = user.id
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        inviter_telegram
    )
    if not row:
        await conn.close()
        await message.answer("Автор события не найден.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    inviter_id = row["id"]
    rows = await conn.fetch(
        "SELECT telegram_id FROM users WHERE open_to_offers = TRUE AND id != $1",
        inviter_id
    )

    invited = 0
    bot = message.bot
    for record in rows:
        tgid = record.get("telegram_id")
        if bot is None or tgid is None:
            continue
        try:
            await bot.send_message(
                chat_id=tgid,
                text=f"📣 Приглашение на событие (ID {event_id})"
            )
            invited += 1
        except Exception:
            pass

    await conn.close()

    await message.answer(
        f"✅ Приглашения отправлены ({invited} чел.).",
        reply_markup=ReplyKeyboardRemove()
    )

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None


    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)


@router.message(StateFilter(InvitationStates.CONFIRM_ALL), F.text == "❌ Отмена")
async def cancel_send_all(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("event_id")
    source = data.get("source", "active")
    page = data.get("page", 0)

    await message.answer("Рассылка отменена.", reply_markup=ReplyKeyboardRemove())

    class FakeCallback:
        def __init__(self, message, data, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user
            self.bot = message.bot

        async def answer(self, *args, **kwargs):
            return None


    fake = FakeCallback(
        message=message,
        data=f"event:{event_id}:{source}:{page}",
        from_user=message.from_user
    )

    await state.clear()
    await handle_show_event(fake, state)
