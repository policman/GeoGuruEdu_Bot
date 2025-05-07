import asyncpg

async def insert_event(conn: asyncpg.Connection, event_data: dict):
    await conn.execute("""
        INSERT INTO events (author_id, title, description, start_date, end_date, organizers, price, photos, videos, is_draft)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    """, event_data['author_id'], event_data['title'], event_data['description'],
         event_data['start_date'], event_data['end_date'], event_data['organizers'],
         event_data['price'], event_data['photos'], event_data['videos'], event_data.get('is_draft', True))