# bot/handlers/learning/take_test.py

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncpg
import os
from datetime import datetime

from bot.services.test_service import TestService
from bot.states.test_states import TestTaking
from bot.database.user_repo import get_user_by_telegram_id
from bot.config import DATABASE_URL

router = Router()


@router.message(F.text == "Пройти тест")
async def show_tests_list(message: Message, state: FSMContext):
    """Показываем список всех доступных тестов как Inline-кнопки, помечая свои как (Ваш)."""
    conn = await asyncpg.connect(DATABASE_URL)
    svc = TestService(conn)

    tests = await svc.get_all_tests()

    # Получаем ID текущего пользователя из БД
    user = message.from_user
    if not user:
        await message.answer("❌ Не удалось определить пользователя.")
        return

    user_row = await get_user_by_telegram_id(conn, user.id)

    await conn.close()

    if not user_row:
        await message.answer("❌ Вас нет в системе, не удалось получить список тестов.")
        return

    user_id = user_row["id"]

    if not tests:
        await message.answer("📭 Пока нет созданных тестов.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for t in tests:
        title = t["title"]
        if t["created_by"] == user_id:
            title += " (Ваш)"


        btn = InlineKeyboardButton(text=title, callback_data=f"start_test:{t['id']}")
        kb.inline_keyboard.append([btn])

    await message.answer("📚 Выберите тест для прохождения:", reply_markup=kb)
    await state.clear()  # сбросим любые FSM-состояния
    await state.set_state(TestTaking.waiting_for_start)



@router.callback_query(TestTaking.waiting_for_start, lambda c: c.data and c.data.startswith("start_test:"))
async def start_selected_test(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data is None:
        return
    parts = callback.data.split(":")
    test_id = int(parts[1])

    conn = await asyncpg.connect(DATABASE_URL)
    svc = TestService(conn)
    test_row = await svc.get_test_by_id(test_id)
    if not test_row:
        await conn.close()
        # Проверяем, что callback.message — это именно Message, прежде чем вызывать .answer()
        if isinstance(callback.message, Message):
            await callback.message.answer("❌ Тест не найден.")
        return

    # Получаем все вопросы (с позициями и вариантами)
    questions = await svc.get_questions(test_id)
    questions_data = []
    for q in questions:
        opts = await svc.get_options(q["id"])
        questions_data.append({
            "question_id": q["id"],
            "text": q["text"],
            "options": [
                {"id": o["id"], "text": o["text"], "is_correct": o["is_correct"]}
                for o in opts
            ]
        })
    await conn.close()

    # Сохраняем во state: тест и questions
    await state.update_data(
        taking_test_id=test_id,
        questions=questions_data,
        current_index=0,
        correct_count=0
    )

    # Убедимся, что callback.message — это именно Message, прежде чем вызвать ask_question
    msg = callback.message
    if not isinstance(msg, Message):
        return

    await ask_question(msg, state)
    await state.set_state(TestTaking.waiting_for_answer)



async def ask_question(chat_obj: Message, state: FSMContext):
    """
    Вспомогательная функция: берёт из state questions[current_index],
    рисует inline-кнопки с вариантами и отправляет сообщение.
    """
    from aiogram.types import Message as AiogramMessage
    if not isinstance(chat_obj, AiogramMessage):
        return

    data = await state.get_data()
    questions = data.get("questions", [])
    idx = data.get("current_index", 0)
    if idx is None or idx >= len(questions):
        return

    q = questions[idx]
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for opt in q["options"]:
        btn = InlineKeyboardButton(
            text=opt["text"],
            callback_data=f"answer:{q['question_id']}:{opt['id']}"
        )
        kb.inline_keyboard.append([btn])

    await chat_obj.answer(
        f"❓ <b>Вопрос {idx+1}:</b> {q['text']}",
        parse_mode="HTML",
        reply_markup=kb
    )


@router.callback_query(TestTaking.waiting_for_answer, lambda c: c.data and c.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data is None:
        return

    parts = callback.data.split(":")
    question_id = int(parts[1])
    chosen_option_id = int(parts[2])

    data = await state.get_data()
    questions = data.get("questions", [])
    idx = data.get("current_index", 0)
    if idx is None or idx >= len(questions):
        return

    q = questions[idx]
    # Найдём в q["options"] ту, которая соответствует chosen_option_id
    selected = next((o for o in q["options"] if o["id"] == chosen_option_id), None)
    is_correct = selected["is_correct"] if selected else False

    # Увеличиваем счётчик, если угадали
    if is_correct:
        new_correct = data.get("correct_count", 0) + 1
        await state.update_data(correct_count=new_correct)

    # Перейдём к следующему вопросу
    next_idx = idx + 1
    total = len(questions)

    msg = callback.message
    if not isinstance(msg, Message):
        return

    if next_idx < total:
        # Убираем клавиатуру предыдущего сообщения
        try:
            await msg.edit_reply_markup(reply_markup=None)
        except:
            pass

        await state.update_data(current_index=next_idx)
        await ask_question(msg, state)
        return

    # Все вопросы пройдены — показываем результат
    correct = data.get("correct_count", 0)
    total_q = total

    # Сохраняем результат в БД
    conn = await asyncpg.connect(DATABASE_URL)
    user_row = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        callback.from_user.id
    )
    if user_row:
        user_id = user_row["id"]
        svc = TestService(conn)
        await svc.save_test_result(user_id, data["taking_test_id"], correct, total_q)
    await conn.close()

    # Очищаем клавиатуру последнего вопроса и выводим итог
    try:
        await msg.edit_reply_markup(reply_markup=None)
    except:
        pass

    await msg.answer(
        f"🏁 Тест завершён!\n"
        f"Ваш результат: <b>{correct} из {total_q}</b>.\n"
        f"Спасибо за прохождение!",
        parse_mode="HTML"
    )

    await state.clear()

