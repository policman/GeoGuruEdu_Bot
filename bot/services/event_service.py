# bot/services/event_service.py

import asyncpg
from datetime import date
import datetime

class EventService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def insert_event(self, event_data: dict) -> int:
        row = await self.conn.fetchrow("""
            INSERT INTO events (
                author_id, title, description, start_date, end_date,
                organizers, price, photo, is_draft
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING id
        """,
            event_data['author_id'], event_data['title'],
            event_data['description'], event_data['start_date'],
            event_data['end_date'], event_data['organizers'],
            event_data['price'], event_data['photo'], event_data.get('is_draft', True)
        )
        if not row:
            raise RuntimeError("Не удалось добавить событие!")
        return row["id"]

    async def add_participant(self, event_id: int, user_id: int):
        await self.conn.execute("""
            INSERT INTO event_participants (event_id, user_id)
            VALUES ($1, $2)
        """, event_id, user_id)

    async def get_created_events(self, user_id: int):
        return await self.conn.fetch(
            "SELECT * FROM events WHERE author_id = $1 ORDER BY start_date", user_id
        )

    async def get_active_events(self, user_id: int):
        today = date.today()
        return await self.conn.fetch(
            """
            SELECT * FROM events
            WHERE start_date >= $1
              AND id IN (
                  SELECT event_id FROM event_participants WHERE user_id = $2
              )
            ORDER BY start_date
            """,
            today, user_id
        )

    async def get_archive_events(self, user_id: int):
        today = date.today()
        return await self.conn.fetch(
            """
            SELECT * FROM events
            WHERE end_date < $1
              AND (
                  id IN (SELECT event_id FROM event_participants WHERE user_id = $2)
                  OR author_id = $2
              )
            ORDER BY end_date DESC
            """,
            today, user_id
        )

    async def get_event_by_id(self, event_id: int):
        return await self.conn.fetchrow(
            "SELECT * FROM events WHERE id = $1", event_id
        )

    async def delete_event(self, event_id: int):
        await self.conn.execute("DELETE FROM events WHERE id = $1", event_id)

    async def delete_event_by_id(self, event_id: int):
        """
        Сначала удаляем участников, потом само событие
        """
        await self.conn.execute("DELETE FROM event_participants WHERE event_id = $1", event_id)
        await self.conn.execute("DELETE FROM events WHERE id = $1", event_id)

    async def invite_all_users(self, event_id, inviter_user_id, conn):
        # рассылка приглашений (как раньше)
        user_rows = await conn.fetch("SELECT id FROM users WHERE id != $1", inviter_user_id)
        now = datetime.datetime.now()
        for u in user_rows:
            await conn.execute(
                """
                INSERT INTO invitations (
                    event_id, invited_user_id, inviter_user_id, is_read, is_accepted, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6)
                ON CONFLICT DO NOTHING
                """,
                event_id, u["id"], inviter_user_id, False, None, now
            )

    async def update_event_fields(self, event_id, **kwargs):
        if not kwargs:
            return
        fields = []
        values = []
        for i, (k, v) in enumerate(kwargs.items()):
            fields.append(f"{k} = ${i+1}")
            values.append(v)
        sql = f"UPDATE events SET {', '.join(fields)} WHERE id = ${len(values)+1}"
        values.append(event_id)
        await self.conn.execute(sql, *values)

    async def get_participant_ids(self, user_id: int) -> set[int]:
        rows = await self.conn.fetch(
            "SELECT event_id FROM event_participants WHERE user_id = $1", user_id
        )
        return {r["event_id"] for r in rows}

    async def get_applied_ids(self, user_id: int) -> set[int]:
        rows = await self.conn.fetch(
            """
            SELECT event_id
            FROM invitations
            WHERE invited_user_id = $1
              AND inviter_user_id IS NULL
              AND is_accepted IS NULL
            """, user_id
        )
        return {r["event_id"] for r in rows}

    async def get_participant_counts(self) -> dict[int, int]:
        rows = await self.conn.fetch(
            "SELECT event_id, COUNT(*) AS cnt FROM event_participants GROUP BY event_id"
        )
        return {r["event_id"]: r["cnt"] for r in rows}


    # ----------------------------------------
    # Методы для таблицы participant_messages
    # ----------------------------------------

    async def save_participant_message(self, event_id: int, from_user_id: int, to_user_id: int, text: str):
        """
        Сохраняет вопрос от участника к организатору (is_answered = FALSE по умолчанию).
        """
        now = datetime.datetime.now()
        await self.conn.execute(
            """
            INSERT INTO participant_messages (
                event_id, from_user_id, to_user_id, message_text, created_at, is_answered
            ) VALUES ($1, $2, $3, $4, $5, FALSE)
            """,
            event_id, from_user_id, to_user_id, text, now
        )

    async def fetch_answers_for_participant(
        self, event_id: int, participant_id: int, organizer_id: int,
        limit: int, offset: int
    ) -> list[asyncpg.Record]:
        """
        Возвращает ответ(ы) организатора участнику:
          - event_id  = ID события
          - from_user_id = ID участника
          - to_user_id   = ID организатора
          - is_answered = TRUE
        """
        rows = await self.conn.fetch(
            """
            SELECT id, message_text, answer_text, answered_at
            FROM participant_messages
            WHERE event_id = $1
              AND from_user_id = $2
              AND to_user_id = $3
              AND is_answered = TRUE
            ORDER BY answered_at DESC
            LIMIT $4 OFFSET $5
            """,
            event_id, participant_id, organizer_id, limit, offset
        )
        return rows

    async def count_answers_for_participant(
        self, event_id: int, participant_id: int, organizer_id: int
    ) -> int:
        """
        Считает, сколько ответов уже дал организатор этому участнику.
        """
        row = await self.conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM participant_messages
            WHERE event_id = $1
              AND from_user_id = $2
              AND to_user_id = $3
              AND is_answered = TRUE
            """,
            event_id, participant_id, organizer_id
        )
        return row["cnt"] if row else 0


    # ----------------------------------------
    # Методы для вопросов (когда организатор их просматривает)
    # ----------------------------------------

    async def fetch_questions_for_author(
        self, event_id: int, author_id: int, limit: int, offset: int
    ) -> list[asyncpg.Record]:
        """
        Возвращает вопросы (в порядке от новых к старым) по событию, адресованные организатору:
            - event_id = ID события
            - to_user_id = author_id
            - is_answered = либо FALSE (не отвечены) либо TRUE (отвечены) — все вопросы
        """
        rows = await self.conn.fetch(
            """
            SELECT id, from_user_id, message_text, created_at, is_answered
            FROM participant_messages
            WHERE event_id = $1
              AND to_user_id = $2
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """,
            event_id, author_id, limit, offset
        )
        return rows

    async def count_participant_questions(self, event_id: int, author_id: int) -> int:
        """
        Считает общее число вопросов участников к организатору:
        """
        row = await self.conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM participant_messages
            WHERE event_id = $1
              AND to_user_id = $2
            """,
            event_id, author_id
        )
        return row["cnt"] if row else 0

    async def get_user_telegram_id(self, internal_user_id: int) -> int | None:
        """
        Возвращает telegram_id пользователя по его внутреннему id (из таблицы users).
        Нужно, чтобы отправить уведомление участнику: Bot.send_message(chat_id=telegram_id, ...)
        """
        row = await self.conn.fetchrow(
            "SELECT telegram_id FROM users WHERE id = $1", internal_user_id
        )
        return row["telegram_id"] if row and row["telegram_id"] else None

    async def get_participant_stats(self, event_id: int) -> dict:
        """
        Возвращает словарь вида:
        {
            "departments": { "Отдел1": 3, "Отдел2": 1, ... },
            "professions": {}
        }
        """
        # Берём только department, потому что столбца profession нет
        rows = await self.conn.fetch(
            """
            SELECT u.department
            FROM users AS u
            JOIN event_participants AS ep ON ep.user_id = u.id
            WHERE ep.event_id = $1
            """,
            event_id
        )
        dept_counts: dict[str, int] = {}
        for r in rows:
            d = r["department"] or "Не указан"
            dept_counts[d] = dept_counts.get(d, 0) + 1

        # Оставляем professions пустым словарём
        return {"departments": dept_counts, "professions": {}}


    async def fetch_unanswered_questions(
        self, event_id: int, organizer_id: int, limit: int, offset: int
    ) -> list[asyncpg.Record]:
        """
        Возвращает «неотвеченные» вопросы (is_answered = FALSE) к организатору:
        SELECT id, from_user_id, message_text, created_at
        WHERE event_id = $1 AND to_user_id = $2 AND is_answered = FALSE
        ORDER BY created_at DESC LIMIT $3 OFFSET $4.
        """
        return await self.conn.fetch(
            """
            SELECT id, from_user_id, message_text, created_at
            FROM participant_messages
            WHERE event_id = $1
              AND to_user_id = $2
              AND is_answered = FALSE
            ORDER BY created_at DESC
            LIMIT $3 OFFSET $4
            """,
            event_id, organizer_id, limit, offset
        )


    async def count_unanswered_questions(self, event_id: int, organizer_id: int) -> int:
        """
        Считает, сколько ещё «неотвеченных» вопросов (is_answered = FALSE)
        в participant_messages у данного организатора по событию.
        """
        row = await self.conn.fetchrow(
            """
            SELECT COUNT(*) AS cnt
            FROM participant_messages
            WHERE event_id = $1
              AND to_user_id = $2
              AND is_answered = FALSE
            """,
            event_id, organizer_id
        )
        return row["cnt"] if row else 0
