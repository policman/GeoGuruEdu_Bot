import asyncpg
from aiogram.types import Message
from bot.config import DATABASE_URL

async def get_or_create_user_id(msg: Message) -> int | None:
    if not msg.from_user:
        return None

    user = msg.from_user
    telegram_id = user.id

    conn = await asyncpg.connect(DATABASE_URL)

    row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    if row:
        await conn.close()
        return row["id"]

    # Заглушки для обязательных полей
    first_name = user.first_name or "-"
    last_name = user.last_name or "-"
    middle_name = "-"
    username = user.username or None
    position = "-"
    experience = 0  # INTEGER
    department = "-"

    # Вставка пользователя с учётом всех обязательных полей
    await conn.execute("""
        INSERT INTO users (
            first_name, last_name, middle_name,
            username, telegram_id, position,
            experience, department
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, first_name, last_name, middle_name,
         username, telegram_id, position,
         experience, department)

    row = await conn.fetchrow("SELECT id FROM users WHERE telegram_id = $1", telegram_id)
    await conn.close()

    if row:
        return row["id"]
    return None
