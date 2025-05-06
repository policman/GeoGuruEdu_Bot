import asyncio
from bot.services.migrations import run_migration

if __name__ == "__main__":
    asyncio.run(run_migration())
