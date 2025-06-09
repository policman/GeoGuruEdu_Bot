from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import asyncpg
from bot.config import DATABASE_URL
from bot.services.test_service import TestService
from bot.database.user_repo import get_user_by_telegram_id
from bot.keyboards.learning.menu import testing_menu_keyboard

router = Router()

@router.message(F.text == "Пригласить в тест")
async def invite_to_test_menu(message: Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="По отделам"), KeyboardButton(text="По профессиям")],
            [KeyboardButton(text="⬅️ Назад к тестам")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Выберите способ приглашения:", reply_markup=kb)


@router.message(F.text == "⬅️ Назад к тестам")
async def back_to_testing_menu(message: Message, state: FSMContext):
    await message.answer("🧪 Меню тестирования:", reply_markup=testing_menu_keyboard())


@router.message(F.text == "По отделам")
async def invite_by_department(message: Message, state: FSMContext):
    user = message.from_user
    if not user:
        await message.answer("❌ Не удалось определить пользователя.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await get_user_by_telegram_id(conn, user.id)
    if not user_row:
        await conn.close()
        await message.answer("❌ Вы не зарегистрированы.")
        return

    tests = await conn.fetch("""
        SELECT id, title FROM tests WHERE created_by = $1
        ORDER BY created_at DESC
    """, user_row["id"])

    await conn.close()

    if not tests:
        await message.answer("❗ У вас пока нет созданных тестов.")
        return

    await state.update_data(tests=tests, creator_id=user_row["id"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=test["title"], callback_data=f"select_test_dep:{test['id']}")]
        for test in tests
    ])
    await message.answer("Выберите тест для приглашения по отделам:", reply_markup=kb)


@router.message(F.text == "По профессиям")
async def invite_by_profession_start(message: Message, state: FSMContext):
    user = message.from_user
    if not user:
        await message.answer("❌ Не удалось определить пользователя.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await get_user_by_telegram_id(conn, user.id)
    if not user_row:
        await conn.close()
        await message.answer("❌ Вы не зарегистрированы.")
        return

    tests = await conn.fetch("""
        SELECT id, title FROM tests WHERE created_by = $1
        ORDER BY created_at DESC
    """, user_row["id"])
    await conn.close()

    if not tests:
        await message.answer("❗ У вас пока нет созданных тестов.")
        return

    await state.update_data(creator_id=user_row["id"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=test["title"], callback_data=f"select_test_prof:{test['id']}")]
        for test in tests
    ])
    await message.answer("Выберите тест, для которого хотите пригласить по профессиям:", reply_markup=kb)


@router.callback_query(F.data.startswith("select_test_prof:"))
async def select_test_for_professions(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await state.update_data(selected_test_id=test_id)

    conn = await asyncpg.connect(DATABASE_URL)
    professions = await conn.fetch("""
        SELECT DISTINCT position FROM users
        WHERE position IS NOT NULL AND position <> ''
        ORDER BY position
    """)
    await conn.close()

    if not professions:
        await callback.message.answer("❌ Не найдено профессий.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=prof["position"], callback_data=f"invite_prof:{prof['position']}")]
        for prof in professions
    ])
    await callback.message.answer("Выберите профессию для приглашения:", reply_markup=kb)


