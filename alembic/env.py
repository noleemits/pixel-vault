"""
alembic/env.py — Alembic migration environment for PixelVault.

Supports both online (connected) and offline (SQL-script) modes.
DATABASE_URL must be set in the environment (or in a .env file loaded before
alembic is invoked).

Typical workflow:
    # Generate a new auto-migration after editing app/models.py
    alembic revision --autogenerate -m "describe_change"

    # Apply pending migrations
    alembic upgrade head

    # Roll back one step
    alembic downgrade -1
"""

import os
import re
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Resolve DATABASE_URL
# Always use the synchronous (psycopg2) DSN for Alembic.
# ---------------------------------------------------------------------------
_raw_url = os.environ.get("DATABASE_URL", "")
if not _raw_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Export it before running alembic commands."
    )

# Strip any async driver prefix so psycopg2 (Alembic's default) is used.
_sync_url = re.sub(r"^postgresql(\+\w+)?://", "postgresql://", _raw_url)
# Escape % for configparser interpolation.
config.set_main_option("sqlalchemy.url", _sync_url.replace("%", "%%"))

# ---------------------------------------------------------------------------
# Import metadata so --autogenerate can detect model changes
# ---------------------------------------------------------------------------
# app.models must be imported *after* DATABASE_URL is set because importing it
# triggers app.database, which reads the env var at module load time.
from app.models import Base  # noqa: E402  (import after env var is set)

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout without a live DB connection
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connect and run migrations in a transaction
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
