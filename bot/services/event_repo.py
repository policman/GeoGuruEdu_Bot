import asyncpg
from datetime import date

async def insert_event(conn: asyncpg.Connection, event_data: dict) -> int:
    row = await conn.fetchrow("""
        INSERT INTO events (author_id, title, description, start_date, end_date, organizers, price, photos, videos, is_draft)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
    """, event_data['author_id'], event_data['title'], event_data['description'],
         event_data['start_date'], event_data['end_date'], event_data['organizers'],
         event_data['price'], event_data['photos'], event_data['videos'], event_data.get('is_draft', True))
    return row["id"]

async def add_participant(conn: asyncpg.Connection, event_id: int, user_id: int):
    await conn.execute("""
        INSERT INTO event_participants (event_id, user_id)
        VALUES ($1, $2)
    """, event_id, user_id)

async def get_created_events(conn: asyncpg.Connection, user_id: int):
    return await conn.fetch("SELECT * FROM events WHERE author_id = $1 ORDER BY start_date", user_id)

async def get_active_events(conn: asyncpg.Connection, user_id: int):
    ######today = date.today()
    today = date(2000, 1, 1)
    return await conn.fetch("""
        SELECT * FROM events
        WHERE start_date >= $1
        AND id IN (SELECT event_id FROM event_participants WHERE user_id = $2)
        ORDER BY start_date
    """, today, user_id)

async def get_archive_events(conn: asyncpg.Connection, user_id: int):
    today = date.today()
    return await conn.fetch("""
        SELECT * FROM events
        WHERE end_date < $1
        AND (id IN (SELECT event_id FROM event_participants WHERE user_id = $2)
             OR author_id = $2)
        ORDER BY end_date DESC
    """, today, user_id)