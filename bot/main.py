from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
import os

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота, хранилища и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Импорт хендлеров
from bot.handlers.start import register_start_handlers
from bot.handlers.menu import register_menu_handlers
from bot.handlers.profile import register_profile_handlers
from bot.handlers.events import register_event_handlers

register_start_handlers(dp)
register_menu_handlers(dp)
register_profile_handlers(dp)
register_event_handlers(dp)

# Импорт миграций
from run_migrations import main as run_migrations_main

# Функция запуска при старте бота
async def on_startup(dp):
    await run_migrations_main()
    print("🚀 Бот запущен и миграции выполнены")

# Точка входа
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
