# bot/database/migrations/invitations.py

from sqlalchemy import Table, Column, Integer, ForeignKey, Boolean, DateTime, MetaData, UniqueConstraint

metadata = MetaData()

invitations = Table(
    "invitations",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE")),
    Column("invited_user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
    Column("inviter_user_id", Integer, ForeignKey("users.id", ondelete="SET NULL")),
    Column("is_read", Boolean, default=False),
    Column("is_accepted", Boolean, default=None, nullable=True),
    Column("created_at", DateTime),
    Column("approved_by_author", Boolean, default=None, nullable=True)
    #UniqueConstraint("event_id", "invited_user_id", name="uniq_event_invited")
)
