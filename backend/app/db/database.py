from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path

# SQLite database file
sqlite_file_name = "medpredict.db"
sqlite_url = f"sqlite:///{Path(__file__).parent.parent.parent}/{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
