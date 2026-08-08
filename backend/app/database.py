"""Database configuration for DapurPangan backend."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Default: lokal dev. Docker compose override via env.
PW = 'zephyrus123'
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://zephyrus:{PW}@localhost:5432/zephyrus"
)

engine = create_engine(DATABASE_URL)


@event.listens_for(engine, "connect")
def _enable_sqlite_fk(dbapi_conn, connection_record):
    if engine.dialect.name == "sqlite":
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
