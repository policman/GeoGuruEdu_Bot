import asyncio
import asyncpg
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

from bot.database.migrations.users import users
from bot.database.migrations.events import events
from bot.database.migrations.participants import event_participants


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL не установлена в переменных окружения.")

metadata = MetaData()
users.tometadata(metadata)
events.tometadata(metadata)
event_participants.tometadata(metadata)

# Добавим таблицу версий миграций
migrations_table = Table(
    "migrations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("applied_at", String, nullable=False)
)


migrations_table.tometadata(metadata)
engine = create_engine(DATABASE_URL)
from bot.database.migrations.invitations import invitations
invitations.tometadata(metadata)


MIGRATION_LOG_FILE = "migration.log"

# === Логгер ===
def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(MIGRATION_LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(message)

# === Ручной fallback ===
async def create_users_table_fallback():
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
    log("✅ Таблица users создана вручную (fallback).")

def add_unique_invitation_index(engine):
    with engine.connect() as conn:
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uniq_event_invited ON invitations (event_id, invited_user_id);"
        )
        print("✅ Индекс на invitations создан.")


# === Основная миграция ===
def create_sqlalchemy_tables():
    metadata.create_all(engine)
    log("✅ Все таблицы SQLAlchemy созданы.")

# === Основная функция ===
async def main():
    try:
        create_sqlalchemy_tables()
        add_unique_invitation_index(engine)
        # Логируем факт миграции
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("""
            INSERT INTO migrations (name, applied_at)
            VALUES ($1, $2)
            ON CONFLICT (name) DO NOTHING;
        """, "initial_migration", datetime.now().isoformat())
        await conn.close()
        log("🗂 Миграция 'initial_migration' записана в журнал.")
    except Exception as e:
        #log(f"❌ Ошибка при создании таблиц: {e}")
        #log("🛠 Пробуем создать таблицу users вручную через asyncpg...")
        await create_users_table_fallback()
        create_sqlalchemy_tables()

if __name__ == "__main__":
    asyncio.run(main())