from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite by default (no setup needed), or PostgreSQL if configured
DEFAULT_DB = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'road_ai.db')}"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

# SQLite needs special args
connect_args = {}
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
