# bot/services/test_service.py

import asyncpg
from typing import List, Optional
from datetime import datetime

class TestService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    # --- Тесты ---
    async def create_test(self, title: str, description: str, created_by: int) -> int:
        row = await self.conn.fetchrow(
            """
            INSERT INTO tests (title, description, created_by)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            title, description, created_by
        )
        if row is None:
            raise RuntimeError("Не удалось создать тест")
        return row["id"]

    async def get_all_tests(self) -> List[asyncpg.Record]:
        return await self.conn.fetch(
            "SELECT id, title, description, created_by FROM tests ORDER BY created_at DESC"
        )


    async def get_test_by_id(self, test_id: int) -> Optional[asyncpg.Record]:
        row = await self.conn.fetchrow(
            "SELECT id, title, description FROM tests WHERE id = $1", test_id
        )
        return row  # может вернуться None, вызывающий код проверяет это

    # --- Вопросы ---
    async def add_question(self, test_id: int, text: str, position: int) -> int:
        row = await self.conn.fetchrow(
            """
            INSERT INTO questions (test_id, text, position)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            test_id, text, position
        )
        if row is None:
            raise RuntimeError("Не удалось добавить вопрос")
        return row["id"]

    async def get_questions(self, test_id: int) -> List[asyncpg.Record]:
        return await self.conn.fetch(
            """
            SELECT id, text, position
            FROM questions
            WHERE test_id = $1
            ORDER BY position
            """,
            test_id
        )

    # --- Варианты ответов ---
    async def add_option(self, question_id: int, text: str, is_correct: bool) -> int:
        row = await self.conn.fetchrow(
            """
            INSERT INTO options (question_id, text, is_correct)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            question_id, text, is_correct
        )
        if row is None:
            raise RuntimeError("Не удалось добавить вариант ответа")
        return row["id"]

    async def get_options(self, question_id: int) -> List[asyncpg.Record]:
        return await self.conn.fetch(
            """
            SELECT id, text, is_correct
            FROM options
            WHERE question_id = $1
            """,
            question_id
        )

    # --- Сохранение результата ---
    async def save_test_result(
        self, user_id: int, test_id: int,
        correct_answers: int, total_questions: int
    ) -> int:
        row = await self.conn.fetchrow(
            """
            INSERT INTO test_results (user_id, test_id, correct_answers, total_questions)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            user_id, test_id, correct_answers, total_questions
        )
        if row is None:
            raise RuntimeError("Не удалось сохранить результат")
        return row["id"]

    async def record_user_answer(
        self, result_id: int, question_id: int, chosen_option: int
    ):
        await self.conn.execute(
            """
            INSERT INTO user_answers (result_id, question_id, chosen_option)
            VALUES ($1, $2, $3)
            """,
            result_id, question_id, chosen_option
        )
