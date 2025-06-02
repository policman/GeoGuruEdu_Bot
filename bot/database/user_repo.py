import asyncpg
from typing import Optional

async def get_user_by_telegram_id(conn: asyncpg.Connection, telegram_id: int) -> Optional[asyncpg.Record]:
    return await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)

async def insert_user(conn: asyncpg.Connection, user_data: dict):
    await conn.execute("""
        INSERT INTO users (last_name, first_name, middle_name, username, telegram_id, position, experience, department)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    """, user_data['last_name'], user_data['first_name'], user_data['middle_name'],
         user_data['username'], user_data['telegram_id'],
         user_data['position'], user_data['experience'], user_data['department'])

async def update_user_field(conn: asyncpg.Connection, telegram_id: int, field: str, value):
    await conn.execute(
        f"UPDATE users SET {field} = $1 WHERE telegram_id = $2",
        value, telegram_id
    )

async def update_user_fields(
    conn: asyncpg.Connection,
    telegram_id: int,
    position: Optional[str] = None,
    department: Optional[str] = None
):
    """
    Обновляет поля position и/или department по telegram_id.
    Если одно из значений None, то это поле не обновляется.
    """
    clauses: list[str] = []
    args: list = []
    idx = 1

    if position is not None:
        clauses.append(f"position = ${idx}")
        args.append(position)
        idx += 1

    if department is not None:
        clauses.append(f"department = ${idx}")
        args.append(department)
        idx += 1

    if not clauses:
        return

    args.append(telegram_id)  # последний параметр для WHERE
    sql = f"UPDATE users SET {', '.join(clauses)} WHERE telegram_id = ${idx}"
    await conn.execute(sql, *args)
