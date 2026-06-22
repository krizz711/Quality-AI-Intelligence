from logging.config import fileConfig

import asyncio

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from sqlalchemy import text

from alembic import context
import os
import sys
from pathlib import Path

# ensure project root is on sys.path for model imports
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

# import the project's metadata
try:
    from db import models as models_module
    target_metadata = models_module.Base.metadata
except Exception:  # pragma: no cover - best-effort import
    target_metadata = None

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# If a DATABASE_URL environment variable is provided (container runtime),
# make sure the alembic Config uses it as the main sqlalchemy.url so both
# CLI and programmatic invocation pick it up.
if os.environ.get("DATABASE_URL"):
    # ConfigParser treats % as interpolation; escape for URL-encoded passwords.
    config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL").replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Allow overriding the URL via env var for local generation
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="arad_alembic_version",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = os.environ.get("DATABASE_URL") or section.get("sqlalchemy.url")

    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            async with connection.begin():
                await connection.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS arad_alembic_version (
                            version_num VARCHAR(255) NOT NULL PRIMARY KEY
                        )
                        """
                    )
                )
                await connection.execute(
                    text(
                        "ALTER TABLE arad_alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"
                    )
                )
                await connection.run_sync(
                    lambda sync_connection: context.configure(
                        connection=sync_connection,
                        target_metadata=target_metadata,
                        version_table="arad_alembic_version",
                        include_object=include_object,
                        compare_type=True,
                        compare_server_default=True,
                    )
                )
                try:
                    await connection.run_sync(lambda _: context.run_migrations())
                except Exception as e:
                    # Don't fail the whole startup on idempotent-already-exists issues.
                    if "already exists" in str(e).lower():
                        import logging

                        logging.getLogger("alembic").warning(
                            "Migration skipped (object already exists): %s", e
                        )
                    else:
                        raise

    asyncio.run(run_async_migrations())


def include_object(object_, name, type_, reflected, compare_to):
    """Limit autogenerate to this application's tables and columns only."""
    if type_ == "table" and name == "arad_alembic_version":
        return False
    if type_ == "table" and reflected and target_metadata is not None:
        return name in target_metadata.tables
    return True


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
