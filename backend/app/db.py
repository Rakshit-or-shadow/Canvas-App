from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def _migrate() -> None:
    """Tiny in-place migration for DBs created by the old single-user schema."""
    with engine.connect() as conn:
        for table in ("pushsubscription", "sentreminder"):
            cols = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
            if cols and "user_id" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 0"))
        conn.commit()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session():
    with Session(engine) as session:
        yield session
