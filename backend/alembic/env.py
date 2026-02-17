from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
import asyncio
import os

from app.db.base import Base
from app.models.user import User
from app.models.fraud import FraudulentNumber, FraudulentSMSPattern, FraudulentDomain
from app.models.report import UserReport, DetectionLog
from app.models.ml_model import MLModelVersion

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """
    Priorité : variable d'environnement DATABASE_URL
    Fallback  : valeur dans alembic.ini
    Ceci permet à Docker de passer l'URL avec le nom de container
    (ex: dyleth-postgres) au lieu de 127.0.0.1
    """
    return os.environ.get(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url")
    )


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url = get_url()
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())