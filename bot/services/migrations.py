import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def run_migration():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не задан в .env")

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            last_name TEXT NOT NULL,
            first_name TEXT NOT NULL,
            middle_name TEXT,
            username TEXT NOT NULL,
            telegram_id BIGINT NOT NULL UNIQUE,
            position TEXT NOT NULL,
            experience INTEGER NOT NULL,
            department TEXT
        );
    """)
    await conn.close()
    print("✅ Таблица users создана (если её не было).")
