from sqlalchemy import Table, Column, Integer, ForeignKey, MetaData

metadata = MetaData()

event_participants = Table(
    "event_participants",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("event_id", Integer, ForeignKey("events.id")),
    Column("user_id", Integer, ForeignKey("users.id"))
)