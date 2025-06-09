import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

from run_migrations import main as run_migrations_main

async def set_default_commands(bot: Bot):
    await bot.set_my_commands([
        BotCommand(command="start", description="Перезапустить бота"),
    ])

async def main():
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в переменных окружении")

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # ───── Импортируем основные роутеры ─────
    from bot.handlers.start import router as start_router
    from bot.handlers.profile import router as profile_router
    from bot.handlers.events.chat import router as events_chat_router

    # ───── Единственный «Learning»-роутер ─────
    from bot.handlers.learning import learning_router
    dp.include_router(learning_router)

    from bot.handlers.events.registration import router as events_router
    dp.include_router(events_router)

    # ───── Подключаем каждый роутер ровно один раз ─────
    dp.include_router(start_router)
    dp.include_router(profile_router)
    dp.include_router(events_chat_router)

    await set_default_commands(bot)
    await run_migrations_main()
    print("🚀 Бот запущен и миграции выполнены")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
