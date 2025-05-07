from sqlalchemy import Table, Column, Integer, String, Date, Text, Boolean, TIMESTAMP, ForeignKey, ARRAY, MetaData
from bot.database.migrations.users import users  # ensure FK target is imported

metadata = MetaData()

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("author_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("title", String, nullable=False),
    Column("description", Text),
    Column("start_date", Date),
    Column("end_date", Date),
    Column("organizers", Text),
    Column("price", Integer),
    Column("photos", ARRAY(Text)),
    Column("videos", ARRAY(Text)),
    Column("is_draft", Boolean, default=True),
    Column("created_at", TIMESTAMP, server_default="now()")
)