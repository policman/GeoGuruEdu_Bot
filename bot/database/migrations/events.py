from sqlalchemy import (
    Table, Column, Integer, String, ForeignKey, Date, MetaData, ARRAY, Text
)

metadata = MetaData()

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String),
    Column("description", String),
    Column("start_date", Date),
    Column("end_date", Date),
    Column("organizers", String),
    Column("price", Integer),
    Column("photo", ARRAY(Text)),   
    Column("creator_id", Integer, ForeignKey("users.id", ondelete="SET NULL")),
)
