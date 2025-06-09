from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import asyncpg
import os
from dotenv import load_dotenv

from bot.states.test_states import TestCreation
from bot.services.test_service import TestService
from bot.database.user_repo import get_user_by_telegram_id
from bot.keyboards.learning.menu import testing_menu_keyboard

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

router = Router()

def cancel_test_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Прекратить создание теста")]],
        resize_keyboard=True
    )

@router.message(F.text == "Создать тест")
async def cmd_create_test(message: Message, state: FSMContext):
    await message.answer(
        "📋 Введите, пожалуйста, название нового теста (текстом):\n\nЕсли хотите отменить создание — нажмите кнопку ниже.",
        reply_markup=cancel_test_keyboard()
    )
    await state.set_state(TestCreation.waiting_for_title)

@router.message(StateFilter(TestCreation), F.text == "❌ Прекратить создание теста")
async def cancel_test_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚫 Создание теста отменено.", reply_markup=testing_menu_keyboard())

@router.message(TestCreation.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    await state.update_data(test_title=title)
    await message.answer("✏️ Теперь введите краткое описание теста (или «–», если без описания):", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_description)

@router.message(TestCreation.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    desc = (message.text or "").strip()
    if desc == "–":
        desc = ""
    await state.update_data(test_description=desc)
    await message.answer("🔹 Сколько вопросов будет в этом тесте? Введите целое число:", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_q_count)

@router.message(TestCreation.waiting_for_q_count)
async def process_q_count(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) < 1:
        await message.answer("❌ Введите корректное число (целое, >= 1):", reply_markup=cancel_test_keyboard())
        return
    q_count = int(text)
    await state.update_data(total_questions=q_count, current_q=1, questions=[])
    await message.answer(f"📝 Введите текст вопроса № 1:", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_q_text)

@router.message(TestCreation.waiting_for_q_text)
async def process_q_text(message: Message, state: FSMContext):
    data = await state.get_data()
    curr = data["current_q"]
    questions = data.get("questions", [])
    questions.append({"text": (message.text or "").strip(), "options": []})
    await state.update_data(questions=questions)
    await message.answer("🔹 Сколько вариантов ответа у этого вопроса? (минимум 2):", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_opt_count)

@router.message(TestCreation.waiting_for_opt_count)
async def process_opt_count(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) < 2:
        await message.answer("❌ Нужно минимум 2 варианта. Введите корректное число:", reply_markup=cancel_test_keyboard())
        return
    opt_count = int(text)
    data = await state.get_data()
    questions = data["questions"]
    questions[-1]["opt_count"] = opt_count
    questions[-1]["opt_entered"] = 0
    await state.update_data(questions=questions)
    await message.answer(f"✏️ Введите текст варианта № 1:", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_opt_text)

@router.message(TestCreation.waiting_for_opt_text)
async def process_opt_text(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    curr_q = questions[-1]
    curr_q["options"].append({"text": (message.text or "").strip(), "is_correct": False})
    curr_q["opt_entered"] += 1
    await state.update_data(questions=questions)
    await message.answer("✅ Этот вариант правильный? (да/нет):", reply_markup=cancel_test_keyboard())
    await state.set_state(TestCreation.waiting_for_opt_is_correct)

@router.message(TestCreation.waiting_for_opt_is_correct)
async def process_opt_is_correct(message: Message, state: FSMContext):
    answer = (message.text or "").strip().lower()
    if answer not in ("да", "нет"):
        await message.answer("❌ Напишите «да» или «нет»:", reply_markup=cancel_test_keyboard())
        return

    data = await state.get_data()
    questions = data["questions"]
    curr_q = questions[-1]
    last_opt = curr_q["options"][-1]
    last_opt["is_correct"] = (answer == "да")

    entered = curr_q["opt_entered"]
    total = curr_q["opt_count"]

    if entered < total:
        await message.answer(f"✏️ Введите текст варианта № {entered+1}:", reply_markup=cancel_test_keyboard())
        await state.set_state(TestCreation.waiting_for_opt_text)
        return

    curr_q_index = data["current_q"]
    total_questions = data["total_questions"]

    if curr_q_index < total_questions:
        await state.update_data(current_q=curr_q_index + 1)
        await message.answer(f"📝 Введите текст вопроса № {curr_q_index + 1}:", reply_markup=cancel_test_keyboard())
        await state.set_state(TestCreation.waiting_for_q_text)
    else:
        conn = await asyncpg.connect(DATABASE_URL)
        user = message.from_user
        if not user:
            await conn.close()
            await message.answer("❌ Не удалось определить пользователя, тест не будет сохранён.")
            await state.clear()
            return
        user_row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", user.id)
        if not user_row:
            await conn.close()
            await message.answer("❌ Вас нет в системе, тест не будет сохранён.")
            await state.clear()
            return

        user_id = user_row["id"]
        svc = TestService(conn)
        title = data["test_title"]
        desc = data["test_description"]
        test_id = await svc.create_test(title, desc, user_id)

        for idx, q_data in enumerate(questions, start=1):
            q_id = await svc.add_question(test_id, q_data["text"], idx)
            for opt in q_data["options"]:
                await svc.add_option(q_id, opt["text"], opt["is_correct"])

        await conn.close()
        await message.answer("🎉 Тест успешно создан!", reply_markup=testing_menu_keyboard())
        await state.clear()
