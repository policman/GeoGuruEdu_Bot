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
        BotCommand(command="help", description="Справка"),
        BotCommand(command="menu", description="Показать главное меню"),
    ])

async def main():
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения")

    bot = Bot(
        token=BOT_TOKEN,
        parse_mode=ParseMode.HTML  # ВОТ ТАК!
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Импорт хендлеров и роутеров
    from bot.handlers import start
    from bot.handlers.menu import router as menu_router
    from bot.handlers import profile
    from bot.handlers.events import router as events_router
    from bot.handlers.learning.ai import ai_chat_router
    from bot.handlers.learning import learning_router
    from bot.handlers.events import manage
    

    dp.include_router(start.router)
    dp.include_router(menu_router)
    dp.include_router(profile.router)
    dp.include_router(events_router)
    dp.include_router(ai_chat_router)
    dp.include_router(learning_router)
    dp.include_router(manage.router)
    
    await set_default_commands(bot)
    await run_migrations_main()
    print("🚀 Бот запущен и миграции выполнены")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
