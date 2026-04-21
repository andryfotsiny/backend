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
from app.models.business import Business
from dotenv import load_dotenv

load_dotenv()
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    if os.environ.get("DATABASE_URL"):
        return os.environ.get("DATABASE_URL")

    db_type = os.environ.get("DB_TYPE", "postgresql+asyncpg")
    db_user = os.environ.get("DB_USER", "dyleth")
    db_password = os.environ.get("DB_PASSWORD", "dyleth123")
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "dyleth")

    return f"{db_type}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


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
