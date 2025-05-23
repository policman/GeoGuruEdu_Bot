import asyncpg
from datetime import date

class EventService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def insert_event(self, event_data: dict) -> int:
        row = await self.conn.fetchrow("""
            INSERT INTO events (author_id, title, description, start_date, end_date, organizers, price, photos, videos, is_draft)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id
        """, event_data['author_id'], event_data['title'], event_data['description'],
             event_data['start_date'], event_data['end_date'], event_data['organizers'],
             event_data['price'], event_data['photos'], event_data['videos'], event_data.get('is_draft', True))
        if not row:
            raise RuntimeError("Не удалось добавить событие в базу данных!")
        return row["id"]

    async def add_participant(self, event_id: int, user_id: int):
        await self.conn.execute("""
            INSERT INTO event_participants (event_id, user_id)
            VALUES ($1, $2)
        """, event_id, user_id)

    async def get_created_events(self, user_id: int):
        return await self.conn.fetch("SELECT * FROM events WHERE author_id = $1 ORDER BY start_date", user_id)

    async def get_active_events(self, user_id: int):
        today = date.today()
        return await self.conn.fetch("""
            SELECT * FROM events
            WHERE start_date >= $1
            AND id IN (SELECT event_id FROM event_participants WHERE user_id = $2)
            ORDER BY start_date
        """, today, user_id)

    async def get_archive_events(self, user_id: int):
        today = date.today()
        return await self.conn.fetch("""
            SELECT * FROM events
            WHERE end_date < $1
            AND (id IN (SELECT event_id FROM event_participants WHERE user_id = $2)
                 OR author_id = $2)
            ORDER BY end_date DESC
        """, today, user_id)
    
    async def get_event_by_id(self, event_id: int):
        return await self.conn.fetchrow("SELECT * FROM events WHERE id = $1", event_id)

    async def delete_event(self, event_id: int):
        await self.conn.execute("DELETE FROM events WHERE id = $1", event_id)

    async def delete_event_by_id(self, event_id: int):
        await self.conn.execute("DELETE FROM events WHERE id = $1", event_id)

    # Универсальное обновление (только передаваемые поля)
    async def update_event_fields(self, event_id, **kwargs):
        if not kwargs:
            return
        fields = []
        values = []
        for i, (key, value) in enumerate(kwargs.items()):
            fields.append(f"{key} = ${i+1}")
            values.append(value)
        sql = f"UPDATE events SET {', '.join(fields)} WHERE id = ${len(values)+1}"
        values.append(event_id)
        await self.conn.execute(sql, *values)
