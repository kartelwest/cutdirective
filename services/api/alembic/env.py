from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context as alembic_context

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.config import DATABASE_URL
from app.database import Base
import app.models  # noqa: F401  registers models with Base.metadata

config = alembic_context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return DATABASE_URL


def run_migrations_offline() -> None:
    url = get_url()
    alembic_context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with alembic_context.begin_transaction():
        alembic_context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        alembic_context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with alembic_context.begin_transaction():
            alembic_context.run_migrations()


if alembic_context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
