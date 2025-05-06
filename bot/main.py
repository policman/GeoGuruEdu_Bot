from aiogram import Bot, Dispatcher, executor
from bot.config import BOT_TOKEN
from bot.handlers.start import register_start_handlers
from bot.handlers.menu import register_menu_handlers
from bot.handlers.learning import register_learning_handlers
from bot.services.migrations import run_migration
import asyncio

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

register_start_handlers(dp)
register_menu_handlers(dp)
register_learning_handlers(dp)

async def on_startup(dispatcher):
    await run_migration()

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
