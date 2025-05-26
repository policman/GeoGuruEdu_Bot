# bot/services/event_service.py

import asyncpg
from datetime import date
import datetime

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
        await self.conn.execute("DELETE FROM event_participants WHERE event_id = $1", event_id)
        await self.conn.execute("DELETE FROM events WHERE id = $1", event_id)

    async def invite_all_users(self, event_id, inviter_user_id, conn):
        # Получить список ВСЕХ пользователей, кроме приглашающего
        user_rows = await conn.fetch("SELECT id FROM users WHERE id != $1", inviter_user_id)
        invited_user_ids = [row['id'] for row in user_rows]

        now = datetime.datetime.now()

        # Вставить приглашения (если нет дублей)
        for invited_id in invited_user_ids:
            await conn.execute(
                """
                INSERT INTO invitations (event_id, invited_user_id, inviter_user_id, is_read, is_accepted, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
                """,
                event_id, invited_id, inviter_user_id, False, None, now
            )

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
