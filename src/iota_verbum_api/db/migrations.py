from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from iota_verbum_api.config import settings
from iota_verbum_api.db.base import Base
from iota_verbum_api.db.session import engine


def run_migrations() -> None:
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        return
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")
