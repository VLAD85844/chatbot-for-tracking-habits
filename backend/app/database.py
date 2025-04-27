from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

def upgrade_db():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

SQLALCHEMY_DATABASE_URL = "postgresql://habit_user:habit_pass@db:5432/habit_db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=0
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()