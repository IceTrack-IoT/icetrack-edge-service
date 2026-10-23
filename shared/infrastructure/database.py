"""Shared Peewee SQLite database configuration."""

from pathlib import Path

from peewee import SqliteDatabase


db = SqliteDatabase(None, timeout=30, pragmas={"busy_timeout": 30_000})


def configure_database(database_path: str) -> None:
    """Configure the database location before contexts initialize their tables."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db.init(str(path))


def connect_database() -> None:
    """Open the thread-local SQLite connection when it is not already open."""
    if db.is_closed():
        db.connect()


def init_db() -> None:
    """Create the tables owned by the bounded contexts when they are absent."""
    connect_database()
    from iam.infrastructure.models import EdgeDeviceModel
    from synchronization.infrastructure.models import TelemetrySyncBatchModel
    from telemetry.infrastructure.models import TelemetrySampleModel

    db.create_tables(
        [EdgeDeviceModel, TelemetrySampleModel, TelemetrySyncBatchModel], safe=True
    )
