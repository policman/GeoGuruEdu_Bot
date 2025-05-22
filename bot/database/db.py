import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def get_connection():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не установлен в .env")
    return await asyncpg.connect(DATABASE_URL)
