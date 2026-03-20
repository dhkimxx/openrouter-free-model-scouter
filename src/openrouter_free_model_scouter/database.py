from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

SQLALCHEMY_DATABASE_URL = os.environ.get(
    "OPENROUTER_SCOUT_DB_URI", "postgresql://postgres:postgres@db:5432/scouter"
)

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    db_path = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "")
    if os.path.dirname(db_path):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    from . import models  # Ensure models are imported before creating tables

    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