@router.callback_query(F.data.startswith("invite_prof:"))
async def invite_by_profession_selected(callback: CallbackQuery, state: FSMContext):
    profession = callback.data.split(":", maxsplit=1)[1]
    state_data = await state.get_data()
    test_id = state_data.get("selected_test_id")
    creator_id = state_data.get("creator_id")

    if not test_id:
        await callback.message.answer("⚠️ Тест не выбран.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("""
        SELECT id FROM users WHERE position = $1 AND id != $2
    """, profession, creator_id)

    invited_count = 0
    for u in users:
        exists = await conn.fetchval("""
            SELECT 1 FROM test_invitations WHERE user_id = $1 AND test_id = $2
        """, u["id"], test_id)
        if not exists:
            await conn.execute("""
                INSERT INTO test_invitations (user_id, test_id, invited_at)
                VALUES ($1, $2, now())
            """, u["id"], test_id)
            invited_count += 1

    await conn.close()
    await callback.message.answer(
        f"✅ Приглашения отправлены ({invited_count}) сотрудникам с профессией: <b>{profession}</b>.", parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("select_test_dep:"))
async def select_test_for_departments(callback: CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split(":")[1])
    await state.update_data(selected_test_id=test_id)

    conn = await asyncpg.connect(DATABASE_URL)
    departments = await conn.fetch("""
        SELECT DISTINCT department FROM users
        WHERE department IS NOT NULL AND department <> ''
        ORDER BY department
    """)
    await conn.close()

    if not departments:
        await callback.message.answer("❌ Не найдено отделов.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=dep["department"], callback_data=f"invite_dep:{dep['department']}")]
        for dep in departments
    ])
    await callback.message.answer("Выберите отдел для приглашения:", reply_markup=kb)


@router.callback_query(F.data.startswith("invite_dep:"))
async def invite_by_department_selected(callback: CallbackQuery, state: FSMContext):
    department = callback.data.split(":")[1]
    state_data = await state.get_data()
    test_id = state_data.get("selected_test_id")
    creator_id = state_data.get("creator_id")

    if not test_id:
        await callback.message.answer("⚠️ Тест не выбран.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    users = await conn.fetch("""
        SELECT id FROM users WHERE department = $1 AND id != $2
    """, department, creator_id)

    invited_count = 0
    for u in users:
        exists = await conn.fetchval("""
            SELECT 1 FROM test_invitations WHERE user_id = $1 AND test_id = $2
        """, u["id"], test_id)
        if not exists:
            await conn.execute("""
                INSERT INTO test_invitations (user_id, test_id, invited_at)
                VALUES ($1, $2, now())
            """, u["id"], test_id)
            invited_count += 1

    await conn.close()
    await callback.message.answer(
        f"✅ Приглашения отправлены ({invited_count}) сотрудникам отдела: <b>{department}</b>.", parse_mode="HTML"
    )


@router.message(F.text == "Приглашения на тест")
async def show_test_invitations(message: Message, state: FSMContext):
    user = message.from_user
    if not user:
        await message.answer("❌ Не удалось определить пользователя.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await get_user_by_telegram_id(conn, user.id)
    if not user_row:
        await conn.close()
        await message.answer("❌ Вы не зарегистрированы в системе.")
        return

    user_id = user_row["id"]

    invitations = await conn.fetch("""
        SELECT ti.id as invitation_id, ti.test_id, t.title
        FROM test_invitations ti
        JOIN tests t ON ti.test_id = t.id
        WHERE ti.user_id = $1 AND NOT ti.accepted AND NOT ti.declined
        ORDER BY ti.invited_at DESC
    """, user_id)

    await conn.close()

    if not invitations:
        await message.answer("📭 У вас нет новых приглашений на тесты.")
        return

    for inv in invitations:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_inv:{inv['invitation_id']}:{inv['test_id']}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_inv:{inv['invitation_id']}")
            ]
        ])
        await message.answer(
            f"📨 Приглашение на тест:\n<b>{inv['title']}</b>", parse_mode="HTML", reply_markup=kb
        )


@router.callback_query(F.data.startswith("accept_inv:"))
async def accept_invitation(callback: CallbackQuery, state: FSMContext):
    _, invitation_id, test_id = callback.data.split(":")

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE test_invitations SET accepted = TRUE WHERE id = $1", int(invitation_id))
    await conn.close()

    await callback.message.edit_reply_markup()
    await callback.message.answer("✅ Приглашение принято. Вы можете пройти тест в разделе 'Пройти тест'.")


@router.callback_query(F.data.startswith("decline_inv:"))
async def decline_invitation(callback: CallbackQuery, state: FSMContext):
    invitation_id = int(callback.data.split(":")[1])

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE test_invitations SET declined = TRUE WHERE id = $1", invitation_id)
    await conn.close()

    await callback.message.edit_reply_markup()
    await callback.message.answer("❌ Приглашение отклонено.")
