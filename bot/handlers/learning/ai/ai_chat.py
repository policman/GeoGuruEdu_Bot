from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from bot.keyboards.learning.ai.ai_chat import ai_chat_kb
from bot.states.ai_chat import AIChatStates
import aiohttp
import os
from typing import Optional
router = Router()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@router.message(Command("ai_chat"))
async def enter_ai_chat(message: types.Message, state: FSMContext):
    await state.set_state(AIChatStates.chatting)
    await message.answer("Привет! Это ИИ-чат DeepSeek. Задай мне вопрос 👇", reply_markup=ai_chat_kb)

@router.message(lambda msg: msg.text == "⛔️ Завершить диалог", AIChatStates.chatting)
async def exit_ai_chat(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Диалог завершён. Возвращаюсь в главное меню.", reply_markup=types.ReplyKeyboardRemove())
    # Вызовите здесь show_main_menu(message), если есть функция

@router.message(AIChatStates.chatting)
async def process_ai_input(message: types.Message, state: FSMContext):
    await state.set_state(AIChatStates.waiting_response)
    await message.answer("🧠 Думаю...")

    response = await query_deepseek(message.text or "")  # <-- исправлено

    if response:
        await message.answer(response)
    else:
        await message.answer("Произошла ошибка при обращении к ИИ.")

    await state.set_state(AIChatStates.chatting)

async def query_deepseek(prompt: str) -> Optional[str]:
    if not OPENROUTER_API_KEY:
        return "API-ключ не настроен."
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/your_bot_username"  # Замените на свой бот
    }
    payload = {
        "model": "deepseek/deepseek-v3-base:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            return None