from sqlmodel import Session, SQLModel, create_engine, select

from .config import DATABASE_URL
from .models import Settings

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(Settings)).first():
            session.add(Settings(id=1))
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session
