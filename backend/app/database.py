from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_compatibility(bind_engine=None):
    engine_to_check = bind_engine or engine
    if not str(engine_to_check.url).startswith("sqlite"):
        return

    inspector = inspect(engine_to_check)
    if not inspector.has_table("predictions"):
        return

    columns = inspector.get_columns("predictions")
    machine_id_column = next((col for col in columns if col["name"] == "machine_id"), None)
    if machine_id_column is None:
        return

    if machine_id_column.get("nullable", True) is False:
        with engine_to_check.begin() as connection:
            connection.execute(text("ALTER TABLE predictions RENAME TO predictions_legacy"))
            connection.execute(
                text(
                    """
                    CREATE TABLE predictions (
                        id INTEGER PRIMARY KEY,
                        machine_id VARCHAR(50),
                        failure_probability FLOAT NOT NULL,
                        health_status VARCHAR(50) NOT NULL,
                        model_version VARCHAR(50) DEFAULT 'v1',
                        created_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO predictions (id, machine_id, failure_probability, health_status, model_version, created_at)
                    SELECT id, machine_id, failure_probability, health_status, model_version, created_at
                    FROM predictions_legacy
                    """
                )
            )
            connection.execute(text("DROP TABLE predictions_legacy"))


ensure_sqlite_compatibility()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
