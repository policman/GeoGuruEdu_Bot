from sqlalchemy import Table, Column, Integer, Text, BigInteger, MetaData

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("last_name", Text, nullable=False),
    Column("first_name", Text, nullable=False),
    Column("middle_name", Text),
    Column("username", Text, nullable=False),
    Column("telegram_id", BigInteger, unique=True, nullable=False),
    Column("position", Text, nullable=False),
    Column("experience", Integer, nullable=False),
    Column("department", Text)
)