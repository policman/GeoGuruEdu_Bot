from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import asyncpg
from bot.config import DATABASE_URL
from bot.database.user_repo import get_user_by_telegram_id
from datetime import date

router = Router()

@router.message(F.text == "📊 Прогресс")
async def show_test_progress(message: Message, state: FSMContext):
    await state.clear()

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

    # --- Результаты тестов ---
    test_results = await conn.fetch("""
        SELECT t.title, tr.correct_answers, tr.total_questions, tr.taken_at
        FROM test_results tr
        JOIN tests t ON tr.test_id = t.id
        WHERE tr.user_id = $1
        ORDER BY tr.taken_at DESC
    """, user_id)

    # --- Создано событий ---
    created_events = await conn.fetchval("""
        SELECT COUNT(*) FROM events WHERE author_id = $1
    """, user_id)

    # --- Активные события (start_date > сегодня) ---
    active_events = await conn.fetchval("""
        SELECT COUNT(*) FROM events e
        LEFT JOIN event_participants ep ON ep.event_id = e.id
        WHERE e.start_date > CURRENT_DATE AND (e.author_id = $1 OR ep.user_id = $1)
    """, user_id)

    # --- Посещённые события (start_date <= сегодня) ---
    visited_events = await conn.fetchval("""
        SELECT COUNT(*) FROM events e
        LEFT JOIN event_participants ep ON ep.event_id = e.id
        WHERE e.start_date <= CURRENT_DATE AND (e.author_id = $1 OR ep.user_id = $1)
    """, user_id)

    # --- Избранные материалы ---
    favorite_materials = await conn.fetchval("""
        SELECT COUNT(*) FROM favorite_materials WHERE user_id = $1
    """, user.id)


    await conn.close()

    # --- Формируем текст ответа ---
    lines = ["📊 <b>Ваш прогресс:</b>\n"]

    if test_results:
        lines.append("🧪 <b>Тесты:</b>")
        for r in test_results:
            date_str = r["taken_at"].strftime("%d.%m.%Y %H:%M")
            score = f"{r['correct_answers']} из {r['total_questions']}"
            lines.append(f"— <b>{r['title']}</b> ({date_str}): {score}")
    else:
        lines.append("🧪 Тесты: пока нет прохождений.")

    lines.append("\n🎯 <b>События:</b>")
    lines.append(f"— Активных событий: {active_events}")
    lines.append(f"— Посещено событий: {visited_events}")
    lines.append(f"— Создано событий: {created_events}")

    lines.append("\n📚 <b>Материалы:</b>")
    lines.append(f"— Избранных материалов: {favorite_materials}")

    await message.answer("\n".join(lines), parse_mode="HTML")
