import asyncpg

async def get_unread_invitations_count(telegram_id: int, conn) -> int:
    result = await conn.fetchval("""
        SELECT COUNT(*)
        FROM invitations
        JOIN users ON invitations.invited_user_id = users.id
        WHERE users.telegram_id = $1 AND invitations.is_read = FALSE AND invitations.is_accepted IS NULL
    """, telegram_id)
    return result or 0
