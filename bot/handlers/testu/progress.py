# # ✅ Файл: bot/handlers/testu/progress.py

# from aiogram import Router, F
# from aiogram.types import Message
# import asyncpg
# from bot.config import DATABASE_URL

# progress_router = Router()

# @progress_router.message(F.text == "📊 Прогресс")
# async def show_progress(message: Message):
#     telegram_id = message.from_user.id

#     conn = await asyncpg.connect(DATABASE_URL)
#     user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)

#     if not user_row:
#         await conn.close()
#         await message.answer("❌ Вы не зарегистрированы в системе.")
#         return

#     results = await conn.fetch(
#         """
#         SELECT t.title, r.correct_answers, r.total_questions
#         FROM test_results r
#         JOIN tests t ON r.test_id = t.id
#         WHERE r.user_id = $1
#         ORDER BY r.id DESC
#         LIMIT 10
#         """,
#         user_row["id"]
#     )
#     await conn.close()

#     if not results:
#         await message.answer("📭 У вас ещё нет пройденных тестов.")
#         return

#     text = "<b>📊 Ваш прогресс:</b>\n\n"
#     for row in results:
#         text += f"🧪 <b>{row['title']}</b> — {row['correct_answers']} / {row['total_questions']}\n"

#     await message.answer(text, parse_mode="HTML")