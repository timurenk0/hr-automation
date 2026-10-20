from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import get_settings

# Use postgresql+psycopg://user:password@host:5432/database in DATABASE_URL.
# Connections are opened on first use, rather than when this module is imported.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Shared base for database models owned by each feature."""


# Generator describes an object that produces values one at a time,
# usually through a function containing yield.

# Generator [YieldType, SendType, ReturnType]


def get_db() -> Generator[Session, None, None]:
    """Provide a session per request; services explicitly commit writes.

    Closing the session also rolls back any uncommitted transaction.
    """
    with SessionLocal() as session:
        yield session
