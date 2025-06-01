import asyncpg
from aiogram.types import Message
from bot.config import DATABASE_URL


async def get_user_by_telegram_id(msg: Message) -> int | None:
    if not msg.from_user:
        return None

    telegram_id = msg.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    await conn.close()

    if row:
        return row["id"]
    return None
