# # ✅ Файл: bot/handlers/testu/tests.py

# from aiogram import Router, F
# from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# from aiogram.fsm.state import StatesGroup, State
# from aiogram.fsm.context import FSMContext
# import asyncpg
# from bot.config import DATABASE_URL

# router = Router()

# class TestState(StatesGroup):
#     choosing_test = State()
#     answering = State()

# # -- Клавиатура с выбором теста --
# async def get_test_list_keyboard() -> InlineKeyboardMarkup:
#     conn = await asyncpg.connect(DATABASE_URL)
#     tests = await conn.fetch("SELECT id, title FROM tests")
#     await conn.close()

#     keyboard = [
#         [InlineKeyboardButton(text=test["title"], callback_data=f"start_test:{test['id']}")]
#         for test in tests
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=keyboard)

# # -- Клавиатура с вариантами ответа --
# def get_answer_keyboard(test_id: int, question_id: int, options: list[str]) -> InlineKeyboardMarkup:
#     buttons = [
#         [InlineKeyboardButton(text=opt, callback_data=f"answer:{test_id}:{question_id}:{opt}")]
#         for opt in options
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=buttons)

# @router.message(F.text == "🧪 Тестирование")
# async def show_test_list(message: Message, state: FSMContext):
#     keyboard = await get_test_list_keyboard()
#     await state.clear()
#     await message.answer("📚 Выберите тему теста:", reply_markup=keyboard)

# @router.callback_query(F.data.startswith("start_test:"))
# async def start_test(callback: CallbackQuery, state: FSMContext):
#     if not callback.data:
#         return

#     test_id = int(callback.data.removeprefix("start_test:"))

#     conn = await asyncpg.connect(DATABASE_URL)
#     questions = await conn.fetch(
#         "SELECT id, question, options FROM test_questions WHERE test_id = $1 ORDER BY id", test_id
#     )
#     await conn.close()

#     if not questions:
#         if callback.message and hasattr(callback.message, "edit_text"):
#             await callback.message.edit_text("❌ У этого теста пока нет вопросов.")
#         else:
#             await callback.answer("❌ У этого теста нет вопросов.", show_alert=True)
#         return


#     await state.update_data(
#         test_id=test_id,
#         questions=questions,
#         current_index=0,
#         correct_answers=0
#     )
#     await state.set_state(TestState.answering)

#     await send_next_question(callback.message, state)

# async def send_next_question(msg: Message, state: FSMContext):
#     if not isinstance(msg, Message):
#         return

#     data = await state.get_data()
#     index = data.get("current_index", 0)
#     questions = data.get("questions", [])

#     if index >= len(questions):
#         await msg.answer("⚠️ Вопросов больше нет.")
#         return

#     question = questions[index]
#     options_raw = question.get("options")
#     options = options_raw.split("||") if options_raw else []

#     kb = get_answer_keyboard(
#         test_id=data["test_id"],
#         question_id=question["id"],
#         options=options
#     )

#     await msg.answer(
#         f"<b>Вопрос {index + 1}:</b> {question['question']}",
#         parse_mode="HTML",
#         reply_markup=kb
#     )

# @router.callback_query(F.data.startswith("answer:"))
# async def handle_answer(callback: CallbackQuery, state: FSMContext):
#     if not callback.data:
#         return

#     try:
#         _, test_id_str, question_id_str, selected = callback.data.split(":")
#         test_id = int(test_id_str)
#         question_id = int(question_id_str)
#     except Exception:
#         if callback.message:
#             await callback.message.answer("Неверный формат ответа.")
#         return

#     conn = await asyncpg.connect(DATABASE_URL)
#     correct = await conn.fetchval(
#         "SELECT correct_option FROM test_questions WHERE id = $1", question_id
#     )
#     user_row = await conn.fetchrow(
#         "SELECT id FROM users WHERE telegram_id = $1", callback.from_user.id
#     )
#     await conn.close()

#     if not user_row:
#         if callback.message:
#             await callback.message.answer("❌ Вы не зарегистрированы в системе.")
#         return

#     data = await state.get_data()
#     correct_answers = data.get("correct_answers", 0)

#     if selected == correct:
#         correct_answers += 1

#     index = data.get("current_index", 0) + 1
#     total = len(data.get("questions", []))

#     if index < total:
#         await state.update_data(current_index=index, correct_answers=correct_answers)
#         await send_next_question(callback.message, state)
#     else:
#         await state.clear()
#         await save_test_result(user_row["id"], test_id, correct_answers, total)
#         if callback.message:
#             await callback.message.answer(
#                 f"✅ Тест завершён!\nРезультат: <b>{correct_answers} из {total}</b>.",
#                 parse_mode="HTML"
#             )

# async def save_test_result(user_id: int, test_id: int, correct: int, total: int):
#     conn = await asyncpg.connect(DATABASE_URL)
#     await conn.execute(
#         """
#         INSERT INTO test_results (user_id, test_id, correct_answers, total_questions)
#         VALUES ($1, $2, $3, $4)
#         """,
#         user_id, test_id, correct, total
#     )
#     await conn.close()